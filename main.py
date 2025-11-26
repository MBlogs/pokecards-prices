import argparse
from scraperconfig import Scraper


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Scrape Pokemon card prices from pricecharting.com'
    )
    parser.add_argument(
        'input_path',
        nargs='?',
        default='cards',
        help='Folder containing CSV files or path to a single CSV file (default: cards/)'
    )
    parser.add_argument(
        '-o', '--output',
        default='card_prices.csv',
        help='Output CSV file (default: card_prices.csv)'
    )
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Configuration file (default: config.yaml)'
    )
    
    args = parser.parse_args()
    
    # Initialize scraper with config file
    scraper = Scraper(args.config)
    
    # Process the input
    scraper.process_cards_input(args.input_path, args.output)
