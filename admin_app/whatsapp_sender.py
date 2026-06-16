"""
WhatsApp Web Selenium Sender
Automated WhatsApp message sending via Selenium + WhatsApp Web.
Adapted from broadcast-github for integration with the CogStim Admin App.
"""

import os
import time
import logging
import unicodedata

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

try:
    import emoji
    HAS_EMOJI = True
except ImportError:
    HAS_EMOJI = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False

# ── Logging setup ────────────────────────────────────────────────
log = logging.getLogger("WhatsAppSender")
log.setLevel(logging.DEBUG)

# Attach a console handler so logs are visible even without the GUI
if not log.handlers:
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.DEBUG)
    _ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s  %(message)s",
                                        datefmt="%H:%M:%S"))
    log.addHandler(_ch)


class WhatsAppSender:
    """Manages a Selenium-driven WhatsApp Web session for sending messages."""

    def __init__(self, chrome_profile_path: str, wait_timeout: int = 20):
        self.chrome_profile_path = chrome_profile_path
        self.wait_timeout = wait_timeout
        self.driver = None
        self.wait = None
        self._ready = False

    # ── lifecycle ─────────────────────────────────────────────────

    def is_running(self) -> bool:
        """Check whether the browser session is alive."""
        if self.driver is None:
            return False
        try:
            _ = self.driver.title  # will throw if session is dead
            return True
        except Exception:
            self.driver = None
            self._ready = False
            return False

    def is_ready(self) -> bool:
        return self._ready and self.is_running()

    def start_browser(self):
        """Launch Chrome with the WhatsApp profile and navigate to WhatsApp Web.

        After calling this, the user needs to scan the QR code (first time only).
        The method blocks for ~20 s to give WhatsApp Web time to load.
        """
        if self.is_running():
            log.info("Browser already running – skipping start_browser()")
            return  # already up

        os.makedirs(self.chrome_profile_path, exist_ok=True)
        log.info("Starting Chrome with profile: %s", self.chrome_profile_path)

        options = Options()
        options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
        options.add_argument("--remote-debugging-port=9222")
        # Suppress noisy DevTools logging
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        if HAS_WDM:
            log.info("Installing / locating ChromeDriver via webdriver-manager...")
            service = Service(ChromeDriverManager().install())
        else:
            log.info("Using system chromedriver (webdriver-manager not available)")
            service = Service()  # rely on chromedriver on PATH

        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, self.wait_timeout)

        log.info("Navigating to https://web.whatsapp.com/ ...")
        self.driver.get("https://web.whatsapp.com/")

    # Selectors that indicate a fully-loaded, logged-in WhatsApp Web session.
    # WhatsApp Web frequently changes its DOM, so we try several.
    _READY_SELECTORS = [
        # Search box (classic selector)
        (By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"),
        # Side-panel header (\"Chats\" heading or equivalent)
        (By.XPATH, "//header//div[@contenteditable='true']"),
        # The search/filter input in the side panel
        (By.XPATH, "//div[@id='side']//div[@contenteditable='true']"),
        # The side panel itself
        (By.CSS_SELECTOR, "div#side"),
        # Any chat-list pane element
        (By.CSS_SELECTOR, "div#pane-side"),
        # New chat / menu button in header
        (By.XPATH, "//div[@id='side']//header"),
    ]

    def wait_until_ready(self, timeout: int = 60, poll: float = 2.0) -> bool:
        """Block until WhatsApp Web is fully loaded (side panel visible).

        Returns True if ready, False on timeout.
        """
        if not self.is_running():
            log.warning("wait_until_ready: browser not running")
            return False

        log.info("Waiting up to %ds for WhatsApp Web to load...", timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            for by, selector in self._READY_SELECTORS:
                try:
                    self.driver.find_element(by, selector)
                    log.info("✅ WhatsApp Web ready (matched: %s)", selector)
                    self._ready = True
                    return True
                except (NoSuchElementException, WebDriverException):
                    continue
            time.sleep(poll)
        log.error("❌ Timed out waiting for WhatsApp Web to become ready")
        return False

    def quit(self):
        """Shut down the browser."""
        log.info("Quitting browser session")
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.driver = None
        self.wait = None
        self._ready = False

    # ── sending ───────────────────────────────────────────────────

    # Message-input selectors, tried in order with a short timeout each.
    _MSG_INPUT_SELECTORS = [
        (By.XPATH, "//footer//div[@contenteditable='true']"),
        (By.XPATH, "//div[@role='textbox'][@contenteditable='true']"),
        (By.XPATH, "//div[@aria-placeholder='Type a message']"),
        (By.XPATH, "//div[@contenteditable='true'][@title='Type a message']"),
        (By.XPATH, "//div[@aria-label='Type a message']"),
        (By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"),
        (By.XPATH, "//div[@contenteditable='true'][@data-tab='6']"),
        (By.XPATH, "//div[@contenteditable='true'][@data-tab='1']"),
    ]

    def send_message(self, phone_number: str, message: str) -> dict:
        """Send a text message to *phone_number* via WhatsApp Web.

        Returns a dict: {"success": bool, "error": str | None}
        """
        if not self.is_running():
            log.error("send_message: browser not running")
            return {"success": False, "error": "Browser not running"}

        phone_clean = phone_number.replace("+", "").replace("-", "").replace(" ", "")
        log.info("── send_message('%s') ──", phone_clean)

        try:
            url = f"https://web.whatsapp.com/send?phone={phone_clean}"
            log.info("Navigating to %s", url)
            self.driver.get(url)

            # Give the page a moment to load
            log.info("Waiting 4s for chat page to load...")
            time.sleep(4)

            # ── Check for invalid-number popup (quick, non-blocking) ─
            log.info("Checking for invalid-number popup (2s)...")
            try:
                popup = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located(
                        (By.XPATH,
                         "//div[contains(text(), 'Phone number shared via url is invalid')]")
                    )
                )
                if popup:
                    log.warning("Invalid number popup detected for %s", phone_clean)
                    try:
                        ok_btn = self.driver.find_element(
                            By.XPATH, "//div[@role='button' and text()='OK']")
                        ok_btn.click()
                        time.sleep(1)
                    except NoSuchElementException:
                        pass
                    return {"success": False,
                            "error": f"Invalid number: {phone_clean}"}
            except TimeoutException:
                log.info("No invalid-number popup → number looks valid")

            # ── Extra check for "couldn't find account" ──
            errs = self.driver.find_elements(
                By.XPATH,
                "//div[contains(text(), \"couldn't find a WhatsApp account\")]"
            )
            if errs:
                log.warning("No WhatsApp account for %s", phone_clean)
                return {"success": False,
                        "error": f"No WhatsApp account for {phone_clean}"}

            # ── Locate the message input box ─────────────────────────
            log.info("Searching for message input box (%d selectors)...",
                     len(self._MSG_INPUT_SELECTORS))
            msg_input = None
            for i, (by, sel) in enumerate(self._MSG_INPUT_SELECTORS, 1):
                log.debug("  [%d] Trying: %s", i, sel)
                try:
                    msg_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, sel))
                    )
                    log.info("  ✅ Found input with selector #%d: %s", i, sel)
                    break
                except TimeoutException:
                    log.debug("  ✗ Not found")
                    continue

            if msg_input is None:
                # Dump current page HTML snippet for debugging
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    snippet = body.get_attribute("innerHTML")[:500]
                    log.error("Page body snippet:\n%s", snippet)
                except Exception:
                    pass
                log.error("❌ Could not find message input box")
                return {"success": False,
                        "error": "Could not find message input box"}

            # ── Insert message via execCommand (React-compatible) ─────
            # document.execCommand('insertText') fires a real browser-level
            # InputEvent (inputType: 'insertText') that React properly
            # intercepts.  No clipboard is touched.  Handles all Unicode
            # including emoji since it goes through the browser's native
            # editing pipeline, not ChromeDriver's character encoding.

            log.info("Inserting message via execCommand (%d chars)...",
                     len(message))
            msg_input.click()
            time.sleep(0.3)

            # Split message into lines; use Shift+Enter for newlines in
            # WhatsApp (plain Enter sends the message).
            lines = message.split('\n')
            for i, line in enumerate(lines):
                if line:
                    self.driver.execute_script(
                        "arguments[0].focus();"
                        "document.execCommand('insertText', false, arguments[1]);",
                        msg_input, line
                    )
                if i < len(lines) - 1:
                    # Shift+Enter = newline in WhatsApp
                    ActionChains(self.driver)\
                        .key_down(Keys.SHIFT).send_keys(Keys.ENTER)\
                        .key_up(Keys.SHIFT).perform()
                time.sleep(0.1)

            time.sleep(0.5)

            # Verify that text appeared in the input
            input_text = msg_input.text or ""
            log.info("Input box text after insert: '%s' (%d chars)",
                     input_text[:80], len(input_text))

            if not input_text.strip():
                log.warning("insertText may have failed – input box is still empty")

            # Send with Enter
            log.info("Pressing Enter to send...")
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()

            # Wait for pending-clock icon to vanish (message delivered)
            log.info("Waiting for message delivery confirmation (30s)...")
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.invisibility_of_element_located(
                        (By.XPATH, "//span[@data-icon='msg-time']")
                    )
                )
                log.info("✅ Message delivered to %s", phone_clean)
            except TimeoutException:
                log.warning("Delivery confirmation timed out (msg-time icon), "
                           "but message may still have been sent")

            return {"success": True, "error": None}

        except (NoSuchElementException, TimeoutException) as exc:
            log.error("❌ UI elements not found / timed out: %s", exc)
            return {"success": False,
                    "error": "WhatsApp UI elements not found / timed out"}
        except WebDriverException as exc:
            log.error("❌ WebDriver error: %s", exc)
            return {"success": False,
                    "error": f"WebDriver error: {exc}"}
        except Exception as exc:
            log.error("❌ Unexpected error: %s", exc, exc_info=True)
            return {"success": False,
                    "error": f"Unexpected: {exc}"}

    # ── utility ───────────────────────────────────────────────────

    @staticmethod
    def normalize_message(text: str) -> str:
        """Remove unsupported control characters but keep emojis."""
        def _keep(c):
            cat = unicodedata.category(c)[0]
            if cat not in ('C', 'Z'):
                return True
            if HAS_EMOJI and emoji.is_emoji(c):
                return True
            if c in ('\n', '\r', ' ', '\t'):
                return True
            return False
        return ''.join(c for c in text if _keep(c))
