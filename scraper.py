import csv
import time
import sys
import yaml
import random
from pathlib import Path
from typing import Dict, List
from urllib.parse import quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd


class Scraper:
    """Unified scraper class with configuration and scraping functionality."""
    
    def __init__(self, config_file: str = 'config.yaml'):
        """Initialize scraper with configuration from YAML file."""
        # Load configuration
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {config_file} not found, using defaults")
            config = {}
        
        scraping = config.get('scraping', {})
        output = config.get('output', {})
        
        # Scraping settings
        self.user_agents = scraping.get('user_agents', [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        ])
        self.timeout = scraping.get('timeout', 15)
        self.max_retries = scraping.get('max_retries', 3)
        self.retry_delay = scraping.get('retry_delay', 2.0)
        
        rate_limit = scraping.get('rate_limit', {})
        self.delay_min = rate_limit.get('delay_min', 1.0)
        self.delay_max = rate_limit.get('delay_max', 3.0)
        self.use_random = rate_limit.get('use_random', True)
        
        self.headers_config = scraping.get('headers', {})
        
        # Output settings
        self.default_folder = output.get('default_folder', 'cards')
        self.default_output_file = output.get('default_output_file', 'card_prices.csv')
        
        # Debug settings
        self.debug_mode = scraping.get('debug_mode', False)
        self.save_failed_html = scraping.get('save_failed_html', False)
        
        # Create session with retry logic
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get_delay(self) -> float:
        """Get delay duration (random or fixed)."""
        if self.use_random:
            return random.uniform(self.delay_min, self.delay_max)
        return self.delay_min
    
    def get_user_agent(self) -> str:
        """Get a random user agent from the list."""
        return random.choice(self.user_agents)
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with a random user agent."""
        headers = self.headers_config.copy()
        headers['User-Agent'] = self.get_user_agent()
        return headers
    
    def build_url(self, set_name: str, card_name: str, card_number: str) -> str:
        """Build the pricecharting.com URL for a Pokemon card."""
        # Convert card name to URL format (lowercase, spaces to hyphens)
        card_name_formatted = card_name.lower().replace(' ', '-')
        # URL encode the card name to handle special characters like apostrophes
        card_name_encoded = quote(card_name_formatted, safe='-')
        return f"https://www.pricecharting.com/game/{set_name}/{card_name_encoded}-{card_number}"
    
    def scrape_price(self, url: str, attempt: int = 1) -> Dict[str, str]:
        """
        Scrape price information from a pricecharting.com URL.
        Returns a dictionary with price data and error information.
        """
        headers = self.get_headers()
        
        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Requests should handle gzip automatically, but let's ensure proper encoding
            if response.encoding is None or response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            # Get the content - response.text should automatically decompress gzip
            html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            prices = {}
            
            # Find the main price table
            price_table = soup.find('table', {'id': 'price_data'})
            
            if not price_table:
                # Check if the page exists at all (might be 404 but with 200 status)
                page_title = soup.find('title')
                if page_title and '404' in page_title.get_text():
                    return {
                        'error': 'not_found',
                        'error_detail': 'Card not found on pricecharting.com (404 page)'
                    }
                
                # Try alternative selectors in case the structure changed
                price_table = soup.find('table', class_='info_box')
                if not price_table:
                    # Save HTML for debugging if enabled
                    if self.save_failed_html:
                        debug_file = f"debug_failed_{url.split('/')[-1]}.html"
                        try:
                            with open(debug_file, 'w', encoding='utf-8', errors='replace') as f:
                                # Ensure we're writing decoded text
                                content = response.text if isinstance(response.text, str) else response.content.decode('utf-8', errors='replace')
                                f.write(content)
                            print(f"  📝 Saved failed HTML to {debug_file}")
                        except Exception as e:
                            print(f"  ⚠ Could not save debug HTML: {e}")
                    
                    return {
                        'error': 'parsing_failed',
                        'error_detail': 'Price table not found on page (tried id=price_data and class=info_box)'
                    }
            
            # Get headers (condition names: Ungraded, Grade 7, Grade 8, etc.)
            headers_row = price_table.find('thead')
            if not headers_row:
                return {
                    'error': 'parsing_failed',
                    'error_detail': 'Table header not found in price table'
                }
            
            headers_tr = headers_row.find('tr')
            if not headers_tr:
                return {
                    'error': 'parsing_failed',
                    'error_detail': 'Header row not found in price table'
                }
            
            headers = [th.get_text(strip=True) for th in headers_tr.find_all('th')]
            
            # Get price values from tbody
            tbody = price_table.find('tbody')
            if not tbody:
                return {
                    'error': 'parsing_failed',
                    'error_detail': 'Table body not found in price table'
                }
            
            price_row = tbody.find('tr')
            if not price_row:
                return {
                    'error': 'parsing_failed',
                    'error_detail': 'Price row not found in table body'
                }
            
            price_cells = price_row.find_all('td')
            
            if not price_cells:
                return {
                    'error': 'parsing_failed',
                    'error_detail': 'No price cells found in price row'
                }
            
            # Match headers with price cells
            found_any_price = False
            for i, header in enumerate(headers):
                if i < len(price_cells):
                    # Extract the price value
                    price_span = price_cells[i].find('span', class_='price')
                    if price_span:
                        price_value = price_span.get_text(strip=True)
                        
                        # Skip if the price is just a dash (no data) or empty
                        if price_value and price_value != '-':
                            # Validate it looks like a price (starts with $ or is a number)
                            if price_value.startswith('$') or price_value.replace('.', '').replace(',', '').isdigit():
                                # Clean up header name for column
                                column_name = header.lower().replace(' ', '_').replace('#', '').replace('.', '')
                                prices[column_name] = price_value
                                found_any_price = True
            
            if not found_any_price:
                return {
                    'error': 'no_prices_available',
                    'error_detail': 'Found price table but no valid prices (all dashes or empty)'
                }
            
            return prices
            
        except requests.Timeout:
            if attempt < self.max_retries:
                retry_delay = self.retry_delay * attempt
                print(f"  ⚠ Request timeout (attempt {attempt}/{self.max_retries}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                return self.scrape_price(url, attempt + 1)
            else:
                return {
                    'error': 'request_timeout',
                    'error_detail': f'Request timed out after {self.max_retries} attempts'
                }
        
        except requests.HTTPError as e:
            if attempt < self.max_retries and e.response.status_code in [429, 500, 502, 503, 504]:
                retry_delay = self.retry_delay * attempt
                print(f"  ⚠ HTTP {e.response.status_code} (attempt {attempt}/{self.max_retries}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                return self.scrape_price(url, attempt + 1)
            else:
                return {
                    'error': 'http_error',
                    'error_detail': f'HTTP {e.response.status_code}: {str(e)}'
                }
        
        except requests.ConnectionError as e:
            if attempt < self.max_retries:
                retry_delay = self.retry_delay * attempt
                print(f"  ⚠ Connection error (attempt {attempt}/{self.max_retries}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                return self.scrape_price(url, attempt + 1)
            else:
                return {
                    'error': 'connection_error',
                    'error_detail': f'Failed to connect: {str(e)}'
                }
        
        except requests.RequestException as e:
            if attempt < self.max_retries:
                retry_delay = self.retry_delay * attempt
                print(f"  ⚠ Request failed (attempt {attempt}/{self.max_retries}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                return self.scrape_price(url, attempt + 1)
            else:
                return {
                    'error': 'request_failed',
                    'error_detail': f'Request error: {str(e)}'
                }
        
        except Exception as e:
            return {
                'error': 'unknown_error',
                'error_detail': f'Unexpected error: {str(e)}'
            }
    
    def process_single_set(self, csv_file: Path, set_name: str) -> List[Dict]:
        """
        Process a single CSV file for one Pokemon card set.
        
        Args:
            csv_file: Path to the CSV file
            set_name: Name of the set (derived from filename)
            session: Requests session with retry logic
            config: Scraper configuration
            
        Returns:
            List of result dictionaries
        """
        results = []
        
        print(f"\n{'='*60}")
        print(f"Processing set: {set_name}")
        print(f"File: {csv_file}")
        print(f"{'='*60}\n")
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                cards = list(reader)
        except Exception as e:
            print(f"Error reading file {csv_file}: {e}", file=sys.stderr)
            return results
        
        # Filter out invalid rows
        cards = [c for c in cards if c.get('card_name', '').strip() and c.get('card_number', '').strip()]
        
        total_cards = len(cards)
        print(f"Found {total_cards} cards to process\n")
        
        for idx, card in enumerate(cards, 1):
            card_name = card.get('card_name', '').strip()
            card_number = card.get('card_number', '').strip()
            
            if not card_name or not card_number:
                continue
            
            url = self.build_url(set_name, card_name, card_number)
            print(f"[{idx}/{total_cards}] Scraping: {card_name} #{card_number}")
            print(f"  URL: {url}")
            
            prices = self.scrape_price(url)
            
            result = {
                'set': set_name,
                'card_name': card_name,
                'card_number': card_number,
                'url': url,
            }
            
            # Check if we got an error or actual prices
            if 'error' in prices:
                result['status'] = 'failed'
                result['error_type'] = prices['error']
                result['error_message'] = prices['error_detail']
                print(f"  ✗ {prices['error']}: {prices['error_detail']}")
            else:
                result.update(prices)
                print(f"  ✓ Found {len(prices)} price(s): {', '.join(prices.keys())}")
            
            results.append(result)
            
            # Be respectful - add delay between requests with randomization
            if idx < total_cards:
                delay = self.get_delay()
                print(f"  ⏱ Waiting {delay:.2f}s before next request...")
                time.sleep(delay)
            
            print()
        
        return results
    
    
    def process_cards_input(self, input_path: str = 'cards', output_file: str = 'card_prices.csv'):
        """
        Process CSV file(s) and scrape prices.
        Can accept either a folder path (processes all CSV files) or a single CSV file path.
        
        Args:
            input_path: Path to folder containing CSV files or path to a single CSV file
            output_file: Path to output CSV file
        """
        path = Path(input_path)
        
        if not path.exists():
            print(f"Error: Path {input_path} not found", file=sys.stderr)
            return
        
        # Determine if input is a file or folder
        if path.is_file():
            # Single file processing
            if not path.suffix == '.csv':
                print(f"Error: File must be a CSV file, got {path.suffix}", file=sys.stderr)
                return
            
            csv_files = [path]
            print(f"Processing single file: {path.stem}")
        else:
            # Folder processing - find all CSV files
            csv_files = list(path.glob('*.csv'))
            
            if not csv_files:
                print(f"Error: No CSV files found in {input_path}", file=sys.stderr)
                return
            
            print(f"Found {len(csv_files)} set(s) to process:")
            for csv_file in csv_files:
                print(f"  - {csv_file.stem}")
        
        all_results = []
        
        for csv_file in csv_files:
            # Use filename (without extension) as set name
            set_name = csv_file.stem
            
            results = self.process_single_set(csv_file, set_name)
            all_results.extend(results)
        
        # Save all results to CSV
        if all_results:
            df = pd.DataFrame(all_results)
            df.to_csv(output_file, index=False)
            print(f"\n{'='*60}")
            print(f"Results saved to {output_file}")
            successful = len([r for r in all_results if 'status' not in r or r['status'] != 'failed'])
            print(f"Successfully processed {successful}/{len(all_results)} cards total")
            print(f"{'='*60}")
        else:
            print("No results to save")