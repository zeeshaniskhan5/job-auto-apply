import time
import random
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class BaseBot:
    def __init__(self, config: dict, platform: str):
        self.config = config
        self.platform = platform
        self.driver = None
        self.wait = None
        self.applied_count = 0
        self.max_applications = config["search"].get("max_applications", 50)
        self.profile_dir = Path(__file__).parent.parent / "profile" / platform

    def _build_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

    def start(self):
        self.driver = self._build_driver()
        self.wait = WebDriverWait(self.driver, 15)
        logger.info(f"[{self.platform}] Browser started.")

    def stop(self):
        if self.driver:
            self.driver.quit()
            logger.info(f"[{self.platform}] Browser closed. Applied: {self.applied_count}")

    def human_type(self, element, text: str):
        element.clear()
        for char in str(text):
            element.send_keys(char)
            time.sleep(random.uniform(0.03, 0.10))

    def random_sleep(self, min_sec: float = 1.0, max_sec: float = 3.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def find(self, by: By, value: str, timeout: int = 10):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def click(self, by: By, value: str, timeout: int = 10) -> bool:
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            el.click()
            return True
        except TimeoutException:
            return False

    def is_logged_in(self, check_url: str, logged_in_indicator: tuple) -> bool:
        self.driver.get(check_url)
        self.random_sleep(2, 4)
        try:
            self.driver.find_element(*logged_in_indicator)
            return True
        except NoSuchElementException:
            return False
