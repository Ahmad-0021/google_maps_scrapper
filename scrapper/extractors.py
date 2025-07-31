from playwright.sync_api import Page
import re
import logging
from .models import Place

def extract_text(page: Page, xpath: str) -> str:
    """Extract text from page using xpath selector"""
    try:
        if page.locator(xpath).count() > 0:
            return page.locator(xpath).inner_text().strip()
    except Exception as e:
        logging.debug(f"Failed to extract text with xpath {xpath}: {e}")
    return ""

def extract_image_url(page: Page) -> str:
    """Extract image URL from the place page"""
    try:
        page.wait_for_timeout(1000)
        selectors = [
            '//div[contains(@class, "ZKCDEc")]//img',
            '//div[contains(@class, "UCw5gc")]//img',
            '//img[contains(@class, "wXeWr")]',
            '//button[@jsaction*="hero"]//img',
            '//div[@data-value="Photo"]//img',
            '//div[contains(@class, "AoGLv")]//img',
            '//img[contains(@src, "googleusercontent")]',  # Common Google image pattern
            '//img[contains(@class, "RZ66Rb")]'  # Another common class
        ]
        
        for selector in selectors:
            try:
                img_locator = page.locator(selector)
                if img_locator.count() > 0:
                    for i in range(min(3, img_locator.count())):
                        src = img_locator.nth(i).get_attribute("src")
                        if src and is_valid_image_url(src):
                            logging.info(f"Found image URL: {src[:50]}...")
                            return src
            except Exception as e:
                logging.debug(f"Failed with selector {selector}: {e}")
                continue
        
        # Try background images
        bg_elements = page.locator('//div[contains(@style, "background-image")]')
        if bg_elements.count() > 0:
            for i in range(min(3, bg_elements.count())):
                try:
                    style = bg_elements.nth(i).get_attribute("style")
                    if style and "url(" in style:
                        url_match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                        if url_match and is_valid_image_url(url_match.group(1)):
                            return url_match.group(1)
                except:
                    continue
                    
        logging.warning("No valid image URL found")
    except Exception as e:
        logging.error(f"Error extracting image URL: {e}")
    
    return ""

def is_valid_image_url(url: str) -> bool:
    """Check if URL is a valid image URL"""
    if not url or len(url) < 10:
        return False
    
    invalid_patterns = [
        "data:image/svg", "placeholder", "blank.gif", 
        "spacer.gif", "1x1.png", "loading.gif", "default"
    ]
    
    if any(pattern in url.lower() for pattern in invalid_patterns):
        return False
    
    # Check for valid URL format
    return url.startswith(('http://', 'https://')) or url.startswith('//')

def extract_place(page: Page) -> Place:
    """Extract place information from Google Maps page"""
    place = Place()  # Now this works because all fields have defaults
    
    try:
        # Wait for the place info to load
        try:
            page.wait_for_selector('//h1[contains(@class, "DUwDvf")]', timeout=5000)
        except:
            logging.warning("Place title selector not found, continuing anyway...")
        
        # Extract name - try multiple selectors
        name_selectors = [
            '//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]',
            '//h1[contains(@class, "DUwDvf")]',
            '//h1[@data-attrid="title"]',
            '//div[contains(@class, "SPZz6b")]//h1'
        ]
        
        for selector in name_selectors:
            name = extract_text(page, selector)
            if name:
                place.name = name
                logging.info(f"Extracted name: {name}")
                break
        
        # Extract address
        address_selectors = [
            '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]',
            '//div[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]',
            '//span[contains(@class, "LrzXr")]',
            '//div[contains(@class, "AeaXub")]//div[contains(@class, "fontBodyMedium")]'
        ]
        
        for selector in address_selectors:
            address = extract_text(page, selector)
            if address:
                place.address = address
                logging.info(f"Extracted address: {address[:50]}...")
                break
        
        # Extract website
        website_selectors = [
            '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]',
            '//a[@data-item-id="authority"]',
            '//a[contains(@href, "http") and not(contains(@href, "google"))]/@href'
        ]
        
        for selector in website_selectors:
            website = extract_text(page, selector)
            if website and website.startswith(('http://', 'https://')):
                place.website = website
                logging.info(f"Extracted website: {website}")
                break
        
        # Extract phone number
        phone_selectors = [
            '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]',
            '//div[contains(@data-item-id, "phone")]//div[contains(@class, "fontBodyMedium")]',
            '//a[starts-with(@href, "tel:")]',
            '//span[contains(@class, "LrzXr") and contains(text(), "+")]'
        ]
        
        for selector in phone_selectors:
            phone = extract_text(page, selector)
            if phone:
                place.phone = phone
                place.phone_number = phone  # Set both fields
                logging.info(f"Extracted phone: {phone}")
                break
        
        # Extract reviews count
        reviews_count_selectors = [
            '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span//span//span[@aria-label]',
            '//span[contains(@aria-label, "reviews")]',
            '//div[contains(@class, "dmRWX")]//span[contains(text(), "(")]'
        ]
        
        for selector in reviews_count_selectors:
            reviews_count_raw = extract_text(page, selector)
            if reviews_count_raw:
                try:
                    # Extract number from text like "(1,234 reviews)" or "1,234"
                    import re
                    numbers = re.findall(r'[\d,]+', reviews_count_raw.replace('\xa0', ''))
                    if numbers:
                        count = int(numbers[0].replace(',', ''))
                        place.review_count = count
                        place.reviews_count = count  # Set both fields
                        logging.info(f"Extracted review count: {count}")
                        break
                except Exception as e:
                    logging.debug(f"Failed to parse review count '{reviews_count_raw}': {e}")
        
        # Extract rating
        rating_selectors = [
            '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span[@aria-hidden]',
            '//span[contains(@class, "ceNzKf")]',
            '//div[contains(@class, "dmRWX")]//span[not(contains(text(), "("))]'
        ]
        
        for selector in rating_selectors:
            rating_raw = extract_text(page, selector)
            if rating_raw:
                try:
                    # Clean and convert rating
                    rating_clean = rating_raw.replace(' ', '').replace(',', '.')
                    # Extract first number that looks like a rating (1.0-5.0)
                    import re
                    rating_match = re.search(r'([1-5][\.,]?\d?)', rating_clean)
                    if rating_match:
                        rating = float(rating_match.group(1).replace(',', '.'))
                        if 1.0 <= rating <= 5.0:
                            place.rating = rating
                            place.reviews_average = rating  # Set both fields
                            logging.info(f"Extracted rating: {rating}")
                            break
                except Exception as e:
                    logging.debug(f"Failed to parse rating '{rating_raw}': {e}")
        
        # Extract image URL
        place.image_url = extract_image_url(page)
        
        # Set description (you can enhance this based on available data)
        if place.name:
            place.description = f"Business listing for {place.name}"
            if place.address:
                place.description += f" located at {place.address}"
        
        logging.info(f"Successfully extracted place: {place.name}")
        
    except Exception as e:
        logging.error(f"Error in extract_place: {str(e)}")
    
    return place