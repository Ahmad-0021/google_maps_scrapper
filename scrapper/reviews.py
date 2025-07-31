from playwright.sync_api import Page
import logging
import time

def extract_reviews(page: Page):
    """Extract reviews from Google Maps place page"""
    reviews_data = []
    
    try:
        # First, try to click on reviews tab/section
        try:
            # Look for reviews button/tab and click it
            reviews_button = page.locator('button[data-tab-index="1"]')  # Reviews tab
            if reviews_button.count() > 0:
                reviews_button.click()
                page.wait_for_timeout(2000)
        except:
            pass
        
        # Alternative: scroll down to reviews section
        try:
            reviews_section = page.locator('div[data-review-id]').first
            if reviews_section.count() > 0:
                reviews_section.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
        except:
            pass
        
        # Scroll to load more reviews
        logging.info("Scrolling to load reviews...")
        for i in range(5):  # Reduced scroll attempts
            try:
                # Scroll within the reviews container
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(1500)
                
                # Check if we have reviews
                review_count = page.locator('div[data-review-id]').count()
                logging.info(f"Found {review_count} reviews after scroll {i+1}")
                
                if review_count > 0:
                    break
            except Exception as e:
                logging.warning(f"Scroll attempt {i+1} failed: {e}")
                continue
        
        # Try multiple selectors for reviews
        review_selectors = [
            'div[data-review-id]',  # Most common
            'div[jsaction*="review"]',
            'div.gws-localreviews__google-review',
            'div[class*="review"]',
            '.wiI7pd'  # Common Google Maps review class
        ]
        
        reviews = []
        for selector in review_selectors:
            try:
                reviews = page.locator(selector).all()
                if reviews:
                    logging.info(f"Found {len(reviews)} reviews using selector: {selector}")
                    break
            except:
                continue
        
        if not reviews:
            logging.warning("No review elements found with any selector")
            return reviews_data
        
        # Extract data from each review
        for idx, review in enumerate(reviews[:20]):  # Limit to first 20 reviews
            try:
                review_data = {}
                
                # Extract author name - try multiple selectors
                author_selectors = [
                    '.d4r55',
                    'div[class*="TSUbDb"] span',
                    'span.X43Kjb',
                    'div.TSUbDb a',
                    '[data-href*="contrib"]'
                ]
                
                for author_sel in author_selectors:
                    try:
                        author_elem = review.locator(author_sel).first
                        if author_elem.count() > 0:
                            review_data['author'] = author_elem.inner_text().strip()
                            break
                    except:
                        continue
                
                # Extract rating
                rating_selectors = [
                    'span[class*="kvMYJc"]',
                    'div[class*="DU9Pgb"] span',
                    'span.fzvQIb',
                    'g-review-stars span'
                ]
                
                for rating_sel in rating_selectors:
                    try:
                        rating_elem = review.locator(rating_sel).first
                        if rating_elem.count() > 0:
                            aria_label = rating_elem.get_attribute('aria-label') or rating_elem.inner_text()
                            if aria_label and ('star' in aria_label.lower() or 'rating' in aria_label.lower()):
                                review_data['rating'] = aria_label
                                break
                    except:
                        continue
                
                # Extract date
                date_selectors = [
                    'span.rsqaWe',
                    'span[class*="dehysf"]',
                    'span.p2TkOb',
                    'div.DU9Pgb span'
                ]
                
                for date_sel in date_selectors:
                    try:
                        date_elem = review.locator(date_sel).first
                        if date_elem.count() > 0:
                            date_text = date_elem.inner_text().strip()
                            if date_text and ('ago' in date_text.lower() or any(month in date_text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])):
                                review_data['date'] = date_text
                                break
                    except:
                        continue
                
                # Extract review content
                content_selectors = [
                    'span[jsname="bN97Pc"]',
                    'div[class*="MyEned"] span',
                    'span.wiI7pd',
                    'div.k8MTF span',
                    'span[data-expandable-section]'
                ]
                
                for content_sel in content_selectors:
                    try:
                        content_elem = review.locator(content_sel).first
                        if content_elem.count() > 0:
                            content_text = content_elem.inner_text().strip()
                            if content_text and len(content_text) > 10:  # Ensure it's actual content
                                review_data['content'] = content_text
                                break
                    except:
                        continue
                
                # Only add review if we got at least author or content
                if review_data.get('author') or review_data.get('content'):
                    # Set defaults for missing fields
                    review_data.setdefault('author', 'Anonymous')
                    review_data.setdefault('date', 'Unknown')
                    review_data.setdefault('content', 'No content')
                    review_data.setdefault('rating', 'No rating')
                    
                    reviews_data.append(review_data)
                    logging.info(f"Extracted review {idx+1}: {review_data['author'][:20]}...")
                
            except Exception as e:
                logging.warning(f"Failed to extract review {idx+1}: {str(e)}")
                continue
        
        logging.info(f"Successfully extracted {len(reviews_data)} reviews")
        
    except Exception as e:
        logging.error(f"Error in extract_reviews: {str(e)}")
    
    return reviews_data