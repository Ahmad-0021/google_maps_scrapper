# scrapper/core.py
import logging
import platform
import random
import time
from typing import List
from contextlib import contextmanager

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from .models import Place
from .extractors import extract_place
from .reviews import extract_reviews
from .utils import save_reviews_to_csv


class BrowserManager:
    """
    A reusable class to manage Playwright browser lifecycle with consistent configuration.
    Adds stealth and human-like behavior.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None

    def start(self):
        """Launch browser with stealth settings."""
        self.playwright = sync_playwright().start()

        executable_path = (
            r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            if platform.system() == "Windows" else None
        )

        self.browser = self.playwright.chromium.launch(
            executable_path=executable_path,
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-infobars',
                '--start-maximized',
                '--disable-notifications',
                '--disable-geolocation',
                '--no-first-run',
                '--no-default-browser-check'
            ]
        )

        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            ignore_https_errors=True
        )

        # Stealth: Hide automation flags
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            window.chrome = {
                runtime: {},
                loadTimes: () => {},
                csi: () => {}
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)

        return self

    def new_page(self) -> Page:
        page = self.context.new_page()
        # Extra stealth: remove Playwright headers
        page.set_extra_http_headers({"sec-fetch-site": "none"})
        return page

    def close(self):
        """Safely close browser and Playwright."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    @contextmanager
    def get_page(self):
        """Context manager for safe page usage."""
        page = self.new_page()
        try:
            yield page
        except Exception as e:
            logging.error(f"Error in page context: {e}")
            raise
        finally:
            page.close()


class GoogleMapsScraper:
    """
    Scraper for Google Maps places and reviews.
    Uses human-like delays and stealth techniques.
    """
    BASE_URL = "https://www.google.com/maps"

    def __init__(self, headless: bool = False):
        self.browser_manager = BrowserManager(headless=headless)

    def scrape_places(self, search_for: str, total: int) -> List[Place]:
        places: List[Place] = []
        try:
            self.browser_manager.start()
            with self.browser_manager.get_page() as page:
                logging.info("🌍 Navigating to Google Maps...")
                page.goto(self.BASE_URL, timeout=60000)
                time.sleep(random.uniform(2.0, 4.0))  # Natural pause after load

                # Search query
                logging.info(f"🔍 Searching for: {search_for}")
                search_box = page.locator('//input[@id="searchboxinput"]')
                search_box.fill(search_for)
                page.keyboard.press("Enter")
                time.sleep(1.5)

                # Wait for results
                try:
                    page.wait_for_selector('//a[contains(@href, "/maps/place/")]', timeout=15000)
                    logging.info("✅ Search results loaded")
                except Exception:
                    logging.error("❌ No results found or timeout")
                    return places

                # Scroll to load more places
                listings_locator = page.locator('//a[contains(@href, "/maps/place/")]')
                previously_counted = 0
                scroll_attempts = 0

                while scroll_attempts < 20:
                    page.mouse.wheel(0, 10000)
                    time.sleep(random.uniform(1.0, 2.5))  # Random scroll delay
                    found = listings_locator.count()
                    logging.info(f"📌 Found {found} places during scrolling")

                    if found >= total:
                        break
                    if found == previously_counted:
                        scroll_attempts += 1
                        if scroll_attempts >= 3:
                            logging.info("🛑 No more new places loading.")
                            break
                    else:
                        scroll_attempts = 0
                    previously_counted = found

                # Get listings
                raw_listings = listings_locator.all()[:total]
                listings = [listing.locator("xpath=..") for listing in raw_listings]
                logging.info(f"📬 Processing {len(listings)} place listings...")

                # Process each place
                for idx, listing in enumerate(listings):
                    try:
                        logging.info(f"📍 Processing place {idx + 1}/{len(listings)}")

                        # Human-like delay before interaction
                        time.sleep(random.uniform(1.5, 3.5))

                        # Click listing
                        listing.click()
                        logging.info("⏳ Waiting for place details to load...")
                        page.wait_for_timeout(3000)
                        page.wait_for_timeout(random.randint(1000, 2000))  # Extra jitter

                        # Extract data
                        place = extract_place(page)
                        if not place.name or place.name in ["", "Unknown", "Failed to extract"]:
                            logging.warning(f"⚠️ Skipping place {idx + 1} - invalid name: {place.name}")
                            continue

                        logging.info(f"💬 Extracting reviews for: {place.name}")
                        reviews = extract_reviews(page)
                        place.reviews = reviews
                        places.append(place)

                        # Log success
                        logging.info(
                            f"✅ Added: {place.name} | "
                            f"⭐ {place.rating or 'N/A'} | "
                            f"🏠 {len(reviews)} reviews | "
                            f"📞 {'Yes' if place.phone else 'No'}"
                        )

                        # Save reviews
                        if reviews:
                            save_reviews_to_csv(place.name, reviews)
                            logging.info(f"💾 Saved {len(reviews)} reviews to CSV")
                        else:
                            logging.info(f"📝 No reviews found for {place.name}")

                        # 🕐 Human-like pause after reading a place
                        wait_time = random.uniform(2.5, 6.0)
                        logging.info(f"⏸️  Sleeping for {wait_time:.2f}s before next place...")
                        time.sleep(wait_time)

                    except Exception as e:
                        logging.error(f"❌ Failed processing listing {idx + 1}: {str(e)}")
                        time.sleep(random.uniform(1.0, 3.0))  # Recover from error
                        continue

        except Exception as e:
            logging.error(f"🚨 Scraping error: {str(e)}")
        finally:
            self.browser_manager.close()

        logging.info(f"🎉 Scraping completed! Extracted {len(places)} places.")
        return places


# 🔥 Top-level function expected by main.py
def scrape_places(search_for: str, total: int) -> List[Place]:
    """
    Public interface for scraping Google Maps places.
    Used by main.py.
    """
    scraper = GoogleMapsScraper(headless=False)  # Set to True in production
    return scraper.scrape_places(search_for, total)