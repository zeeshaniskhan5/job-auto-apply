import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from core.base_bot import BaseBot
from core.qa_engine import QAEngine

logger = logging.getLogger(__name__)

LOGIN_URL = "https://secure.indeed.com/auth?hl=en_IN&co=IN"
JOBS_URL = "https://www.indeed.com/jobs?q={keywords}&l={location}&fromage=7&iafilter=1"


class IndeedBot(BaseBot):
    def __init__(self, config: dict):
        super().__init__(config, "indeed")
        self.creds = config["indeed"]
        self.search = config["search"]
        self.qa = QAEngine(config)

    def login(self):
        self.driver.get("https://www.indeed.com/")
        self.random_sleep(2, 3)

        try:
            self.driver.find_element(By.ID, "jobsearch-SerpJobCard")
            logger.info("[Indeed] Already logged in via saved session.")
            return
        except NoSuchElementException:
            pass

        self.driver.get(LOGIN_URL)
        self.random_sleep(2, 3)

        email_field = self.find(By.ID, "ifl-InputFormField-3")
        if not email_field:
            email_field = self.find(By.CSS_SELECTOR, "input[type='email']")
        if email_field:
            self.human_type(email_field, self.creds["email"])
            self.click(By.CSS_SELECTOR, "button[type='submit']")
            self.random_sleep(2, 3)

        pass_field = self.find(By.CSS_SELECTOR, "input[type='password']")
        if pass_field:
            self.human_type(pass_field, self.creds["password"])
            self.click(By.CSS_SELECTOR, "button[type='submit']")
            self.random_sleep(3, 5)

        logger.info("[Indeed] Login attempted — complete CAPTCHA manually if prompted.")

    def run(self):
        self.start()
        self.login()

        keywords = self.search.get("keywords", "Software Engineer")
        location = self.search.get("location", "India")
        url = JOBS_URL.format(
            keywords=keywords.replace(" ", "+"),
            location=location.replace(" ", "+"),
        )

        self.driver.get(url)
        self.random_sleep(3, 5)

        while self.applied_count < self.max_applications:
            job_cards = self.driver.find_elements(
                By.CSS_SELECTOR, "div.job_seen_beacon, .resultContent"
            )
            if not job_cards:
                logger.info("[Indeed] No job cards found.")
                break

            for card in job_cards:
                if self.applied_count >= self.max_applications:
                    break
                try:
                    easily_apply = card.find_elements(
                        By.XPATH, ".//*[contains(text(),'Easily apply') or contains(text(),'Easy Apply')]"
                    )
                    if not easily_apply:
                        continue

                    title = card.find_element(By.CSS_SELECTOR, "h2 a, .jobTitle a")
                    title.click()
                    self.random_sleep(2, 4)
                    self._apply_in_new_tab()
                except Exception as e:
                    logger.warning(f"[Indeed] Skipping card: {e}")
                    continue

            if not self._go_to_next_page():
                break

        self.stop()

    def _apply_in_new_tab(self):
        original = self.driver.current_window_handle
        tabs_before = set(self.driver.window_handles)

        apply_btn = self.find(
            By.XPATH,
            "//button[contains(text(),'Apply now') or contains(text(),'Apply on company')]",
            timeout=5,
        )
        if not apply_btn:
            return

        apply_btn.click()
        self.random_sleep(2, 3)

        new_tabs = set(self.driver.window_handles) - tabs_before
        if new_tabs:
            self.driver.switch_to.window(new_tabs.pop())
            self._fill_indeed_form()
            self.driver.close()
            self.driver.switch_to.window(original)
        else:
            self._fill_indeed_form()

    def _fill_indeed_form(self):
        resume_path = self.config["personal"].get("resume_path", "")
        max_steps = 10

        for _ in range(max_steps):
            self.random_sleep(1, 2)

            # Resume upload
            try:
                upload = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                if resume_path:
                    upload.send_keys(resume_path)
                    self.random_sleep(1, 2)
            except NoSuchElementException:
                pass

            # Text fields
            for inp in self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='text'], input[type='number'], textarea"
            ):
                try:
                    if inp.get_attribute("value"):
                        continue
                    label = self._get_label_for(inp)
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
                    for opt in s.options:
                        if answer.lower() in opt.text.lower():
                            s.select_by_visible_text(opt.text)
                            break
                except Exception:
                    pass

            # Radio / checkbox
            for radio in self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
                try:
                    if radio.is_selected():
                        continue
                    label_el = radio.find_element(By.XPATH, "following-sibling::label")
                    label_text = label_el.text
                    q_container = radio.find_element(By.XPATH, "ancestor::fieldset//legend")
                    answer = self.qa.answer(q_container.text)
                    if answer.lower() in label_text.lower():
                        radio.click()
                except Exception:
                    pass

            # Submit
            if self._click_button(["Submit your application", "Submit application"]):
                self.applied_count += 1
                logger.info(f"[Indeed] Applied! Total: {self.applied_count}")
                self.random_sleep(2, 3)
                return

            # Continue / Next
            if not self._click_button(["Continue", "Next", "Review your application"]):
                logger.warning("[Indeed] Could not progress form — skipping.")
                return

    def _click_button(self, labels: list) -> bool:
        for label in labels:
            try:
                btn = self.driver.find_element(
                    By.XPATH, f"//button[contains(text(),'{label}')]"
                )
                btn.click()
                self.random_sleep(1, 2)
                return True
            except NoSuchElementException:
                pass
        return False

    def _get_label_for(self, element) -> str:
        try:
            el_id = element.get_attribute("id")
            if el_id:
                label = self.driver.find_element(By.XPATH, f"//label[@for='{el_id}']")
                return label.text
        except Exception:
            pass
        return element.get_attribute("placeholder") or element.get_attribute("aria-label") or ""

    def _go_to_next_page(self) -> bool:
        try:
            next_btn = self.driver.find_element(
                By.CSS_SELECTOR, "a[data-testid='pagination-page-next']"
            )
            next_btn.click()
            self.random_sleep(3, 5)
            return True
        except NoSuchElementException:
            return False
