# Pokemon Card Price Scraper
Scrape Pokemon card prices for multiple sets with intelligent retry logic and rate limiting.

## ⚠️ Disclaimer

**This project is for educational and personal use only.**

- The scraper implements respectful rate limiting (2-5 second delays) that simulates normal browser usage
- Incremental scraping only re-fetches cards with failed scrapes or data older than 7 days (configurable)
- This tool is designed for small-scale, personal price tracking of individual card collections
- **For commercial use or large-scale operations**, please use PriceCharting's official API: https://www.pricecharting.com/api-documentation#prices-api
- I am not responsible for any misuse of this tool or violations of PriceCharting's terms of service
- Always respect website resources and server capacity
- Consider uploading your collection directly to PriceCharting.com for built-in price tracking features


## Features

- **Multi-set support**: Process multiple card sets from CSV files
- **Configurable scraping**: Customize user agents, timeouts, retries via config file
- **Retry logic**: Automatic retries with exponential backoff on failures
- **Rate limiting**: Random delays between requests to avoid detection
- **Rotating user agents**: Multiple user agents to appear more natural
- **URL encoding**: Proper handling of special characters (apostrophes, etc.)

## Setup

### Prerequisites

- Python 3.14+ (developed with Python 3.14)
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer and resolver

### Installation

```bash
# Clone the repository
git clone "https://github.com/MBlogs/pokecards-prices.git"
cd pokecards-prices  

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Unix/macOS
# or `.venv\Scripts\activate` on Windows

# Install dependencies ready to run
uv sync
```


### Run the Scraper

```bash
# Activate virtual environment first
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

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

**Note**: This project requires standard HTML/HTTP libraries. Do not install the `brotli` package unless you modify the config to request brotli encoding, as the default configuration uses only `gzip` and `deflate` compression.

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

## Output

The script generates a single CSV file (default: `output/card_prices.csv`) containing:
- `set`: The set name (from the CSV filename)
- `card_name`: The card name
- `card_number`: The card number
- `batch_start_time`: ISO timestamp when the scraping batch started
- `scraped_at`: ISO timestamp when this specific card was scraped
- Price columns: `ungraded`, `grade_7`, `grade_8`, `grade_9`, `grade_95`, `psa_10`, etc.
- `status`: "failed" for unsuccessful scrapes
- `error_type`, `error_message`: Details for failed scrapes
- `url`: The pricecharting.com URL

### Incremental Scraping

The scraper intelligently merges results with existing data:
- **Skips cards** with successful scrapes less than 7 days old (configurable in `config.yaml`)
- **Re-scrapes cards** that previously failed or have no price data
- **Preserves historical data** while updating only what's necessary
- Output file grows incrementally and maintains all card history

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

- **Be respectful to the server** - recommended delays are 1-3 seconds between requests
- Invalid rows (missing card name or number) are automatically skipped
- Failed HTML pages are saved to `debug/` folder when `save_failed_html: true` in config
- The script shows detailed progress with emoji indicators:
  - ✓ Success (price found)
  - ✗ Failure (scraping error)
  - 🔍 Scraping (actively fetching)
  - ⏭ Skipping (using cached data)
  - ⏱ Waiting (rate limiting delay)

## Troubleshooting

- **Binary/garbled HTML output**: Ensure `Accept-Encoding` in config is set to `gzip, deflate` (not `br`)
- **Old data not refreshing**: Adjust `max_age_days` in config or set `incremental.enabled: false`
- **Cards not found**: Verify card names match PriceCharting.com URL format (lowercase, hyphens, with variant suffixes)
- **Rate limiting errors**: Increase delay values in `config.yaml`
