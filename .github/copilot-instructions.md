# Copilot Instructions: Pokemon Card Price Scraper

## Project Overview
Web scraper for Pokemon card prices from pricecharting.com with rate limiting, retry logic, and batch processing support.

## Architecture

### Core Design
- **Single-class architecture**: `Scraper` class in `scraperconfig.py` handles everything (config loading, session management, scraping, batch processing)
- **YAML-driven configuration**: `config.yaml` centralizes all scraping behavior (user agents, timeouts, retries, rate limits)
- **CLI entry point**: `main.py` is a thin wrapper that parses args and delegates to `Scraper.process_cards_input()`

### URL Building Pattern
```python
# Card names: lowercase, spaces→hyphens, then URL encode for special chars (apostrophes, etc.)
# CRITICAL: Use quote(card_name_formatted, safe='-') to preserve hyphens
url = f"https://www.pricecharting.com/game/{set_name}/{encoded_card_name}-{card_number}"
```

### Data Flow
1. CSV files in `cards/` folder (filename = set name, e.g., `pokemon-stellar-crown.csv`)
2. Each CSV: `card_name,card_number` columns only (no variant types like "Reverse Holo")
3. Scraper builds URLs, fetches pages, parses price tables
4. Output: Single consolidated `card_prices.csv` with all sets

## Critical Implementation Details

### Error Handling Philosophy
- Return error dictionaries (`{'error': 'type', 'error_detail': 'msg'}`) rather than raising exceptions
- Automatic retry with exponential backoff for timeouts/5xx errors (configurable via `max_retries`, `retry_delay`)
- Results include failed cards with `status='failed'` + error details for debugging

### HTML Parsing Strategy
- Primary target: `<table id="price_data">` with `<thead>` headers and `<tbody>` price rows
- Fallback: `<table class="info_box">` (alternative structure)
- Extract prices from `<span class="price">` elements
- Skip dashes/empty values; validate prices start with `$` or are numeric
- **Debug mode**: Set `save_failed_html: true` in config to save unparseable pages

### Rate Limiting Pattern
```python
# Between each request: random delay from config (default 1-3s)
delay = random.uniform(self.delay_min, self.delay_max) if self.use_random else self.delay_min
time.sleep(delay)
```

### Session Management
- Requests session with `HTTPAdapter` + `Retry` strategy (retries 429, 5xx)
- Rotating user agents (random selection per request)
- Headers include Accept-Encoding for gzip/compression support

## Development Workflows

### Running the Scraper
```bash
# Process all CSV files in cards/ folder
python main.py

# Process single file
python main.py cards/pokemon-stellar-crown.csv

# Custom output location
python main.py -o results.csv

# Custom config
python main.py -c myconfig.yaml
```

### Testing Patterns
- `test_scraper.py`: Validate HTML parsing logic against local example files (`example/examplepage*.html`)
- `test_url_encoding.py`: Verify URL encoding for special characters (apostrophes, ampersands)
- No formal test framework—quick validation scripts only

### Debugging Failed Scrapes
1. Enable `save_failed_html: true` in `config.yaml`
2. Run scraper—failed pages saved as `debug_failed_*.html`
3. Inspect HTML structure vs. expected selectors in `scrape_price()`

## Configuration Patterns

### Typical Adjustments
- **Rate limit too aggressive?** Increase `delay_max` or set `use_random: false` + fixed `delay_min`
- **Hitting timeouts?** Increase `timeout` (default 15s) or `max_retries` (default 3)
- **Getting blocked?** Add more `user_agents` or increase delays

### Adding New Price Columns
If pricecharting.com adds new grades/conditions:
1. No code changes needed—parser extracts all `<th>` headers dynamically
2. Column names auto-generated: lowercase, spaces→underscores, strip `#` and `.`

## Project Conventions

### CSV Input Format
- **KEEP variant suffixes** like `-reverse-holo`, `-holo` as part of the card name when present
- Card names should match the format used in pricecharting.com URLs
- Example: `ponyta-reverse-holo,19` stays as `ponyta-reverse-holo` + URL encoding handles special characters

### Error Types
- `not_found`: Card doesn't exist (404 page)
- `parsing_failed`: HTML structure different than expected
- `no_prices_available`: Table found but all prices are dashes/empty
- `request_timeout`: Request timed out after retries
- `http_error`: Non-retryable HTTP error
- `connection_error`: Network failure after retries

### Dependencies
Python 3.14+ required. Core deps:
- `requests` + `urllib3`: HTTP with retry logic
- `beautifulsoup4` + `lxml`: HTML parsing
- `pandas`: CSV I/O
- `pyyaml`: Config loading

**CRITICAL**: Do NOT request brotli encoding (`br`) in `Accept-Encoding` header unless `brotli` package is installed. Use only `gzip, deflate` to avoid receiving compressed binary responses that can't be decoded.
