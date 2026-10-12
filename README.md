# Colombo Stock Exchange (CSE) Daily Stock Prices & Dividend Mapper

A Python pipeline and Google Colab-compatible notebook that extracts daily stock prices and maps historical dividend payouts for any company listed on the **Colombo Stock Exchange (CSE)**.

Default stock: **Commercial Bank of Ceylon PLC** (`COMB.N0000`).

---

## Key Highlights

- **Pure HTTP Requests**: No Selenium, Playwright, Chromium, or headless browsers. Uses standard `requests` and `pandas`.
- **Google Colab Compatible**: Runs on Python 3.13 / Ubuntu 24.04 with minimal dependencies (`pandas`, `requests`, `lxml`, `beautifulsoup4`).
- **Configurable Symbol**: Easily run for any CSE ticker (e.g. `COMB.N0000`, `JKH.N0000`, `SAMP.N0000`).
- **Multi-Source Dividend Tracking**:
  - **CSE Official Announcements API** (2019 – Present)
  - **StockAnalysis.com** (~4 years of declared cash distributions)
  - **Manual / Annual Reports Dictionary** (for pre-2022 historical payments)
- **Independent Column Mapping**: Each dividend source is preserved in its own column (`dps_cse`, `dps_stockanalysis`, `dps_manual`) without averaging or modifying reported values.
- **Strict Ex-Date Mapping**: Dividend amounts are attached only on the first trading day on or after each ex-dividend date (within a 7-day calendar window to accommodate Sri Lankan Poya/public holidays and weekends).

---

## CSE API Reverse-Engineering Findings

The Colombo Stock Exchange (`cse.lk`) backend operates on Spring Boot and exposes internal REST endpoints under `https://www.cse.lk/api/`.

### 1. Request Format
- **Important**: The CSE backend expects parameters passed as `application/x-www-form-urlencoded` (`data={"param": "value"}`). Passing JSON body causes `HTTP 400 "... parameter is missing"`.
- Requests should include `Origin: https://www.cse.lk` and `Referer: https://www.cse.lk/`.

### 2. Symbol to Numeric `stockId` Resolution
- **Endpoint**: `POST https://www.cse.lk/api/companyInfoSummery`
- **Body**: `symbol=<TICKER>` (e.g. `symbol=COMB.N0000`)
- **Key**: `response["reqSymbolInfo"]["id"]` (e.g. `208` for `COMB.N0000`).

