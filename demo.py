#!/usr/bin/env python3
"""
Demo mode — no config.yaml, no login, no applications.
Opens all 3 platforms, searches for jobs, prints what it finds.
"""

import asyncio
import sys
from playwright.async_api import async_playwright

SEARCH_KEYWORD = "Python Developer"
LOCATION       = "Mumbai"
MAX_SHOW       = 5   # jobs to display per platform

# ── colours for terminal output ───────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

STEALTH = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
"""

def banner(platform: str, colour: str):
    print(f"\n{colour}{BOLD}{'-'*50}")
    print(f"  {platform}")
    print(f"{'-'*50}{RESET}")

def job_line(i: int, title: str, company: str, location: str):
    print(f"  {i+1}. {BOLD}{title}{RESET}")
    print(f"     {company}  |  {location}")


# ── LinkedIn ──────────────────────────────────────────────────

async def demo_linkedin(context):
    banner("LinkedIn Jobs", GREEN)
    page = await context.new_page()
    await page.add_init_script(STEALTH)
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={SEARCH_KEYWORD.replace(' ', '%20')}"
        f"&location={LOCATION.replace(' ', '%20')}"
        f"&f_LF=f_AL"
    )
    print(f"  Searching: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    cards = await page.locator("ul.jobs-search__results-list li").all()
    jobs  = []
    for card in cards[:MAX_SHOW]:
        try:
            title    = await card.locator("h3").inner_text(timeout=2000)
            company  = await card.locator("h4").inner_text(timeout=2000)
            location = await card.locator(".job-search-card__location").inner_text(timeout=2000)
            jobs.append((title.strip(), company.strip(), location.strip()))
        except Exception:
            pass

    if jobs:
        print(f"  Found {len(cards)} Easy Apply jobs. Showing top {len(jobs)}:\n")
        for i, (t, c, l) in enumerate(jobs):
            job_line(i, t, c, l)
    else:
        print("  Jobs loaded — LinkedIn requires login to show full listings.")
        print("  (Browser opened — you can see the job page visually.)")

    await asyncio.sleep(3)
    await page.close()


# ── Indeed ────────────────────────────────────────────────────

async def demo_indeed(context):
    banner("Indeed Jobs", YELLOW)
    page = await context.new_page()
    await page.add_init_script(STEALTH)
    url = (
        f"https://www.indeed.com/jobs"
        f"?q={SEARCH_KEYWORD.replace(' ', '+')}"
        f"&l={LOCATION.replace(' ', '+')}"
        f"&fromage=7"
    )
    print(f"  Searching: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    cards = await page.locator(".job_seen_beacon, .resultContent").all()
    jobs  = []
    for card in cards[:MAX_SHOW]:
        try:
            title   = await card.locator("h2 span, .jobTitle span").first.inner_text(timeout=2000)
            company = await card.locator("[data-testid='company-name'], .companyName").first.inner_text(timeout=2000)
            loc     = await card.locator("[data-testid='text-location'], .companyLocation").first.inner_text(timeout=2000)
            easy    = await card.locator("text=Easily apply").count()
            jobs.append((title.strip(), company.strip(), loc.strip(), easy > 0))
        except Exception:
            pass

    if jobs:
        print(f"  Found {len(cards)} jobs. Showing top {len(jobs)}:\n")
        for i, (t, c, l, easy) in enumerate(jobs):
            tag = f"  {GREEN}[Easy Apply]{RESET}" if easy else ""
            print(f"  {i+1}. {BOLD}{t}{RESET}{tag}")
            print(f"     {c}  |  {l}")
    else:
        print("  Page loaded — check the browser window to see Indeed results.")

    await asyncio.sleep(3)
    await page.close()


# ── Naukri ────────────────────────────────────────────────────

async def demo_naukri(context):
    banner("Naukri Jobs", CYAN)
    page = await context.new_page()
    await page.add_init_script(STEALTH)
    slug = SEARCH_KEYWORD.lower().replace(" ", "-")
    url  = f"https://www.naukri.com/{slug}-jobs?jobAge=7"
    print(f"  Searching: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(3)

    cards = await page.locator("article.jobTuple, .cust-job-tuple").all()
    jobs  = []
    for card in cards[:MAX_SHOW]:
        try:
            title   = await card.locator("a.title, .title").first.inner_text(timeout=2000)
            company = await card.locator("a.subTitle, .companyInfo a").first.inner_text(timeout=2000)
            loc     = await card.locator(".location, li.location span").first.inner_text(timeout=2000)
            jobs.append((title.strip(), company.strip(), loc.strip()))
        except Exception:
            pass

    if jobs:
        print(f"  Found {len(cards)} jobs. Showing top {len(jobs)}:\n")
        for i, (t, c, l) in enumerate(jobs):
            job_line(i, t, c, l)
    else:
        print("  Page loaded — check the browser window to see Naukri results.")

    await asyncio.sleep(3)
    await page.close()


# ── Main ──────────────────────────────────────────────────────

async def main():
    print(f"\n{BOLD}{'='*50}")
    print("  Job Auto Apply - DEMO MODE")
    print("  Created by zxdevelopers")
    print(f"  Keyword : {SEARCH_KEYWORD}")
    print(f"  Location: {LOCATION}")
    print(f"  No login | No applications | Just browsing")
    print(f"{'='*50}{RESET}\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        await asyncio.gather(
            demo_linkedin(context),
            demo_indeed(context),
            demo_naukri(context),
        )

        print(f"\n{BOLD}{'='*50}")
        print("  Demo complete!")
        print("  Fill in config.yaml and run: python main.py")
        print(f"{'='*50}{RESET}")

        await asyncio.sleep(2)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
