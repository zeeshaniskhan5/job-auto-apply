import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from core.base_bot import BaseBot
from core.qa_engine import QAEngine

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.naukri.com/nlogin/login"
JOBS_URL = "https://www.naukri.com/{keywords}-jobs?jobAge=7"


class NaukriBot(BaseBot):
    def __init__(self, config: dict):
        super().__init__(config, "naukri")
        self.creds = config["naukri"]
        self.search = config["search"]
        self.qa = QAEngine(config)

    def login(self):
        self.driver.get("https://www.naukri.com/")
        self.random_sleep(2, 3)

        # Check if already logged in
        try:
            self.driver.find_element(By.CLASS_NAME, "nI-gNb-drawer__icon")
            logger.info("[Naukri] Already logged in via saved session.")
            return
        except NoSuchElementException:
            pass

        self.driver.get(LOGIN_URL)
        self.random_sleep(2, 3)

        email_field = self.find(By.ID, "usernameField")
        pass_field = self.find(By.ID, "passwordField")
        if not email_field or not pass_field:
            logger.error("[Naukri] Login fields not found.")
            return

        self.human_type(email_field, self.creds["email"])
        self.human_type(pass_field, self.creds["password"])
        self.click(By.XPATH, "//button[@type='submit' and contains(text(),'Login')]")
        self.random_sleep(3, 5)
        logger.info("[Naukri] Logged in successfully.")

    def update_profile(self):
        """Bumps your Naukri profile to top of recruiter searches."""
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            self.random_sleep(2, 3)
            save_btn = self.find(By.XPATH, "//button[contains(text(),'Save')]", timeout=5)
            if save_btn:
                save_btn.click()
                self.random_sleep(1, 2)
                logger.info("[Naukri] Profile updated (bumped to top).")
        except Exception as e:
            logger.warning(f"[Naukri] Profile update failed: {e}")

    def run(self):
        self.start()
        self.login()
        self.update_profile()

        keywords = self.search.get("keywords", "software-developer")
        slug = keywords.lower().replace(" ", "-")
        url = JOBS_URL.format(keywords=slug)

        self.driver.get(url)
        self.random_sleep(3, 5)

        while self.applied_count < self.max_applications:
            job_tuples = self._get_job_links()
            if not job_tuples:
                logger.info("[Naukri] No more jobs found.")
                break

            for job_url in job_tuples:
                if self.applied_count >= self.max_applications:
                    break
                try:
                    self.driver.get(job_url)
                    self.random_sleep(2, 4)
                    self._apply_to_job()
                except Exception as e:
                    logger.warning(f"[Naukri] Skipping job: {e}")
                    continue

            if not self._go_to_next_page():
                break

        self.stop()

    def _get_job_links(self) -> list:
        cards = self.driver.find_elements(
            By.CSS_SELECTOR, "article.jobTuple, .cust-job-tuple"
        )
        links = []
        for card in cards:
            try:
                a = card.find_element(By.CSS_SELECTOR, "a.title, a.row1")
                href = a.get_attribute("href")
                if href:
                    links.append(href)
            except NoSuchElementException:
                pass
        return links

    def _apply_to_job(self):
        apply_btn = self.find(
            By.XPATH,
            "//button[contains(text(),'Apply') and not(contains(text(),'Applied'))]",
            timeout=5,
        )
        if not apply_btn:
            return

        apply_btn.click()
        self.random_sleep(2, 3)

        # Handle apply modal / chatbot
        max_steps = 8
        for _ in range(max_steps):
            self.random_sleep(1, 2)

            # Fill text fields in modal
            for inp in self.driver.find_elements(
                By.CSS_SELECTOR,
                "div.chatbot_DrawerContentWrapper input[type='text'], "
                "div.chatbot_DrawerContentWrapper input[type='number'], "
                "div.chatbot_DrawerContentWrapper textarea, "
                "div.apply-question input, div.apply-question textarea",
            ):
                try:
                    if inp.get_attribute("value"):
                        continue
                    label = self._get_question_text(inp)
                    answer = self.qa.answer(label)
                    if answer:
                        self.human_type(inp, answer)
                except Exception:
                    pass

            # Dropdowns
            for sel in self.driver.find_elements(By.CSS_SELECTOR, "select"):
                try:
                    label = self._get_question_text(sel)
                    answer = self.qa.answer(label)
                    s = Select(sel)
                    for opt in s.options:
                        if answer.lower() in opt.text.lower():
                            s.select_by_visible_text(opt.text)
                            break
                except Exception:
                    pass

            # Radio buttons
            for radio in self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
                try:
                    if radio.is_selected():
                        continue
                    label_el = self.driver.find_element(
                        By.XPATH, f"//label[@for='{radio.get_attribute(\"id\")}']"
                    )
                    q_text = self._get_question_text(radio)
                    answer = self.qa.answer(q_text)
                    if answer.lower() in label_el.text.lower():
                        radio.click()
                except Exception:
                    pass

            # Submit
            if self._click_button(["Submit", "Apply"]):
                # Check if "Applied" confirmation appeared
                self.random_sleep(1, 2)
                success = self.driver.find_elements(
                    By.XPATH, "//*[contains(text(),'Successfully Applied') or contains(text(),'applied successfully')]"
                )
                if success:
                    self.applied_count += 1
                    logger.info(f"[Naukri] Applied! Total: {self.applied_count}")
                    self._close_modal()
                    return

            # Next / Continue
            if not self._click_button(["Next", "Continue", "Proceed"]):
                break

        self._close_modal()

    def _get_question_text(self, element) -> str:
        try:
            el_id = element.get_attribute("id")
            if el_id:
                label = self.driver.find_element(By.XPATH, f"//label[@for='{el_id}']")
                return label.text
        except Exception:
            pass
        try:
            return (
                element.find_element(By.XPATH, "ancestor::div[contains(@class,'question')]//p").text
            )
        except Exception:
            pass
        return element.get_attribute("placeholder") or element.get_attribute("aria-label") or ""

    def _click_button(self, labels: list) -> bool:
        for label in labels:
            try:
                btn = self.driver.find_element(
                    By.XPATH,
                    f"//button[contains(text(),'{label}')] | //input[@value='{label}']",
                )
                btn.click()
                self.random_sleep(1, 2)
                return True
            except NoSuchElementException:
                pass
        return False

    def _close_modal(self):
        for selector in [
            "//button[@class='close-btn']",
            "//span[@class='close-icon']",
            "//button[contains(@class,'close')]",
        ]:
            try:
                self.driver.find_element(By.XPATH, selector).click()
                self.random_sleep(1, 2)
                return
            except NoSuchElementException:
                pass

    def _go_to_next_page(self) -> bool:
        try:
            next_btn = self.driver.find_element(
                By.CSS_SELECTOR, "a.pagination-btn.rightBtn, a[title='Next']"
            )
            next_btn.click()
            self.random_sleep(3, 5)
            return True
        except NoSuchElementException:
            return False
