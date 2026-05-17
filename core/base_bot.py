import asyncio
import random
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext, Playwright

logger = logging.getLogger(__name__)

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
"""


class BaseBot:
    def __init__(self, config: dict, platform: str):
        self.config = config
        self.platform = platform
        self.applied_count = 0
        self.max_applications = config["search"].get("max_applications", 50)
        self.profile_dir = Path(__file__).parent.parent / "profile" / platform
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self._playwright: Playwright = None
        self.context: BrowserContext = None
        self.page: Page = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self.context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=False,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self.context.on("page", self._on_new_page)
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        await self.page.add_init_script(STEALTH_SCRIPT)
        logger.info(f"[{self.platform}] Browser started.")

    async def _on_new_page(self, page: Page):
        await page.add_init_script(STEALTH_SCRIPT)

    async def stop(self):
        if self.context:
            await self.context.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info(f"[{self.platform}] Browser closed. Applied: {self.applied_count}")

    async def human_type(self, selector: str, text: str, clear: bool = True):
        if clear:
            await self.page.fill(selector, "")
        await self.page.type(selector, str(text), delay=random.randint(40, 100))

    async def human_type_el(self, element, text: str):
        await element.fill("")
        await element.type(str(text), delay=random.randint(40, 100))

    async def sleep(self, min_sec: float = 1.0, max_sec: float = 3.0):
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def find(self, selector: str, timeout: int = 8000):
        try:
            el = self.page.locator(selector).first
            await el.wait_for(timeout=timeout)
            return el
        except Exception:
            return None

    async def click(self, selector: str, timeout: int = 8000) -> bool:
        try:
            await self.page.locator(selector).first.click(timeout=timeout)
            return True
        except Exception:
            return False

    async def is_logged_in(self, url: str, indicator_selector: str) -> bool:
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.sleep(2, 3)
        try:
            await self.page.wait_for_selector(indicator_selector, timeout=5000)
            return True
        except Exception:
            return False

    async def get_label_for(self, element) -> str:
        try:
            el_id = await element.get_attribute("id")
            if el_id:
                label = self.page.locator(f"label[for='{el_id}']")
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
