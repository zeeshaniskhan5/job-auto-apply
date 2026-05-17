import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
)
from core.base_bot import BaseBot
from core.qa_engine import QAEngine

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.linkedin.com/login"
FEED_URL = "https://www.linkedin.com/feed"
JOBS_URL = "https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords={keywords}&location={location}"


class LinkedInBot(BaseBot):
    def __init__(self, config: dict):
        super().__init__(config, "linkedin")
        self.creds = config["linkedin"]
        self.search = config["search"]
        self.qa = QAEngine(config)

    def login(self):
        if self.is_logged_in(FEED_URL, (By.ID, "global-nav")):
            logger.info("[LinkedIn] Already logged in via saved session.")
            return

        self.driver.get(LOGIN_URL)
        self.random_sleep(2, 3)

        email_field = self.find(By.ID, "username")
        pass_field = self.find(By.ID, "password")
        if not email_field or not pass_field:
            logger.error("[LinkedIn] Login page elements not found.")
            return

        self.human_type(email_field, self.creds["email"])
        self.human_type(pass_field, self.creds["password"])
        self.click(By.XPATH, "//button[@type='submit']")
        self.random_sleep(3, 5)
        logger.info("[LinkedIn] Logged in successfully.")

    def run(self):
        self.start()
        self.login()

        keywords = self.search.get("keywords", "Software Engineer")
        location = self.search.get("location", "India")
        url = JOBS_URL.format(keywords=keywords.replace(" ", "%20"), location=location.replace(" ", "%20"))

        self.driver.get(url)
        self.random_sleep(3, 5)

        while self.applied_count < self.max_applications:
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".job-card-container")
            if not job_cards:
                logger.info("[LinkedIn] No more job cards found.")
                break

            for card in job_cards:
                if self.applied_count >= self.max_applications:
                    break
                try:
                    card.click()
                    self.random_sleep(2, 3)
                    self._apply_to_job()
                except Exception as e:
                    logger.warning(f"[LinkedIn] Skipping card: {e}")
                    continue

            if not self._go_to_next_page():
                break

        self.stop()

    def _apply_to_job(self):
        easy_apply_btn = self.find(By.XPATH, "//button[contains(@class,'jobs-apply-button')]", timeout=5)
        if not easy_apply_btn:
            return
        if "Easy Apply" not in easy_apply_btn.text:
            return

        easy_apply_btn.click()
        self.random_sleep(2, 3)

        max_pages = 10
        for _ in range(max_pages):
            self._fill_form_fields()
            self.random_sleep(1, 2)

            if self._click_submit():
                self.applied_count += 1
                logger.info(f"[LinkedIn] Applied! Total: {self.applied_count}")
                self.random_sleep(2, 3)
                self._close_modal()
                return

            if not self._click_next():
                self._close_modal()
                return

        self._close_modal()

    def _fill_form_fields(self):
        resume_path = self.config["personal"].get("resume_path", "")

        # Resume upload
        try:
            upload = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            if resume_path:
                upload.send_keys(resume_path)
                self.random_sleep(1, 2)
        except NoSuchElementException:
            pass

        # Text inputs
        for inp in self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number'], textarea"):
            try:
                label = self._get_label_for(inp)
                if inp.get_attribute("value"):
                    continue
                answer = self.qa.answer(label)
                if answer:
                    self.human_type(inp, answer)
            except Exception:
                pass

        # Dropdowns
        for sel in self.driver.find_elements(By.TAG_NAME, "select"):
            try:
                label = self._get_label_for(sel)
                answer = self.qa.answer(label)
                s = Select(sel)
                options_text = [o.text.lower() for o in s.options]
                match = next((o for o in options_text if answer.lower() in o), None)
                if match:
                    s.select_by_visible_text(
                        s.options[options_text.index(match)].text
                    )
            except Exception:
                pass

        # Radio buttons
        for radio in self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
            try:
                if not radio.is_selected():
                    label = self._get_label_for(radio)
                    answer = self.qa.answer(label)
                    radio_label = radio.find_element(By.XPATH, "following-sibling::label")
                    if answer.lower() in radio_label.text.lower():
                        radio.click()
            except Exception:
                pass

    def _get_label_for(self, element) -> str:
        try:
            el_id = element.get_attribute("id")
            if el_id:
                label = self.driver.find_element(By.XPATH, f"//label[@for='{el_id}']")
                return label.text
        except Exception:
            pass
        try:
            return element.get_attribute("placeholder") or element.get_attribute("aria-label") or ""
        except Exception:
            return ""

    def _click_next(self) -> bool:
        for xpath in [
            "//button[contains(@aria-label,'Continue to next step')]",
            "//button[contains(@aria-label,'Review')]",
            "//button[span[text()='Next']]",
        ]:
            if self.click(By.XPATH, xpath, timeout=3):
                self.random_sleep(1, 2)
                return True
        return False

    def _click_submit(self) -> bool:
        for xpath in [
            "//button[contains(@aria-label,'Submit application')]",
            "//button[span[text()='Submit application']]",
        ]:
            if self.click(By.XPATH, xpath, timeout=3):
                self.random_sleep(2, 3)
                return True
        return False

    def _close_modal(self):
        for xpath in [
            "//button[@aria-label='Dismiss']",
            "//button[contains(@class,'artdeco-modal__dismiss')]",
        ]:
            if self.click(By.XPATH, xpath, timeout=3):
                self.random_sleep(1, 2)
                return

    def _go_to_next_page(self) -> bool:
        try:
            next_btn = self.driver.find_element(
                By.XPATH, "//button[@aria-label='View next page']"
            )
            if next_btn.is_enabled():
                next_btn.click()
                self.random_sleep(3, 5)
                return True
        except NoSuchElementException:
            pass
        return False
