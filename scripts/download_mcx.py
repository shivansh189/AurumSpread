
import asyncio
import argparse
import calendar
import csv
import io
import time
from datetime import date, datetime
from pathlib import Path

from playwright.async_api import async_playwright


URL = "https://www.mcxindia.com/market-data/bhavcopy"
RAW_DIR = Path("data/raw")
LOG_FILE = Path("data/mcx_download_log.txt")

# Wait between requests so we don't overload the MCX website.
WAIT_BETWEEN_DOWNLOADS = 2

# Number of times to retry a failed date.
MAX_RETRIES = 3


def expected_date_text(day):
    """Convert a date to the date format shown on the MCX page."""
    return day.strftime("%d %b %Y")


def expected_filename(day):
    """Create the expected MCX filename."""
    return f"BhavCopyDateWise_{day.strftime('%d%m%Y')}.csv"


def is_valid_csv(path, requested_date):
    """Check that the CSV contains the requested trading date."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or "Date" not in reader.fieldnames:
                return False

            dates_found = set()

            for row in reader:
                raw_date = (row.get("Date") or "").strip()

                if not raw_date:
                    continue

                try:
                    parsed_date = datetime.strptime(
                        raw_date, "%d %b %Y"
                    ).date()
                    dates_found.add(parsed_date)
                except ValueError:
                    continue

        return dates_found == {requested_date}

    except Exception:
        return False


def month_dates(year, month):
    """Generate weekdays for the requested month."""
    last_day = calendar.monthrange(year, month)[1]

    for day_number in range(1, last_day + 1):
        current = date(year, month, day_number)

        # Skip Saturdays and Sundays.
        if current.weekday() < 5:
            yield current


async def download_one_date(page, day):
    filename = expected_filename(day)
    destination = RAW_DIR / filename

    # If an existing file is correct, don't download it again.
    if destination.exists() and is_valid_csv(destination, day):
        print(f"SKIP already verified: {filename}")
        return True

    date_text = expected_date_text(day)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(
                f"Downloading {date_text} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

            # Set the date in the MCX date picker.
            await page.locator("#bhavCopyDateWise").fill(
                day.strftime("%Y-%m-%d")
            )

            # Click Show and wait for results.
            await page.locator("#btnDateWise").click()
            await page.wait_for_timeout(2500)

            # Verify the requested date appears in the page.
            body_text = await page.locator("body").inner_text()

            if date_text not in body_text:
                raise RuntimeError(
                    f"Page did not display expected date: {date_text}"
                )

            # Trigger the CSV export.
            async with page.expect_download(timeout=30000) as download_info:
                await page.locator("#btnDateWiseCSV").click()

            download = await download_info.value

            # Save temporarily, then validate before replacing the final file.
            temporary_path = RAW_DIR / f"temp_{filename}"
            await download.save_as(temporary_path)

            if not is_valid_csv(temporary_path, day):
                temporary_path.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Downloaded CSV did not contain only {date_text}"
                )

            # Replace any incorrect old file only after validation succeeds.
            temporary_path.replace(destination)

            print(f"SUCCESS: {filename}")
            return True

        except Exception as error:
            print(f"FAILED attempt {attempt}: {error}")

            if attempt < MAX_RETRIES:
                await page.wait_for_timeout(3000)

    print(f"ERROR: Could not download {date_text}")
    return False


async def main(year, month):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    dates = list(month_dates(year, month))

    print(f"\nMCX monthly downloader")
    print(f"Month: {calendar.month_name[month]} {year}")
    print(f"Weekdays to check: {len(dates)}")
    print(f"Output folder: {RAW_DIR.resolve()}\n")

    successful = 0
    failed_dates = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        print("Opening MCX...")
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        for day in dates:
            success = await download_one_date(page, day)

            if success:
                successful += 1
            else:
                failed_dates.append(day)

            # Pause between dates.
            await page.wait_for_timeout(
                WAIT_BETWEEN_DOWNLOADS * 1000
            )

        await browser.close()

    print("\n========== SUMMARY ==========")
    print(f"Successful/verified: {successful}")
    print(f"Failed dates: {len(failed_dates)}")

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(
            f"\nRun: {year}-{month:02d} | "
            f"Success: {successful} | "
            f"Failed: {len(failed_dates)}\n"
        )

        for day in failed_dates:
            log.write(f"FAILED: {day.isoformat()}\n")

    if failed_dates:
        print("\nDates to retry:")
        for day in failed_dates:
            print(day.isoformat())

    print(f"\nLog saved to: {LOG_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download MCX Bhav Copy for one month."
    )

    parser.add_argument(
        "--month",
        type=int,
        required=True,
        help="Month number, e.g. 7 for July",
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year, e.g. 2026",
    )

    args = parser.parse_args()

    if args.month < 1 or args.month > 12:
        raise ValueError("Month must be between 1 and 12.")

    asyncio.run(main(args.year, args.month))
