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
├── cse_daily_dividends.py                # Standalone CLI Python pipeline
├── cse_daily_dividends.ipynb             # Google Colab compatible notebook
├── COMB.N0000_dividends.csv              # Separate dividends-only output CSV
├── COMB.N0000_daily_with_dividends.csv   # Daily trading table with mapped dividends
├── requirements.txt                      # Python dependencies
├── .gitignore                            # Git ignore rules
├── LICENSE                               # MIT License
└── README.md                             # Documentation
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

## License

This project is licensed under the [MIT License](LICENSE).
