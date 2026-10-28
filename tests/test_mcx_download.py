
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.mcxindia.com/market-data/bhavcopy"
TEST_DATE = "2026-10-15"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        print("Opening MCX...")
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Select the requested date
        await page.locator("#bhavCopyDateWise").fill(TEST_DATE)

        # Click Show
        await page.locator("#btnDateWise").click()
        await page.wait_for_timeout(4000)

        # Verify visible table date
        body_text = await page.locator("body").inner_text()

        if "15 Oct 2026" not in body_text:
            print("ERROR: Requested date not found in table.")
            await browser.close()
            return

        print("Table date verified: 15 Oct 2026")

        # Trigger CSV download and save it
        async with page.expect_download(timeout=30000) as download_info:
            await page.locator("#btnDateWiseCSV").click()

        download = await download_info.value

        output_dir = Path("data/test_downloads")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "BhavCopyDateWise_15102026.csv"
        await download.save_as(output_path)

        print("Download saved to:", output_path)
        print("Original filename:", download.suggested_filename)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
