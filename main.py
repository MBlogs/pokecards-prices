import argparse
from scraper import Scraper


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
        default=None,
        help='Output CSV file (default: from config.yaml)'
    )
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Configuration file (default: config.yaml)'
    )
    
    args = parser.parse_args()
    
    # Initialize scraper with config file
    scraper = Scraper(args.config)
    
    # Use output from args, or fall back to config default
    output_file = args.output if args.output else scraper.default_output_file
    
    # Process the input
    scraper.process_cards_input(args.input_path, output_file)
