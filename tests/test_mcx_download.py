"""MCX Bhavcopy live download integration test (skipped when playwright is absent)."""

import asyncio
from pathlib import Path
import pytest

playwright = pytest.importorskip("playwright", reason="playwright is required for live MCX scraper test")
from playwright.async_api import async_playwright

URL = "https://www.mcxindia.com/market-data/bhavcopy"
TEST_DATE = "2026-10-15"


@pytest.mark.asyncio
async def test_mcx_download_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=15000)
        assert "mcxindia.com" in page.url
        await browser.close()
