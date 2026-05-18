import asyncio
import logging
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from core.base_bot import BaseBot
from core.qa_engine import QAEngine

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.linkedin.com/login"
FEED_URL  = "https://www.linkedin.com/feed"
JOBS_URL  = (
    "https://www.linkedin.com/jobs/search/"
    "?f_LF=f_AL&keywords={keywords}&location={location}"
)

# LinkedIn changes class names often — try multiple selectors
JOB_CARD_SELECTORS = [
    "li.scaffold-layout__list-item",
    ".jobs-search-results__list-item",
    "div[data-job-id]",
    ".job-card-container",
    ".jobs-search-two-pane__job-card-container--viewport-tracking-0",
]

APPLY_BTN_SELECTORS = [
    "button.jobs-apply-button",
    "button[aria-label*='Easy Apply']",
    "button:has-text('Easy Apply')",
    ".jobs-apply-button--top-card",
]


class LinkedInBot(BaseBot):
    def __init__(self, config: dict):
        super().__init__(config, "linkedin")
        self.search = config["search"]
        self.qa     = QAEngine(config)

    # ── Auth ──────────────────────────────────────────────────

    async def login(self):
        await self.wait_for_manual_login(
            login_url=LOGIN_URL,
            indicator_selector="#global-nav",
            platform="LinkedIn",
        )

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

        logger.info(f"[LinkedIn] Navigating to job search: '{keywords}' in '{location}'")
        logger.info(f"[LinkedIn] URL: {url}")
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.sleep(4, 6)

        page_num = 1
        while self.applied_count < self.max_applications:
            logger.info(f"[LinkedIn] ---- Page {page_num} ----")

            cards = await self._get_job_cards()
            if not cards:
                logger.info("[LinkedIn] No job cards found — scrolling and retrying...")
                await self.page.evaluate("window.scrollTo(0, 300)")
                await self.sleep(2, 3)
                cards = await self._get_job_cards()
                if not cards:
                    logger.warning("[LinkedIn] Still no job cards. Check if the browser is on the right page.")
                    logger.info(f"[LinkedIn] Current URL: {self.page.url}")
                    break

            logger.info(f"[LinkedIn] Found {len(cards)} job cards on page {page_num}.")

            for i, card in enumerate(cards):
                if self.applied_count >= self.max_applications:
                    logger.info(f"[LinkedIn] Reached max applications ({self.max_applications}). Stopping.")
                    break
                try:
                    # Try to get job title for logging
                    title = "Unknown"
                    try:
                        title = await card.locator("a.job-card-list__title, h3, .job-card-container__link").first.inner_text(timeout=2000)
                        title = title.strip()
                    except Exception:
                        pass

                    logger.info(f"[LinkedIn] [{i+1}/{len(cards)}] '{title}'")
                    await card.scroll_into_view_if_needed()
                    await card.click()
                    await self.sleep(2, 3)
                    await self._apply()
                except Exception as e:
                    logger.warning(f"[LinkedIn] Skipping card {i+1}: {e}")

            if not await self._next_page():
                logger.info("[LinkedIn] No more pages.")
                break
            page_num += 1

        logger.info(f"[LinkedIn] ---- Session complete. Applied: {self.applied_count} ----")
        await self.stop()

    async def _get_job_cards(self) -> list:
        for sel in JOB_CARD_SELECTORS:
            cards = await self.page.locator(sel).all()
            if cards:
                return cards
        return []

    # ── Apply flow ────────────────────────────────────────────

    async def _apply(self):
        # Find Easy Apply button using multiple selectors
        apply_btn = None
        for sel in APPLY_BTN_SELECTORS:
            candidate = self.page.locator(sel).first
            try:
                await candidate.wait_for(timeout=3000)
                text = await candidate.inner_text()
                if "Easy Apply" in text:
                    apply_btn = candidate
                    break
            except Exception:
                continue

        if not apply_btn:
            logger.info("[LinkedIn] No Easy Apply button — skipping (likely external apply).")
            return

        logger.info("[LinkedIn] Easy Apply button found — opening form...")
        await apply_btn.click()
        await self.sleep(2, 3)

        for step in range(10):
            logger.info(f"[LinkedIn] Form step {step + 1} — filling fields...")
            await self._fill_page()
            await self.sleep(1, 2)

            if await self._submit():
                self.applied_count += 1
                logger.info(f"[LinkedIn] SUCCESS — Applied! Total so far: {self.applied_count}")
                await self.sleep(2, 3)
                await self._dismiss()
                return

            if not await self._next_step():
                logger.info("[LinkedIn] Could not advance to next step — closing form.")
                await self._dismiss()
                return

        await self._dismiss()

    # Fields to always skip — not application questions
    SKIP_LABELS = {
        "search", "filter", "recaptcha", "g-recaptcha", "captcha",
        "add a company", "date posted", "city, state", "title, skill",
        "job title", "location", "search by", "sort by",
    }

    def _is_junk_label(self, label: str) -> bool:
        label_lower = label.lower().strip()
        return any(skip in label_lower for skip in self.SKIP_LABELS)

    async def _get_modal(self):
        """Return the Easy Apply modal locator — scopes all field filling inside it."""
        for sel in [
            "div.jobs-easy-apply-modal",
            "div[data-test-modal-id='easy-apply-modal']",
            "div.artdeco-modal[role='dialog']",
            "div[aria-label*='Easy Apply']",
            "div.artdeco-modal__content",
        ]:
            modal = self.page.locator(sel).first
            if await modal.count():
                return modal
        return self.page  # fallback to full page if modal not found

    async def _fill_page(self):
        resume = self.config["personal"].get("resume_path", "")
        modal  = await self._get_modal()

        # Resume upload — inside modal only
        if resume:
            upload = modal.locator("input[type='file']").first
            if await upload.count():
                try:
                    await upload.set_input_files(resume)
                    await self.sleep(1, 2)
                    logger.info("[LinkedIn] Resume uploaded.")
                except Exception:
                    pass

        # Text / number inputs — inside modal only
        for inp in await modal.locator(
            "input[type='text'], input[type='number'], input[type='tel'], textarea"
        ).all():
            try:
                val = await inp.input_value()
                if val:
                    continue
                label = await self.get_label_for(inp)
                if self._is_junk_label(label):
                    continue
                answer = self.qa.answer(label)
                if answer:
                    logger.info(f"[LinkedIn] Filling '{label}' => '{answer}'")
                    await self.human_type_el(inp, answer)
            except Exception:
                pass

        # Selects — inside modal only
        for sel in await modal.locator("select").all():
            try:
                label  = await self.get_label_for(sel)
                if self._is_junk_label(label):
                    continue
                answer = self.qa.answer(label)
                opts   = await sel.locator("option").all_inner_texts()
                match  = next((o for o in opts if answer.lower() in o.lower()), None)
                if match:
                    logger.info(f"[LinkedIn] Selecting '{label}' => '{match}'")
                    await sel.select_option(label=match)
            except Exception:
                pass

        # Radio buttons — inside modal only
        for radio in await modal.locator("input[type='radio']").all():
            try:
                if await radio.is_checked():
                    continue
                rid = await radio.get_attribute("id")
                if not rid:
                    continue
                label_el = modal.locator(f"label[for='{rid}']")
                label_text = await label_el.inner_text()
                try:
                    fieldset = radio.locator("xpath=ancestor::fieldset").first
                    q_text   = await fieldset.locator("legend").inner_text()
                except Exception:
                    q_text = label_text
                if self._is_junk_label(q_text):
                    continue
                answer = self.qa.answer(q_text)
                if answer.lower() in label_text.lower():
                    logger.info(f"[LinkedIn] Radio '{q_text}' => '{label_text}'")
                    await radio.click()
            except Exception:
                pass

    async def _next_step(self) -> bool:
        for label in ["Continue to next step", "Review your application", "Next"]:
            btn = self.page.locator(f"button:has-text('{label}')").first
            if await btn.count():
                await btn.click()
                await self.sleep(1, 2)
                return True
        return False

    async def _submit(self) -> bool:
        for sel in [
            "button:has-text('Submit application')",
            "button[aria-label*='Submit application']",
        ]:
            btn = self.page.locator(sel).first
            if await btn.count():
                await btn.click()
                await self.sleep(2, 3)
                return True
        return False

    async def _dismiss(self):
        for sel in [
            "button[aria-label='Dismiss']",
            "button[aria-label='Dismiss']",
            "button.artdeco-modal__dismiss",
            "button:has-text('Done')",
        ]:
            if await self.click(sel, timeout=3000):
                await self.sleep(1, 2)
                return

    async def _next_page(self) -> bool:
        for sel in [
            "button[aria-label='View next page']",
            "button[aria-label='Next']",
        ]:
            btn = self.page.locator(sel).first
            if await btn.count() and await btn.is_enabled():
                await btn.click()
                await self.sleep(3, 5)
                return True
        return False
