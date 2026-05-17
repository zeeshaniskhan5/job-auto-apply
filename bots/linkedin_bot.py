import asyncio
import logging
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from core.base_bot import BaseBot
from core.qa_engine import QAEngine

logger = logging.getLogger(__name__)

LOGIN_URL  = "https://www.linkedin.com/login"
FEED_URL   = "https://www.linkedin.com/feed"
JOBS_URL   = (
    "https://www.linkedin.com/jobs/search/"
    "?f_LF=f_AL&keywords={keywords}&location={location}"
)


class LinkedInBot(BaseBot):
    def __init__(self, config: dict):
        super().__init__(config, "linkedin")
        self.creds  = config["linkedin"]
        self.search = config["search"]
        self.qa     = QAEngine(config)

    # ── Auth ──────────────────────────────────────────────────

    async def login(self):
        if await self.is_logged_in(FEED_URL, "#global-nav"):
            logger.info("[LinkedIn] Already logged in via saved session.")
            return

        await self.page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await self.sleep(2, 3)
        await self.human_type("#username", self.creds["email"])
        await self.human_type("#password", self.creds["password"])
        await self.click("button[type='submit']")
        await self.sleep(4, 6)
        logger.info("[LinkedIn] Logged in.")

    # ── Main run loop ─────────────────────────────────────────

    async def run(self):
        await self.start()
        await self.login()

        keywords = self.search.get("keywords", "Software Engineer")
        location = self.search.get("location", "India")
        url = JOBS_URL.format(
            keywords=keywords.replace(" ", "%20"),
            location=location.replace(" ", "%20"),
        )
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.sleep(3, 5)

        while self.applied_count < self.max_applications:
            cards = await self.page.locator(".job-card-container").all()
            if not cards:
                logger.info("[LinkedIn] No more job cards.")
                break

            for card in cards:
                if self.applied_count >= self.max_applications:
                    break
                try:
                    await card.click()
                    await self.sleep(2, 3)
                    await self._apply()
                except Exception as e:
                    logger.warning(f"[LinkedIn] Skipping card: {e}")

            if not await self._next_page():
                break

        await self.stop()

    # ── Apply flow ────────────────────────────────────────────

    async def _apply(self):
        btn = self.page.locator("button.jobs-apply-button").first
        try:
            await btn.wait_for(timeout=5000)
            text = await btn.inner_text()
            if "Easy Apply" not in text:
                return
            await btn.click()
        except PlaywrightTimeout:
            return

        await self.sleep(2, 3)

        for _ in range(10):
            await self._fill_page()
            await self.sleep(1, 2)

            if await self._submit():
                self.applied_count += 1
                logger.info(f"[LinkedIn] Applied! Total: {self.applied_count}")
                await self.sleep(2, 3)
                await self._dismiss()
                return

            if not await self._next_step():
                await self._dismiss()
                return

        await self._dismiss()

    async def _fill_page(self):
        resume = self.config["personal"].get("resume_path", "")

        # Resume upload
        upload = self.page.locator("input[type='file']").first
        if resume and await upload.count():
            try:
                await upload.set_input_files(resume)
                await self.sleep(1, 2)
            except Exception:
                pass

        # Text / number / textarea
        for inp in await self.page.locator(
            "input[type='text'], input[type='number'], textarea"
        ).all():
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

        # Radio buttons
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

    async def _next_step(self) -> bool:
        for label in [
            "Continue to next step",
            "Review your application",
            "Next",
        ]:
            btn = self.page.locator(f"button:has-text('{label}')").first
            if await btn.count():
                await btn.click()
                await self.sleep(1, 2)
                return True
        return False

    async def _submit(self) -> bool:
        btn = self.page.locator("button:has-text('Submit application')").first
        if await btn.count():
            await btn.click()
            await self.sleep(2, 3)
            return True
        return False

    async def _dismiss(self):
        for sel in [
            "button[aria-label='Dismiss']",
            "button.artdeco-modal__dismiss",
        ]:
            if await self.click(sel, timeout=3000):
                await self.sleep(1, 2)
                return

    async def _next_page(self) -> bool:
        btn = self.page.locator("button[aria-label='View next page']").first
        if await btn.count() and await btn.is_enabled():
            await btn.click()
            await self.sleep(3, 5)
            return True
        return False
