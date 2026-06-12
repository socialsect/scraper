"""Shared Playwright browser pool with stealth settings."""

import asyncio
import random
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
"""

CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]


async def dismiss_consent(page: Page) -> None:
    """Click common cookie/consent buttons if present."""
    selectors = [
        'button:has-text("Accept all")',
        'button:has-text("Accept All")',
        'button:has-text("I agree")',
        'button:has-text("Agree")',
        'button[id="L2AGLb"]',
        'button:has-text("Reject all")',
        '[aria-label="Accept all"]',
    ]
    for selector in selectors:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=800):
                await btn.click(timeout=2000)
                await asyncio.sleep(0.3)
                return
        except Exception:
            continue


class PlaywrightPool:
    """Manages a shared browser with a semaphore-limited context pool."""

    def __init__(self, max_workers: int = 4, headless: bool = True):
        self.max_workers = max_workers
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._sem: asyncio.Semaphore | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=CHROMIUM_ARGS,
        )
        self._sem = asyncio.Semaphore(self.max_workers)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None

    async def _new_stealth_context(self) -> BrowserContext:
        assert self._browser is not None
        viewport = random.choice([
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
        ])
        context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport=viewport,
            locale="en-US",
            timezone_id="America/New_York",
            color_scheme="light",
        )
        await context.add_init_script(STEALTH_INIT_SCRIPT)
        return context

    @asynccontextmanager
    async def acquire_context(self):
        assert self._sem is not None
        async with self._sem:
            context = await self._new_stealth_context()
            try:
                yield context
            finally:
                await context.close()

    @asynccontextmanager
    async def acquire_page(self):
        async with self.acquire_context() as context:
            page = await context.new_page()
            try:
                yield page
            finally:
                await page.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()
