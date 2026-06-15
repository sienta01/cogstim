"""
WhatsApp Web Selenium Sender
Automated WhatsApp message sending via Selenium + WhatsApp Web.
Adapted from broadcast-github for integration with the CogStim Admin App.
"""

import os
import time
import unicodedata

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
            return  # already up

        os.makedirs(self.chrome_profile_path, exist_ok=True)

        options = Options()
        options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
        options.add_argument("--remote-debugging-port=9222")
        # Suppress noisy DevTools logging
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        if HAS_WDM:
            service = Service(ChromeDriverManager().install())
        else:
            service = Service()  # rely on chromedriver on PATH

        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, self.wait_timeout)

        self.driver.get("https://web.whatsapp.com/")

    def wait_until_ready(self, timeout: int = 60, poll: float = 2.0) -> bool:
        """Block until WhatsApp Web is fully loaded (side panel visible).

        Returns True if ready, False on timeout.
        """
        if not self.is_running():
            return False

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                # The side panel search box is present once logged in
                self.driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='3']")
                self._ready = True
                return True
            except (NoSuchElementException, WebDriverException):
                time.sleep(poll)
        return False

    def quit(self):
        """Shut down the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.driver = None
        self.wait = None
        self._ready = False

    # ── sending ───────────────────────────────────────────────────

    def send_message(self, phone_number: str, message: str) -> dict:
        """Send a text message to *phone_number* via WhatsApp Web.

        Returns a dict: {"success": bool, "error": str | None}
        """
        if not self.is_running():
            return {"success": False, "error": "Browser not running"}

        phone_clean = phone_number.replace("+", "").replace("-", "").replace(" ", "")

        try:
            self.driver.get(f"https://web.whatsapp.com/send?phone={phone_clean}")
            time.sleep(3)

            # Check for invalid-number popup
            try:
                popup = WebDriverWait(self.driver, 7).until(
                    EC.presence_of_element_located(
                        (By.XPATH,
                         "//div[contains(text(), 'Phone number shared via url is invalid')]")
                    )
                )
                if popup:
                    # Dismiss the popup
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
                pass  # no popup → number is valid

            # Extra check for "couldn't find account"
            errs = self.driver.find_elements(
                By.XPATH,
                "//div[contains(text(), \"couldn't find a WhatsApp account\")]"
            )
            if errs:
                return {"success": False,
                        "error": f"No WhatsApp account for {phone_clean}"}

            # Wait for chat input
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@aria-label='Type a message']")
                )
            )

            # Type message preserving line breaks
            msg_input = self.driver.find_element(
                By.XPATH, "//div[@aria-label='Type a message']")
            for line in message.split("\n"):
                msg_input.send_keys(line)
                msg_input.send_keys(Keys.SHIFT + Keys.ENTER)
            msg_input.send_keys(Keys.ENTER)  # send

            # Wait for pending-clock icon to vanish (message delivered)
            WebDriverWait(self.driver, 30).until(
                EC.invisibility_of_element_located(
                    (By.XPATH, "//span[@data-icon='msg-time']")
                )
            )

            return {"success": True, "error": None}

        except (NoSuchElementException, TimeoutException):
            return {"success": False,
                    "error": "WhatsApp UI elements not found / timed out"}
        except WebDriverException as exc:
            return {"success": False,
                    "error": f"WebDriver error: {exc}"}
        except Exception as exc:
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
