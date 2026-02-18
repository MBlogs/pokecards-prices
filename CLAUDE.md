# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pokemon card price scraper that fetches prices from pricecharting.com. Processes CSV files of card lists, scrapes prices with rate limiting and retry logic, and outputs a consolidated price CSV.

## Commands

```bash
# Install dependencies (uses uv, Python 3.14+)
uv sync

# Run scraper on all sets
python main.py

# Run on a single set
python main.py cards/pokemon-stellar-crown.csv

# Custom output / config
python main.py -o results.csv -c custom_config.yaml
```

No test framework — validation scripts only (`test_scraper.py`, `test_url_encoding.py`).

## Architecture

**Single-class design**: `Scraper` in `scraper.py` handles config loading, HTTP sessions, scraping, and batch processing. `main.py` is a thin CLI wrapper using argparse.

**Data flow**: CSV files in `cards/` (filename = set name) → `Scraper.process_cards_input()` → builds pricecharting.com URLs → fetches/parses HTML → merges with existing data → writes to `output/card_prices.csv`.

**URL pattern**: `https://www.pricecharting.com/game/{set_name}/{encoded_card_name}-{card_number}` — card names are lowercased, spaces become hyphens, then URL-encoded with `quote(name, safe='-')`.

**Incremental scraping**: Existing output is loaded and cards with recent successful scrapes (configurable `max_age_days`) are skipped. Failed cards are always re-scraped.

## Key Implementation Details

- **Error handling**: `scrape_price()` returns error dicts (`{'error': 'type', 'error_detail': 'msg'}`) rather than raising exceptions. Failed cards get `status='failed'` in output.
- **HTML parsing**: Targets `<table id="price_data">`, falls back to `<table class="info_box">`. Extracts prices from `<span class="price">` elements. Column names are auto-generated from table headers.
- **Rate limiting**: Random delays between requests (configurable in `config.yaml`). Uses rotating user agents and `requests.Session` with `HTTPAdapter`/`Retry` for exponential backoff on 429/5xx.
- **Do NOT use brotli encoding** in `Accept-Encoding` — only `gzip, deflate`. The `brotli` package is not installed.
- **Debug mode**: Set `save_failed_html: true` in `config.yaml` to save unparseable HTML pages to `debug/`.

## CSV Input Format

Each file in `cards/` has columns: `card_name`, `card_number`, and optionally `quantity`. Variant suffixes like `-reverse-holo` are part of the card name. Names must match pricecharting.com URL format.

## Configuration

All scraping behavior is controlled via `config.yaml`: user agents, timeouts, retries, rate limits, incremental settings, sort order, and output paths.
