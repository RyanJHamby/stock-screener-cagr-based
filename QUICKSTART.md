# Quick Start Guide

Get the stock screener running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Get Your API Key

1. Go to https://finnhub.io/
2. Click "Get free API key"
3. Sign up (takes 30 seconds)
4. Copy your API key

## Step 3: Configure

```bash
cp .env.example .env
```

Edit `.env` and paste your API key:

```
FINNHUB_API_KEY=your_actual_key_here
```

## Step 4: Test Your Setup

```bash
python test_setup.py
```

All tests should pass ✓

## Step 5: Run a Test Screener

Start with just 20 stocks to test:

```bash
python main.py --limit 20
```

This will:
- Fetch data for 20 stocks
- Calculate all metrics
- Score and rank them
- Show top 10 performers
- Save results to `output/`

**Expected runtime**: 2-5 minutes (depending on API speed and caching)

## Step 6: Run Full Screener

Once you're happy with the test results:

```bash
python main.py
```

This will process all US stocks (may take 1-2 hours on first run due to API rate limits).

**Tip**: Subsequent runs are much faster thanks to caching!

## Understanding the Output

### Console Output

```
====================================================================================================
TOP 10 HYPERPERFORMANCE STOCKS
====================================================================================================
Rank   Symbol     Score    Moat     Rev CAGR     EPS CAGR     Themes
----------------------------------------------------------------------------------------------------
1      NVDA       95.23    0.85     45.32        52.18        AI, Semiconductors
```

- **Score**: Overall hyperperformance score (0-100). Higher = better growth potential
- **Moat**: Competitive advantage score (0-1). Higher = stronger business moat
- **Rev CAGR**: Revenue compound annual growth rate (%)
- **EPS CAGR**: Earnings per share growth rate (%)
- **Themes**: Industry classifications

### Files Generated

In the `output/` directory:

1. **JSON file**: Complete data with all metrics
2. **CSV file**: Summary spreadsheet (open in Excel/Google Sheets)
3. **LOG file**: Detailed execution log

## Common Use Cases

### Test with Specific Stocks

```bash
python main.py --symbols AAPL MSFT GOOGL NVDA AMD TSLA
```

### Show More Results

```bash
python main.py --limit 50 --top 20
```

Shows top 20 instead of top 10.

### Schedule Daily Runs

**macOS/Linux** (using cron):

```bash
crontab -e
```

Add:

```
0 18 * * * cd /path/to/stock-screener-cagr-based && python3 main.py
```

**GitHub Actions** (automated on GitHub):

1. Push code to GitHub
2. Add `FINNHUB_API_KEY` to repository secrets
3. Workflow runs automatically daily at 6 PM EST

## Interpreting Scores

### Hyperperformance Score

- **90-100**: Exceptional growth with strong fundamentals
- **80-90**: Very strong growth potential
- **70-80**: Good growth prospects
- **60-70**: Moderate growth
- **<60**: May not meet 30% CAGR target

### Moat Score

- **0.8-1.0**: Very strong competitive advantages
- **0.6-0.8**: Good moat indicators
- **0.4-0.6**: Some advantages
- **<0.4**: Limited moat evidence

## What to Look For

High-potential stocks typically have:

✓ Revenue CAGR > 30%
✓ EPS CAGR > 30%
✓ Positive FCF margin
✓ ROIC > 15%
✓ Insider buying
✓ Strong analyst ratings
✓ QoQ acceleration

## Troubleshooting

### "API key not found"

Make sure `.env` file exists and contains your key.

### "Rate limit exceeded"

The screener respects rate limits, but if you see this:
- Wait a few minutes and try again
- Reduce stocks processed: `--limit 10`

### "No stocks were successfully ranked"

- Check your internet connection
- Verify API key is valid
- Try with a test symbol: `--symbols AAPL`

### Caching Issues

Clear the cache:

```bash
rm -rf cache/
```

## Next Steps

1. Review the top performers in detail
2. Research individual companies
3. Compare with your own analysis
4. Set up automated daily runs
5. Track performance over time

## Remember

⚠️ **This tool is for research only, not financial advice**

Always:
- Do your own due diligence
- Diversify your investments
- Consult financial advisors
- Understand the risks

---

Happy screening! 📊📈
