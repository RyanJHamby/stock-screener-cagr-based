# Daily Hyperperformance Stock Screener

A Python-based stock screener that identifies US companies with expected annualized growth ≥30% for the next 3-5 years, using only the free Finnhub API.

## Overview

This screener analyzes all US stocks daily to identify potential "hyperperformers" - companies showing strong growth metrics, competitive moats, and positive momentum signals. It combines fundamental analysis with growth indicators to surface high-potential investment opportunities.

### Key Features

- **Comprehensive Data Collection**: Fetches income statements, balance sheets, cash flow, ratios, prices, insider transactions, and analyst estimates
- **Growth Metrics**: Calculates revenue/EPS CAGR (3yr & 5yr), quarter-over-quarter acceleration
- **Quality Indicators**: Evaluates ROIC, ROE, FCF margins, and debt levels
- **Moat Analysis**: Identifies competitive advantages through multiple proxies
- **Sentiment Signals**: Tracks insider buying and analyst recommendations
- **Smart Caching**: Minimizes API calls to stay within free-tier limits (60 calls/min)
- **Daily Automation**: Can run automatically via cron or GitHub Actions

## Methodology

### Hyperperformance Scoring (0-100)

The screener calculates a weighted score based on:

| Component | Weight | Description |
|-----------|--------|-------------|
| Revenue CAGR | 30% | 3-year and 5-year revenue growth rate |
| EPS CAGR | 30% | 3-year and 5-year earnings per share growth |
| FCF Margin | 15% | Free cash flow as % of revenue |
| ROIC/ROE | 10% | Return on invested capital and equity |
| Insider/Analyst Signals | 10% | Insider buying + analyst buy ratings |
| QoQ Acceleration | 5% | Sequential revenue growth momentum |

### Moat Score (0-1)

Competitive advantage proxies:

- **High ROIC** (>15%): Indicates operational excellence and pricing power
- **Stable Gross Margins**: Suggests sustainable competitive position
- **Revenue/EPS Acceleration**: Shows strong execution
- **Insider Buying**: Signals management confidence
- **Analyst Upgrades**: Reflects improving market perception

The moat score acts as a multiplier (up to 1.2x) on the base hyperperformance score.

### Thematic Classification

Stocks are tagged with themes:
- **AI**: Artificial intelligence, machine learning companies
- **Semiconductors**: Chip manufacturers, GPU/CPU makers
- **Energy Infrastructure**: Renewable energy, power, battery tech

## Installation

### Prerequisites

- Python 3.11 or higher
- Finnhub API key (free tier: 60 calls/minute)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stock-screener-cagr-based
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key**
   ```bash
   cp .env.example .env
   # Edit .env and add your Finnhub API key
   ```

4. **Get your Finnhub API key**
   - Visit https://finnhub.io/
   - Sign up for a free account
   - Copy your API key
   - Paste it into `.env` file

## Usage

### Basic Usage

Run the screener on all US stocks:

```bash
python main.py
```

### Testing Mode

Test with a limited number of stocks:

```bash
# Process only first 50 stocks
python main.py --limit 50

# Process specific symbols
python main.py --symbols AAPL MSFT GOOGL NVDA

# Show top 20 performers instead of default 10
python main.py --top 20
```

### Output

The screener generates two files in the `output/` directory:

1. **JSON file** (`screener_results_YYYYMMDD_HHMMSS.json`): Complete data with all metrics
2. **CSV file** (`screener_results_YYYYMMDD_HHMMSS.csv`): Summary with key metrics

Example console output:

```
====================================================================================================
TOP 10 HYPERPERFORMANCE STOCKS
====================================================================================================
Rank   Symbol     Score    Moat     Rev CAGR     EPS CAGR     Themes
----------------------------------------------------------------------------------------------------
1      NVDA       95.23    0.85     45.32        52.18        AI, Semiconductors
2      TSLA       87.45    0.72     38.45        41.23        Energy Infrastructure
3      AMD        84.12    0.68     35.67        38.90        Semiconductors
...
====================================================================================================
```

### Output Fields

| Field | Description |
|-------|-------------|
| rank | Overall ranking by hyperperformance score |
| symbol | Stock ticker |
| hyperperformance_score | Final score (0-100) |
| moat_score | Competitive advantage score (0-1) |
| revenue_cagr_3yr / 5yr | Revenue compound annual growth rate |
| eps_cagr_3yr / 5yr | Earnings per share CAGR |
| fcf_margin | Free cash flow margin (%) |
| roic / roe | Return on invested capital / equity (%) |
| qoq_acceleration | Quarter-over-quarter growth acceleration (%) |
| insider_buy_ratio | % of insider transactions that are buys |
| analyst_buy_ratio | % of analyst ratings that are buy/strong buy |
| market_cap | Market capitalization |
| current_price | Current stock price |
| themes | Thematic classifications |

