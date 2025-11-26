# Pokemon Card Price Scraper

Scrape Pokemon card prices from pricecharting.com for multiple sets with intelligent retry logic and rate limiting.

## Features

- **Multi-set support**: Process multiple card sets from CSV files
- **Configurable scraping**: Customize user agents, timeouts, retries via config file
- **Retry logic**: Automatic retries with exponential backoff on failures
- **Rate limiting**: Random delays between requests to avoid detection
- **Rotating user agents**: Multiple user agents to appear more natural
- **URL encoding**: Proper handling of special characters (apostrophes, etc.)

## Setup

Install dependencies:
```bash
pip install requests beautifulsoup4 pandas lxml urllib3 pyyaml
```

## Configuration

Create a `config.yaml` file to customize scraping behavior (or use the default one provided):

```yaml
scraping:
  user_agents:
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36..."
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
  
  timeout: 15
  max_retries: 3
  retry_delay: 2.0
  
  rate_limit:
    delay_min: 1.0
    delay_max: 3.0
    use_random: true
```

### Configuration Options

- **user_agents**: List of user agent strings (randomly rotated)
- **timeout**: Request timeout in seconds
- **max_retries**: Number of retry attempts on failure
- **retry_delay**: Base delay for exponential backoff
- **rate_limit**:
  - `delay_min`: Minimum delay between requests
  - `delay_max`: Maximum delay between requests
  - `use_random`: Use random delays (true) or fixed (false)

## Usage

### Folder Structure

Place CSV files in the `cards/` folder, with one CSV per set. The filename (without .csv extension) will be used as the set name for the URL.

Example:
```
cards/
  pokemon-stellar-crown.csv
  pokemon-white-flare.csv
  pokemon-destined-rivals.csv
```

### CSV Format

Each CSV should contain:
- `card_name`: The card name (e.g., "lacey", "team-rocket's-raticate")
- `card_number`: The card number (e.g., "172", "40")

Example `pokemon-stellar-crown.csv`:
```csv
card_name,card_number
lacey,172
erika's-invitation,191
tatsugiri,131
```

**Important Notes**:
- Special characters like apostrophes are automatically URL-encoded
- **Include variant suffixes** like `-reverse-holo` or `-holo` as part of the card_name when they are part of the card's official name
- The card name in the CSV should match how it appears on pricecharting.com URLs
- Example: Use `tatsugiri-reverse-holo` for reverse holo variant, `tatsugiri` for base card

### Run the Scraper

```bash
# Process all CSV files in the cards/ folder with default config
python main.py

# Process a single CSV file
python main.py cards/pokemon-white-flare.csv

# Specify a different folder
python main.py my_cards_folder/

# Specify output file
python main.py -o results.csv

# Process single file with custom output
python main.py cards/pokemon-stellar-crown.csv -o stellar_prices.csv

# Use a different config file
python main.py --config custom_config.yaml

# Combine options
python main.py my_cards/ -o prices.csv -c config.yaml
```

## Output

The script generates a single CSV file (`card_prices.csv` by default) containing:
- `set`: The set name (from the CSV filename)
- `card_name`: The card name
- `card_number`: The card number
- `url`: The pricecharting.com URL
- Price columns: `ungraded`, `grade_7`, `grade_8`, `grade_9`, `grade_95`, `psa_10`, etc.
- `status`: "failed" for unsuccessful scrapes

## Features in Detail

### Retry Logic
- Failed requests are automatically retried up to `max_retries` times
- Uses exponential backoff (delay increases with each retry)
- Handles common HTTP errors (429, 500, 502, 503, 504)

### Rate Limiting
- Random delays between requests (configurable range)
- Prevents server overload and detection
- Displays countdown timer for transparency

### User Agent Rotation
- Randomly selects from configured user agents
- Makes requests appear more natural
- Includes realistic browser headers

## Notes

- Be respectful to the server - recommended delays are 1-3 seconds
- Invalid rows (missing card name or number) are automatically skipped
- The script shows detailed progress with emoji indicators:
  - ✓ Success
  - ✗ Failure
  - ⚠ Retry
  - ⏱ Waiting
