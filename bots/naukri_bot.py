import asyncio
import logging
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from core.base_bot import BaseBot
from core.qa_engine import QAEngine

logger = logging.getLogger(__name__)

HOME_URL  = "https://www.naukri.com/"
LOGIN_URL = "https://www.naukri.com/nlogin/login"
JOBS_URL  = "https://www.naukri.com/{keywords}-jobs?jobAge=7"


class NaukriBot(BaseBot):
    def __init__(self, config: dict):
        super().__init__(config, "naukri")
        self.creds  = config["naukri"]
        self.search = config["search"]
        self.qa     = QAEngine(config)

    # ── Auth ──────────────────────────────────────────────────

    async def login(self):
        if await self.is_logged_in(HOME_URL, ".nI-gNb-drawer__icon, .nI-gNb-menuItem"):
            logger.info("[Naukri] Already logged in via saved session.")
            return

        await self.page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await self.sleep(2, 3)
        await self.human_type("#usernameField", self.creds["email"])
        await self.human_type("#passwordField", self.creds["password"])
        await self.click("button[type='submit']:has-text('Login')")
        await self.sleep(4, 6)
        logger.info("[Naukri] Logged in.")

    async def _bump_profile(self):
        """Refreshes Naukri profile so it appears at top of recruiter searches."""
        try:
            await self.page.goto(
                "https://www.naukri.com/mnjuser/profile",
                wait_until="domcontentloaded",
            )
            await self.sleep(2, 3)
            save = self.page.locator("button:has-text('Save')").first
            if await save.count():
                await save.click()
                await self.sleep(1, 2)
                logger.info("[Naukri] Profile bumped to top.")
        except Exception as e:
            logger.warning(f"[Naukri] Profile bump failed: {e}")

    # ── Main run loop ─────────────────────────────────────────

    async def run(self):
        await self.start()
        await self.login()
        await self._bump_profile()

        keywords = self.search.get("keywords", "software-developer")
        slug = keywords.lower().replace(" ", "-")
        url  = JOBS_URL.format(keywords=slug)

        await self.page.goto(url, wait_until="domcontentloaded")
        await self.sleep(3, 5)

        while self.applied_count < self.max_applications:
            links = await self._collect_job_links()
            if not links:
                logger.info("[Naukri] No more jobs found.")
                break

            for link in links:
                if self.applied_count >= self.max_applications:
                    break
                try:
                    await self.page.goto(link, wait_until="domcontentloaded")
                    await self.sleep(2, 4)
                    await self._apply()
                except Exception as e:
                    logger.warning(f"[Naukri] Skipping job: {e}")

            if not await self._next_page():
                break

        await self.stop()

    # ── Apply flow ────────────────────────────────────────────

    async def _apply(self):
        apply_btn = self.page.locator(
            "button:has-text('Apply'), a:has-text('Apply')"
        ).first
        try:
            await apply_btn.wait_for(timeout=5000)
            btn_text = await apply_btn.inner_text()
            if "Applied" in btn_text:
                return
            await apply_btn.click()
        except PlaywrightTimeout:
            return

        await self.sleep(2, 3)

        for _ in range(8):
            await self.sleep(1, 2)
            await self._fill_modal()

            # Check success
            success = self.page.locator(
                "text=Successfully Applied, text=applied successfully"
            )
            if await success.count():
                self.applied_count += 1
                logger.info(f"[Naukri] Applied! Total: {self.applied_count}")
                await self._close_modal()
                return

            # Submit
            submit = self.page.locator(
                "button:has-text('Submit'), button:has-text('Apply')"
            ).last
            if await submit.count():
                await submit.click()
                await self.sleep(1, 2)
                if await self.page.locator(
                    "text=Successfully Applied, text=applied successfully"
                ).count():
                    self.applied_count += 1
                    logger.info(f"[Naukri] Applied! Total: {self.applied_count}")
                    await self._close_modal()
                    return

            # Next / Continue
            progressed = False
            for label in ["Next", "Continue", "Proceed"]:
                btn = self.page.locator(f"button:has-text('{label}')").first
                if await btn.count():
                    await btn.click()
                    await self.sleep(1, 2)
                    progressed = True
                    break
            if not progressed:
                break

        await self._close_modal()

    async def _fill_modal(self):
        resume = self.config["personal"].get("resume_path", "")

        # Resume upload
        if resume:
            upload = self.page.locator("input[type='file']").first
            if await upload.count():
                try:
                    await upload.set_input_files(resume)
                    await self.sleep(1, 2)
                except Exception:
                    pass

        # Text / number / textarea inside apply drawer/modal
        scope = (
            "div.chatbot_DrawerContentWrapper input[type='text'], "
            "div.chatbot_DrawerContentWrapper input[type='number'], "
            "div.chatbot_DrawerContentWrapper textarea, "
            "div.apply-question input, "
            "div.apply-question textarea"
        )
        for inp in await self.page.locator(scope).all():
            try:
                if await inp.input_value():
                    continue
                label = await self.get_label_for(inp)
                answer = self.qa.answer(label)
                if answer:
                    await self.human_type_el(inp, answer)
            except Exception:
                pass

        # Selects
        for sel in await self.page.locator("select").all():
            try:
                label  = await self.get_label_for(sel)
                answer = self.qa.answer(label)
                opts   = await sel.locator("option").all_inner_texts()
                match  = next((o for o in opts if answer.lower() in o.lower()), None)
                if match:
                    await sel.select_option(label=match)
            except Exception:
                pass

        # Radios
        for radio in await self.page.locator("input[type='radio']").all():
            try:
                if await radio.is_checked():
                    continue
                rid = await radio.get_attribute("id")
                label_el = self.page.locator(f"label[for='{rid}']")
                label_text = await label_el.inner_text()
                fieldset = radio.locator("xpath=ancestor::fieldset").first
                q_text = await fieldset.locator("legend").inner_text()
                answer = self.qa.answer(q_text)
                if answer.lower() in label_text.lower():
                    await radio.click()
            except Exception:
                pass

    async def _collect_job_links(self) -> list:
        cards = await self.page.locator(
            "article.jobTuple, .cust-job-tuple"
        ).all()
        links = []
        for card in cards:
            try:
                a = card.locator("a.title, a.row1").first
                href = await a.get_attribute("href")
                if href:
                    links.append(href)
            except Exception:
                pass
        return links

    async def _close_modal(self):
        for sel in [
            "button.close-btn",
            "span.close-icon",
            "button[class*='close']",
        ]:
            if await self.click(sel, timeout=3000):
                await self.sleep(1, 2)
                return

    async def _next_page(self) -> bool:
        btn = self.page.locator(
            "a.pagination-btn.rightBtn, a[title='Next']"
        ).first
        if await btn.count():
            await btn.click()
            await self.sleep(3, 5)
            return True
        return False
