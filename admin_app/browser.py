import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure Chrome options
chrome_profile_path = r"D:/OneDrive/Timmy/broadcast/Timmy/chrome-whatsapp-profile"

options = Options()
options.add_argument(f"--user-data-dir={chrome_profile_path}")  # Keep login session
options.add_argument("--remote-debugging-port=9222")  # Prevents multiple instances

# Initialize WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)  # Set up a wait for elements

# Keep the browser open
print("Keeping browser open.")
input("Press Enter to close the browser...")