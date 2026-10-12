# CSE Dividend & Price Verification Scripts

This directory contains standalone testing, verification, and inspection utilities developed during the discovery and reverse-engineering of the Colombo Stock Exchange (CSE) API and dividend data pipelines.

## Scripts Index

| Script | Purpose | Key Endpoints / Sources |
|---|---|---|
| [`test_pipeline.py`](test_pipeline.py) | **End-to-end integration test** validating full symbol resolution, dividend extraction across all 3 sources, daily prices fetch, and merging logic. | CSE API, StockAnalysis, Manual Dict |
| [`parse_all_announcements.py`](parse_all_announcements.py) | Scrapes and unpacks the entire corporate dividend disclosures archive for a stock. | `/api/getAnnouncementByCompany`, `/api/getAnnouncementById` |
| [`test_cse_endpoints.py`](test_cse_endpoints.py) | Systematic endpoint probe testing periods (`1`, `2`, `3`, `5`, etc.) and payload formats. | `/api/companyChartDataByStock`, `/api/charts`, `/api/charts/52week` |
| [`test_stockanalysis.py`](test_stockanalysis.py) | Tests plain-HTTP extraction of historical declared dividend payout tables. | `stockanalysis.com/quote/cose/<SYMBOL>/dividend/` |
| [`inspect_div_announcements.py`](inspect_div_announcements.py) | Deep inspection of raw JSON announcement structures, attachments, and field types. | `/api/getAnnouncementById` |
| [`test_daily_format.py`](test_daily_format.py) | Tests millisecond timestamp conversion to Sri Lanka local time (UTC+05:30) and OHLC formatting. | `/api/companyChartDataByStock` |
| [`check_div_range.py`](check_div_range.py) | Analyzes generated CSV files to inspect which dividends fall inside vs outside the trading price date range. | Local CSV files |
| [`probe_cse.py`](probe_cse.py) | Tests HTTP headers, CORS/Referer requirements, and form parameter parsing behavior. | `/api/companyInfoSummery` |

## Usage Examples

Run any script with Python:

```bash
# Run end-to-end test pipeline
python scripts/test_pipeline.py

# Parse all dividend disclosures for Commercial Bank or any other symbol
python scripts/parse_all_announcements.py COMB.N0000

# Probe CSE chart endpoints
python scripts/test_cse_endpoints.py COMB.N0000

# Test StockAnalysis scraper
python scripts/test_stockanalysis.py COMB.N0000

# Check date ranges of generated CSV outputs
python scripts/check_div_range.py COMB.N0000
```
