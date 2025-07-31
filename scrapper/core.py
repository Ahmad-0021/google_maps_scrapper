# scrapper/core.py
import logging
import platform
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
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None

    def start(self):
        """Launch browser and create context."""
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
                '--start-maximized'
            ]
        )

        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            ignore_https_errors=True
        )

        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)

        return self

    def new_page(self) -> Page:
        page = self.context.new_page()
        return page

    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    @contextmanager
    def get_page(self):
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
    Main scraper class.
    """
    BASE_URL = "https://www.google.com/maps"  # ← Removed extra spaces

    def __init__(self, headless: bool = False):
        self.browser_manager = BrowserManager(headless=headless)

    def scrape_places(self, search_for: str, total: int) -> List[Place]:
        places: List[Place] = []
        try:
            self.browser_manager.start()
            with self.browser_manager.get_page() as page:
                logging.info("Navigating to Google Maps...")
                page.goto(self.BASE_URL, timeout=60000)
                page.wait_for_timeout(3000)

                logging.info(f"Searching for: {search_for}")
                search_box = page.locator('//input[@id="searchboxinput"]')
                search_box.fill(search_for)
                page.keyboard.press("Enter")

                page.wait_for_selector('//a[contains(@href, "/maps/place/")]', timeout=15000)
                logging.info("Search results loaded")

                listings_locator = page.locator('//a[contains(@href, "/maps/place/")]')
                previously_counted = 0
                scroll_attempts = 0

                while scroll_attempts < 20:
                    page.mouse.wheel(0, 10000)
                    page.wait_for_timeout(1000)
                    found = listings_locator.count()
                    logging.info(f"Found {found} places during scrolling")

                    if found >= total:
                        break
                    if found == previously_counted:
                        scroll_attempts += 1
                        if scroll_attempts >= 3:
                            break
                    else:
                        scroll_attempts = 0
                    previously_counted = found

                listings = listings_locator.all()[:total]
                listings = [listing.locator("xpath=..") for listing in listings]
                logging.info(f"Processing {len(listings)} place listings...")

                for idx, listing in enumerate(listings):
                    try:
                        logging.info(f"Processing place {idx + 1}/{len(listings)}")
                        listing.click()
                        page.wait_for_timeout(3000)

                        place = extract_place(page)
                        if not place.name or place.name in ["", "Unknown", "Failed to extract"]:
                            logging.warning(f"Skipping place {idx + 1} - invalid name: {place.name}")
                            continue

                        logging.info(f"Extracting reviews for: {place.name}")
                        reviews = extract_reviews(page)
                        place.reviews = reviews
                        places.append(place)

                        logging.info(
                            f"✅ Added: {place.name} | Reviews: {len(reviews)} | Rating: {place.rating} | Address: {'Yes' if place.address else 'No'}"
                        )

                        if reviews:
                            save_reviews_to_csv(place.name, reviews)
                            logging.info(f"💾 Saved {len(reviews)} reviews for {place.name}")
                        else:
                            logging.warning(f"⚠️ No reviews found for {place.name}")

                    except Exception as e:
                        logging.error(f"❌ Failed processing listing {idx + 1}: {str(e)}")
                        continue

        except Exception as e:
            logging.error(f"❌ Scraping error: {str(e)}")
        finally:
            self.browser_manager.close()

        logging.info(f"🎉 Scraping completed! Extracted {len(places)} places.")
        return places


# 🔥 Add this: Top-level function expected by main.py
def scrape_places(search_for: str, total: int) -> List[Place]:
    """
    Convenience function that matches the expected interface in main.py.
    """
    scraper = GoogleMapsScraper(headless=False)  # You can make headless configurable
    return scraper.scrape_places(search_for, total)