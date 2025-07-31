import logging
import os
import pandas as pd
from dataclasses import asdict
from typing import List
from .models import Place
import csv

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

def save_places_to_csv(places: List[Place], output_path: str = "result.csv", append: bool = False):
    if not places:
        logging.warning("No places to save.")
        return
        
    df = pd.DataFrame([asdict(place) for place in places])
    file_exists = os.path.isfile(output_path)
    mode = "a" if append else "w"
    header = not (append and file_exists)
    
    df.to_csv(output_path, index=False, mode=mode, header=header)
    
    # Count images if image_url field exists
    with_images = 0
    if 'image_url' in df.columns:
        with_images = df['image_url'].notna().sum()
    
    logging.info(f"Saved {len(df)} places | Images: {with_images}/{len(df)} ({with_images/len(df)*100:.1f}%)")

def save_reviews_to_csv(place_name: str, reviews: List[dict]):
    """Save reviews to CSV file"""
    if not reviews:
        logging.warning(f"No reviews to save for {place_name}")
        return
    
    # Create directory if it doesn't exist
    os.makedirs("scraped_data", exist_ok=True)
    
    # Clean place name for filename
    safe_name = "".join(c for c in place_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"scraped_data/{safe_name}_reviews.csv"
    
    try:
        with open(filename, mode="w", newline='', encoding="utf-8") as f:
            if reviews:
                fieldnames = reviews[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(reviews)
        
        logging.info(f"Saved {len(reviews)} reviews to {filename}")
        
    except Exception as e:
        logging.error(f"Error saving reviews for {place_name}: {str(e)}")