## Architecture

### Project Structure

```
stock-screener-cagr-based/
├── main.py                 # Main orchestration script
├── fetch_data.py           # Finnhub API client with caching
├── compute_metrics.py      # Financial metrics calculations
├── score_stocks.py         # Scoring and ranking logic
├── config.py               # Configuration and constants
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── cache/                 # API response cache (auto-created)
├── output/                # Results output (auto-created)
└── .github/
    └── workflows/
        └── daily-screener.yml  # GitHub Actions automation
```

### Module Overview

#### `fetch_data.py`
- Handles all Finnhub API interactions
- Implements rate limiting (55 calls/minute for safety)
- Caches responses to minimize API usage
- Automatic retry with exponential backoff
- Fetches: company profiles, financials, metrics, quotes, insider transactions, analyst data

#### `compute_metrics.py`
- Extracts financial data from API responses
- Calculates CAGR for revenue and EPS
- Computes margins (FCF, gross, operating)
- Calculates ROIC, ROE, debt ratios
- Analyzes insider trading patterns
- Extracts analyst estimates and trends
- Classifies stocks into thematic categories

#### `score_stocks.py`
- Implements the hyperperformance scoring algorithm
- Calculates moat score based on competitive advantage proxies
- Normalizes metrics to 0-100 scale
- Applies weighted scoring
- Ranks and filters stocks

#### `main.py`
- Orchestrates the complete screening workflow
- Manages progress logging
- Handles errors gracefully
- Saves results in JSON and CSV formats
- Provides console output of top performers

## Automation

### Daily Scheduling with Cron

Add to your crontab to run daily at 6 PM EST:

```bash
crontab -e
```

Add this line:

```
0 18 * * * cd /path/to/stock-screener-cagr-based && /usr/bin/python3 main.py >> /var/log/stock-screener.log 2>&1
```

### GitHub Actions

The repository includes a GitHub Actions workflow (`.github/workflows/daily-screener.yml`) that runs automatically every day.

To use it:

1. Add your Finnhub API key as a repository secret:
   - Go to Settings → Secrets and variables → Actions
   - Create new secret: `FINNHUB_API_KEY`
   - Paste your API key

2. The workflow will run daily and upload results as artifacts

3. Customize the schedule by editing `.github/workflows/daily-screener.yml`

## Configuration

Edit `config.py` to customize:

- **Cache expiry times**: How long to cache different types of data
- **Scoring weights**: Adjust the importance of different metrics
- **Moat thresholds**: Change what qualifies as a competitive advantage
- **Stock filters**: Minimum market cap, trading volume
- **Thematic keywords**: Add/modify theme classifications

## Limitations & Considerations

### Free API Tier Limits

- **60 calls/minute**: The screener respects this with built-in rate limiting
- **Limited historical data**: Some endpoints may not return full 5-year history
- **Cache recommended**: First run will be slow; subsequent runs use cache

### Data Quality

- Not all stocks have complete financial data
- Stocks with insufficient data are filtered out
- Metrics requiring multi-year data need at least 2-3 years of history

### Investment Disclaimer

This tool is for **educational and research purposes only**. It is not financial advice. Always:
- Do your own research
- Consult with financial advisors
- Understand that past performance doesn't guarantee future results
- Be aware of risks in stock market investing

## Troubleshooting

### API Rate Limit Errors

If you see rate limit errors:
- Reduce `API_CALLS_PER_MINUTE` in `config.py`
- Use `--limit` flag to process fewer stocks initially
- Check cache is working (should see fewer API calls on reruns)

### Missing Data

Some stocks may not have all metrics:
- This is normal - not all companies report all data
- Stocks with too little data are filtered out
- Check logs for specific issues

### Cache Issues

Clear the cache if you suspect stale data:

```bash
rm -rf cache/
```

## Contributing

Contributions welcome! Areas for improvement:

- Additional data sources
- More sophisticated scoring algorithms
- Better handling of missing data
- UI/web interface
- Backtesting framework
- Portfolio optimization

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Data powered by [Finnhub.io](https://finnhub.io/)
- Inspired by growth investing principles and quantitative screening methodologies

---

**Last Updated**: January 2025
