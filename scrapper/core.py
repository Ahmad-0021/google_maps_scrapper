import platform
import logging
from typing import List
from playwright.sync_api import sync_playwright
from .models import Place
from .extractors import extract_place
from .reviews import extract_reviews
from .utils import save_reviews_to_csv

def scrape_places(search_for: str, total: int) -> List[Place]:
    places: List[Place] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=(
                r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
                if platform.system() == "Windows" else None
            ),
            headless=False,
            args=[
                '--no-sandbox', 
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        
        page = context.new_page()

        try:
            logging.info("Navigating to Google Maps...")
            page.goto("https://www.google.com/maps", timeout=60000)
            page.wait_for_timeout(3000)
            
            # Search for places
            logging.info(f"Searching for: {search_for}")
            search_box = page.locator('//input[@id="searchboxinput"]')
            search_box.fill(search_for)
            page.keyboard.press("Enter")
            
            # Wait for results
            page.wait_for_selector('//a[contains(@href, "/maps/place/")]', timeout=15000)
            logging.info("Search results loaded")

            # Scroll to load more places
            page.hover('//a[contains(@href, "/maps/place/")]')
            previously_counted = scroll_attempts = 0

            while scroll_attempts < 20:
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(1000)
                found = page.locator('//a[contains(@href, "/maps/place/")]').count()
                logging.info(f"Found: {found}")

                if found >= total:
                    break
                if found == previously_counted:
                    scroll_attempts += 1
                    if scroll_attempts >= 3:
                        break
                else:
                    scroll_attempts = 0
                previously_counted = found

            # Get place listings
            listings = page.locator('//a[contains(@href, "/maps/place/")]').all()[:total]
            listings = [listing.locator("xpath=..") for listing in listings]
            logging.info(f"Processing {len(listings)} listings...")

            for idx, listing in enumerate(listings):
                try:
                    logging.info(f"Processing place {idx + 1}/{len(listings)}")
                    
                    # Click on the listing
                    listing.click()
                    page.wait_for_timeout(3000)

                    # Extract place information
                    place = extract_place(page)
                    
                    # Validate that we got at least a name
                    if not place.name or place.name in ["", "Unknown", "Failed to extract"]:
                        logging.warning(f"Skipping place {idx + 1} - no valid name extracted")
                        continue

                    # Extract reviews
                    logging.info(f"Extracting reviews for: {place.name}")
                    reviews = extract_reviews(page)
                    place.reviews = reviews

                    places.append(place)
                    logging.info(
                        f"✅ Added: {place.name} | Reviews: {len(reviews)} | Rating: {place.rating} | Address: {'Yes' if place.address else 'No'}"
                    )

                    # Save reviews to CSV if we have any
                    if reviews:
                        save_reviews_to_csv(place.name, reviews)
                        logging.info(f"💾 Saved {len(reviews)} reviews for {place.name}")
                    else:
                        logging.warning(f"⚠️  No reviews found for {place.name}")

                except Exception as e:
                    logging.error(f"❌ Failed processing listing {idx + 1}: {str(e)}")
                    continue

        except Exception as e:
            logging.error(f"❌ Scraping error: {str(e)}")

        finally:
            browser.close()

    logging.info(f"🎉 Scraping completed! Extracted {len(places)} places total.")
    return places