### 3. Public Stock Chart Daily Prices
- **Endpoint**: `POST https://www.cse.lk/api/companyChartDataByStock`
- **Body**: `stockId=<INTEGER>&period=<INTEGER>`
- **Period Codes**:
  - `period=1`: **1 Day** (Intraday tick-by-tick trades for today's session)
  - `period=2`: **1 Week** (Last 5 trading days)
  - `period=3`: **1 Month** (Last 20 trading days)
  - `period=4`: **3 Months** (Last ~39 trading days)
  - `period=5`: **1 Year / 52-Week Daily Data** (~241 daily trading records)
  - `period>=6`: Defaults back to 1 week (4–5 points).
- **Public Range Limit**: The free public chart API caps daily OHLC data at **1 year** (~241 trading days). The full 10-year historical trades endpoint (`/api/historicalTrades`) on `cse.lk` is gated behind an authenticated user subscription (`ROLE_PLATINUM` / `ROLE_CLASSIC`). If you possess an extended 10-year CSV, you can provide it via `--csv` or `HISTORICAL_CSV_PATH`.

### 4. Dividend Disclosures Archive
- **Company Announcements**: `POST https://www.cse.lk/api/getAnnouncementByCompany` with `symbol=<TICKER>`.
- **Announcement Details**: `POST https://www.cse.lk/api/getAnnouncementById` with `announcementId=<ID>`.
- Yields structured fields:
  - `xd`: Ex-dividend date (e.g. `02 Apr 2026`)
  - `recordDate`: Record date timestamp
  - `payment`: Payment date (e.g. `24 Apr 2026`)
  - `votingDivPerShare`: Declared cash dividend per voting share (e.g. `8.0`, `7.5`, `4.5`)

---

## Project Structure

```text
cse-daily-dividends/
├── cse_daily_dividends.py                   # Standalone CLI Python pipeline
├── cse_daily_dividends.ipynb                # Google Colab compatible notebook
├── COMB.N0000_dividends.csv                 # Consolidated 10-year dividends-only CSV
├── COMB.N0000_daily_with_dividends.csv      # Daily trading table with mapped dividends
├── COMB.N0000_cse_announcements_parsed.csv  # Parsed corporate announcements archive
├── requirements.txt                         # Minimal Python dependencies
├── .gitignore                               # Git ignore rules
├── LICENSE                                  # MIT License
├── README.md                                # Project documentation
└── scripts/                                 # Verification & testing utilities
    ├── README.md                            # Scripts directory documentation
    ├── test_pipeline.py                     # End-to-end integration test runner
    ├── parse_all_announcements.py           # Full announcement dividend parser
    ├── extract_all_10y_dividends.py         # 10-year cash & scrip dividend extractor
    ├── test_cse_endpoints.py                # CSE API endpoint & parameter probe
    ├── test_stockanalysis.py                # StockAnalysis scraper test
    ├── inspect_div_announcements.py         # JSON announcement metadata inspector
    ├── test_daily_format.py                 # OHLC timestamp & timezone test
    ├── check_div_range.py                   # Date-bound CSV alignment checker
    └── probe_cse.py                         # CSE server headers & status probe
```

---

## Output CSV Schema

### 1. Daily Table (`{SYMBOL}_daily_with_dividends.csv`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `date` | `YYYY-MM-DD` | Trading day date |
| `close` | `float` | Closing price (Rs.) |
| `volume` | `float` | Shares traded |
| `dps_cse` | `float` | Declared dividend from CSE Announcements API |
| `dps_stockanalysis` | `float` | Cash dividend from StockAnalysis |
| `dps_manual` | `float` | Historical dividend from Annual Reports dict |

### 2. Dividends Only (`{SYMBOL}_dividends.csv`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `ex_date` | `YYYY-MM-DD` | Ex-dividend date |
| `record_date` | `YYYY-MM-DD` | Shareholder record date |
| `pay_date` | `YYYY-MM-DD` | Dividend payment date |
| `amount` | `float` | Dividend amount per share |
| `source` | `string` | Source identifier (`cse_api`, `stockanalysis`, `manual`) |

---

## Quickstart

### Option A: Command Line

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/cse-daily-dividends.git
   cd cse-daily-dividends
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run for default stock (`COMB.N0000`)**:
   ```bash
   python cse_daily_dividends.py
   ```

4. **Run for any other CSE company**:
   ```bash
   python cse_daily_dividends.py --symbol JKH.N0000
   ```

5. **Run with an extended 10-year historical CSV**:
   ```bash
   python cse_daily_dividends.py --symbol COMB.N0000 --csv path/to/10y_prices.csv
   ```

### Option B: Google Colab

1. Upload `cse_daily_dividends.ipynb` to [Google Colab](https://colab.research.google.com/).
2. Run cells sequentially:
   - Cell 1 installs dependencies.
   - Cell 2 sets the `SYMBOL` variable and manual dividend dictionary.
   - Cells 3–7 query APIs, build tables, and export CSV files.
   - Cell 8 automatically downloads `{SYMBOL}_dividends.csv` and `{SYMBOL}_daily_with_dividends.csv`.

---

## Sample Output (`COMB.N0000`)

```text
===========================================================================
PIPELINE SUMMARY & DIAGNOSTICS
===========================================================================
Stock Symbol:          COMB.N0000
CSE Stock ID:          208
Daily Trading Days:    241 rows
Date Span:             2025-10-13 to 2026-10-09
Total Dividend Events: 22 records across sources
Trading Days w/ Divs:  1 days marked in price series

Trading Days with Marked Dividends:
      date  close  volume  dps_cse  dps_stockanalysis  dps_manual
2026-04-02 201.75  474222      8.0                8.0         NaN
===========================================================================
```

---

## 10-Year Historical Dividend Record (2014 – 2026)

Commercial Bank of Ceylon (`COMB.N0000`) dividend distributions extracted and consolidated in [`COMB.N0000_dividends.csv`](COMB.N0000_dividends.csv):

| Financial Year | Ex-Dividend Date (XD) | Payment Date | Cash DPS (Rs.) | Scrip Dividend Component | Primary Source |
|:---|:---:|:---:|:---:|:---|:---:|
| **2025** (Paid 2026) | **2026-04-02** | 2026-04-24 | **8.00** | + Scrip consideration Rs. 2.50 | CSE API & StockAnalysis |
| **2024** (Paid 2025) | **2025-04-01** | 2025-04-23 | **7.50** | + Scrip consideration Rs. 2.00 | CSE API & StockAnalysis |
| **2023** (Paid 2024) | **2024-04-01** | 2024-04-24 | **4.50** | + Scrip at Rs. 90.60 | CSE API & StockAnalysis |
| **2022** (Paid 2023) | **2023-03-31** | 2023-04-18 | *0.00 (Scrip only)* | **1 for 16.993 shares** (Rs. 3.825/sh eq.)* | CSE Announcements API |
| **2021** (Paid 2022) | **2022-03-31** | 2022-04-25 | **4.50** | + Scrip 1 for 26.3 shares | CSE API & StockAnalysis |
| **2020** (Paid 2021) | **2021-03-31** | 2021-04-23 | **4.50** | + Scrip at Rs. 87.70 | CSE API |
| **2019** (Final) | **2020-02-12** | 2020-02-24 | **3.00** | Second Interim / Final | CSE API |
| **2019** (1st Interim) | **2019-11-05** | 2019-11-18 | **1.50** | First Interim Cash | CSE API & Annual Report |
| **2018** (Final) | **2019-03-29** | 2019-04-18 | **2.00** | Final Cash Dividend | Annual Report |
| **2018** (1st Interim) | **2018-11-06** | 2018-11-20 | **1.50** | First Interim Cash | Annual Report |
| **2017** (Final) | **2018-03-29** | 2018-04-20 | **2.00** | Final Cash Dividend | Annual Report |
| **2017** (1st Interim) | **2017-11-07** | 2017-11-21 | **1.50** | First Interim Cash | Annual Report |
| **2016** (Final) | **2017-03-31** | 2017-04-21 | **2.00** | Final Cash Dividend | Annual Report |
| **2016** (1st Interim) | **2016-11-08** | 2016-11-22 | **1.50** | First Interim Cash | Annual Report |
| **2015** (Final) | **2016-03-31** | 2016-04-22 | **2.00** | Final Cash Dividend | Annual Report |
| **2015** (1st Interim) | **2015-11-10** | 2015-11-24 | **1.00** | First Interim Cash | Annual Report |
| **2014** (Final) | **2015-03-31** | 2015-04-24 | **1.50** | Final Cash Dividend | Annual Report |
| **2014** (1st Interim) | **2014-11-11** | 2014-11-25 | **1.00** | First Interim Cash | Annual Report |

*\*Note on 2023 (FY 2022): Due to CBSL capital conservation directives on banks following the 2022 economic crisis, Commercial Bank paid a 100% Scrip Dividend (1 share for every 16.993 ordinary shares, valued at Rs. 65/share), which is why cash-only platforms report zero cash dividend for that year.*

---

## Verification & Utility Scripts

Additional diagnostic, testing, and reverse-engineering utilities are available in the [`scripts/`](scripts/) folder:

- [`scripts/test_pipeline.py`](scripts/test_pipeline.py): End-to-end integration test runner.
- [`scripts/parse_all_announcements.py`](scripts/parse_all_announcements.py): Full company announcement dividend scraper.
- [`scripts/extract_all_10y_dividends.py`](scripts/extract_all_10y_dividends.py): Complete 10-year cash & scrip dividend extractor.
- [`scripts/test_cse_endpoints.py`](scripts/test_cse_endpoints.py): Probe CSE API endpoints, parameters, and periods.
- [`scripts/test_stockanalysis.py`](scripts/test_stockanalysis.py): Test StockAnalysis scraping logic.
- [`scripts/inspect_div_announcements.py`](scripts/inspect_div_announcements.py): Inspect raw JSON metadata for dividend announcements.
- [`scripts/test_daily_format.py`](scripts/test_daily_format.py): Test OHLC candle timestamp parsing and Colombo timezone localization.
- [`scripts/check_div_range.py`](scripts/check_div_range.py): Validate generated CSV date bounds and in-range dividends.
- [`scripts/probe_cse.py`](scripts/probe_cse.py): Test CSE server headers and connectivity.

---

## License

This project is licensed under the [MIT License](LICENSE).
