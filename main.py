from scrapper.core import scrape_places
from scrapper.utils import save_places_to_csv, setup_logging
import argparse
import logging

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str, help="Search query for Google Maps")
    parser.add_argument("-t", "--total", type=int, help="Total number of results to scrape")
    parser.add_argument("-o", "--output", type=str, default="result.csv", help="Output CSV file path")
    parser.add_argument("--append", action="store_true", help="Append results to the output file instead of overwriting")
    args = parser.parse_args()

    search_for = args.search or "Gyms in Lahore"
    total = args.total or 1
    output_path = args.output
    append = args.append

    setup_logging()
    logging.info(f"Starting scrape for: '{search_for}' (total: {total})")

    places = scrape_places(search_for, total)
    save_places_to_csv(places, output_path, append=append)

if __name__ == "__main__":
    main()
