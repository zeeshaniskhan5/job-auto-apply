import asyncio
import logging
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from core.base_bot import BaseBot
from core.qa_engine import QAEngine

logger = logging.getLogger(__name__)

HOME_URL = "https://www.indeed.com/"
LOGIN_URL = "https://secure.indeed.com/auth?hl=en_IN&co=IN"
JOBS_URL  = "https://www.indeed.com/jobs?q={keywords}&l={location}&fromage=7&iafilter=1"


class IndeedBot(BaseBot):
    def __init__(self, config: dict):
        super().__init__(config, "indeed")
        self.creds  = config["indeed"]
        self.search = config["search"]
        self.qa     = QAEngine(config)

    # ── Auth ──────────────────────────────────────────────────

    async def login(self):
        await self.page.goto(HOME_URL, wait_until="domcontentloaded")
        await self.sleep(2, 3)

        # Check session via sign-in link absence
        if not await self.page.locator("a[href*='login'], a[href*='signin']").count():
            logger.info("[Indeed] Already logged in via saved session.")
            return

        await self.page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await self.sleep(2, 3)

        email_sel = "input[type='email'], input[name='__email'], #ifl-InputFormField-3"
        await self.human_type(email_sel, self.creds["email"])
        await self.click("button[type='submit']")
        await self.sleep(2, 3)

        await self.human_type("input[type='password']", self.creds["password"])
        await self.click("button[type='submit']")
        await self.sleep(4, 6)
        logger.info("[Indeed] Login attempted — solve CAPTCHA in browser if prompted.")

    # ── Main run loop ─────────────────────────────────────────

    async def run(self):
        await self.start()
        await self.login()

        keywords = self.search.get("keywords", "Software Engineer")
        location = self.search.get("location", "India")
        url = JOBS_URL.format(
            keywords=keywords.replace(" ", "+"),
            location=location.replace(" ", "+"),
        )
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.sleep(3, 5)

        while self.applied_count < self.max_applications:
            cards = await self.page.locator(
                "div.job_seen_beacon, .resultContent"
            ).all()
            if not cards:
                logger.info("[Indeed] No job cards found.")
                break

            for card in cards:
                if self.applied_count >= self.max_applications:
                    break
                try:
                    easy_apply = card.locator(
                        "text=Easily apply, text=Easy Apply"
                    )
                    if not await easy_apply.count():
                        continue
                    title = card.locator("h2 a, .jobTitle a").first
                    await title.click()
                    await self.sleep(2, 4)
                    await self._apply()
                except Exception as e:
                    logger.warning(f"[Indeed] Skipping card: {e}")

            if not await self._next_page():
                break

        await self.stop()

    # ── Apply flow ────────────────────────────────────────────

    async def _apply(self):
        apply_btn = self.page.locator(
            "button:has-text('Apply now'), button:has-text('Apply on')"
        ).first
        try:
            await apply_btn.wait_for(timeout=5000)
        except PlaywrightTimeout:
            return

        # Playwright handles new tab natively
        async with self.context.expect_page() as new_page_info:
            await apply_btn.click()

        try:
            new_page: Page = await new_page_info.value
            await new_page.wait_for_load_state("domcontentloaded")
            await self._fill_form(new_page)
            await new_page.close()
        except Exception:
            # No new tab — form is inline
            await self._fill_form(self.page)

    async def _fill_form(self, page: Page):
        resume = self.config["personal"].get("resume_path", "")
        max_steps = 10

        for _ in range(max_steps):
            await asyncio.sleep(1.5)

            # Resume upload
            if resume:
                upload = page.locator("input[type='file']").first
                if await upload.count():
                    try:
                        await upload.set_input_files(resume)
                        await asyncio.sleep(1)
                    except Exception:
                        pass

            # Text / number / textarea
            for inp in await page.locator(
                "input[type='text'], input[type='number'], textarea"
            ).all():
                try:
                    if await inp.input_value():
                        continue
                    label = await self._get_label(page, inp)
                    answer = self.qa.answer(label)
                    if answer:
                        await inp.fill("")
                        await inp.type(answer, delay=50)
                except Exception:
                    pass

            # Selects
            for sel in await page.locator("select").all():
                try:
                    label  = await self._get_label(page, sel)
                    answer = self.qa.answer(label)
                    opts   = await sel.locator("option").all_inner_texts()
                    match  = next((o for o in opts if answer.lower() in o.lower()), None)
                    if match:
                        await sel.select_option(label=match)
                except Exception:
                    pass

            # Radios
            for radio in await page.locator("input[type='radio']").all():
                try:
                    if await radio.is_checked():
                        continue
                    rid = await radio.get_attribute("id")
                    label_el = page.locator(f"label[for='{rid}']")
                    label_text = await label_el.inner_text()
                    fieldset = radio.locator("xpath=ancestor::fieldset").first
                    q_text = await fieldset.locator("legend").inner_text()
                    answer = self.qa.answer(q_text)
                    if answer.lower() in label_text.lower():
                        await radio.click()
                except Exception:
                    pass

            # Submit
            submit = page.locator(
                "button:has-text('Submit your application'), "
                "button:has-text('Submit application')"
            ).first
            if await submit.count():
                await submit.click()
                await asyncio.sleep(2)
                self.applied_count += 1
                logger.info(f"[Indeed] Applied! Total: {self.applied_count}")
                return

            # Next / Continue
            continued = False
            for label in ["Continue", "Next", "Review your application"]:
                btn = page.locator(f"button:has-text('{label}')").first
                if await btn.count():
                    await btn.click()
                    await asyncio.sleep(1.5)
                    continued = True
                    break
            if not continued:
                logger.warning("[Indeed] Could not progress form — skipping.")
                return

    async def _get_label(self, page: Page, element) -> str:
        try:
            el_id = await element.get_attribute("id")
            if el_id:
                label = page.locator(f"label[for='{el_id}']")
                if await label.count():
                    return (await label.inner_text()).strip()
        except Exception:
            pass
        for attr in ("placeholder", "aria-label", "name"):
            try:
                val = await element.get_attribute(attr)
                if val:
                    return val.strip()
            except Exception:
                pass
        return ""

    async def _next_page(self) -> bool:
        btn = self.page.locator("a[data-testid='pagination-page-next']").first
        if await btn.count():
            await btn.click()
            await self.sleep(3, 5)
            return True
        return False
