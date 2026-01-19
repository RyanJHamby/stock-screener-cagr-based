# Long-Term Minervini Trend Template Screener

Senior quant implementation for 3-5 year holding horizon.
Built for **signal durability, not frequency**. Rejects shallow momentum and cyclical spikes.

## Philosophy

This is **not** the classic Minervini template for swing trading.
This is an institutional-grade extrapolation for **multi-year compounders**.

### Key Differences from Classic Template

| Classic Minervini | Long-Term Minervini |
|-------------------|---------------------|
| 50/150/200 DMA | 40-week / 80-week MA |
| Recent RS strength | 18+ month RS persistence |
| Breakout timing | Multi-year stair-step structure |
| Tight stop-losses | Structural trend violations only |
| High frequency signals | Low frequency, high conviction |

## Implementation

### Architecture

```
run_minervini.py          # Main orchestration
  └── MinerviniRunner     # Integration layer
      ├── price_data.py   # OHLC fetching (Finnhub)
      ├── minervini_longterm.py  # Core filters & scoring
      │   ├── TechnicalFilters
      │   ├── FundamentalFilters
      │   ├── InstitutionalOwnership
      │   └── LongTermScorer
      └── fetch_data.py   # Existing infrastructure
```

### Filters (All Toggleable)

#### 1. Regime Confirmation
```python
- Price > 40-week MA > 80-week MA
- 80-week MA slope positive ≥20/26 weeks
```
**Rejects:** Stocks in downtrends or rangebound

#### 2. RS Persistence
```python
- RS percentile ≥85 for 70%+ of last 18 months
- RS drawdown < SPY drawdown during corrections
```
**Rejects:** Recent momentum spikes, cyclical rotations

#### 3. Earnings Quality
```python
- Revenue CAGR ≥15% (3-5yr) OR operating margin expansion
- ROIC or gross margin trend positive
```
**Rejects:** Growth without profitability runway

#### 4. Trend Structure
```python
- Multi-year stair-step pattern (advance → consolidate → advance)
- Volatility contraction near rising long-term MAs
```
**Rejects:** Parabolic moves, unstable structures

#### 5. Structural Violation Detector
```python
- Flag: weekly close < 80-week MA + RS breakdown (RS < 70)
```
**Not a stop** - a warning signal for re-evaluation

#### 6. Valuation Disqualifier
```python
- Reject only if P/E > 2× (FCF_growth × 2)
```
**Not** a value screen - just removes extreme valuation risk

### Scoring System

**Composite Score = Weighted Average of:**

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| Trend Durability | 30% | Regime alignment, slope persistence, structure |
| RS Persistence | 30% | Historical RS strength, resilience |
| Fundamental Runway | 25% | Revenue quality, capital efficiency |
| Institutional Stability | 15% | Ownership trend stability |

**Output: 0-100 score, higher = better**

## Usage

### Basic Run

```bash
# Screen specific stocks
python run_minervini.py --symbols NVDA AVGO TSM AMD

# Screen top 100 from universe
python run_minervini.py --limit 100

# Full market scan (WARNING: Takes hours)
python run_minervini.py
```

### Toggle Filters

```bash
# Disable RS filter (for testing)
python run_minervini.py --no-rs --symbols AAPL MSFT

# Technical only (no fundamentals)
python run_minervini.py --no-fundamentals --limit 50

# Show top 50 instead of default 20
python run_minervini.py --limit 200 --top 50
```

### Virtual Environment

```bash
source venv/bin/activate
python run_minervini.py --symbols NVDA AMD AVGO TSM
```

## Output

### Console Output
```
============================================================
TOP 20 LONG-TERM MINERVINI STOCKS
============================================================
Rank   Symbol     Score    Trend    RS       Fundmtl  Inst     Price        Sector
------------------------------------------------------------
1      NVDA       87.5     95.0     92.0     78.0     65.0     $186.23      Semiconductors
2      AVGO       82.3     88.0     89.0     75.0     68.0     $351.71      Semiconductors
...
```

### Files Generated

```
output/
├── minervini_20260117_164500.json  # Full data with all metrics
├── minervini_20260117_164500.csv   # Ranked summary
└── minervini_20260117.log          # Execution log
```

### CSV Columns

- `rank` - Overall ranking
- `symbol` - Ticker
- `composite_score` - Final score (0-100)
- `trend_durability` - Trend component score
- `rs_persistence` - RS component score
- `fundamental_runway` - Fundamental score
- `institutional_stability` - Ownership score
- `current_price` - Current price
- `market_cap` - Market cap (millions)
- `sector` - Industry
- `regime_aligned` - Passed regime filter
- `rs_current` - Current RS percentile
- `revenue_cagr` - Revenue CAGR (%)
- `structural_violation` - Warning flag

## What Gets Filtered Out

### Disqualified Examples

**Regime Misalignment:**
- Stock trading below 40-week or 80-week MA
- 80-week MA not trending up

**RS Not Persistent:**
- Recent breakout but weak historical RS
- RS percentile was below 85 for most of last 18 months

**Revenue Quality:**
- Revenue CAGR < 15% AND no margin expansion
- Flat or declining margins

**Valuation:**
- Extreme P/E (>100) with no FCF growth to justify
- Example: P/E of 200 when FCF growing at 10%

## Integration with Existing Screener

Both screeners can run independently:

```bash
# Original hyperperformance screener (CAGR-based)
python main.py --symbols NVDA AMD --top 20

# New long-term Minervini screener (trend + durability)
python run_minervini.py --symbols NVDA AMD --top 20
```

**Use cases:**
- **main.py**: Find high-growth stocks (any trend state)
- **run_minervini.py**: Find established trends with durability

## Design Decisions

### Why Weekly MAs Instead of Daily?

Reduces noise, focuses on structural trends not intraday swings.

### Why 18-Month RS Requirement?

Eliminates sector rotations and recent momentum spikes.
Captures structural leadership, not tactical setups.

### Why No Hard Stop-Losses?

This is for position sizing and monitoring, not mechanical trading.
Structural violations are **warnings** requiring re-evaluation, not automatic exits.

### Why Valuation as Disqualifier Only?

Quality growth often trades at premium multiples.
We only reject **extreme** valuation disconnects.

### Why Institutional Ownership?

Placeholder for free-tier API limitations.
In production, this would track actual institutional flow.

## Limitations (Free Tier)

1. **No true institutional ownership data** - Finnhub free tier doesn't provide
2. **Limited historical depth** - Some stocks lack 5 years of clean data
3. **Rate limiting** - Full market scan takes hours
4. **No options/short interest** - Not available in free tier

## Production Enhancements

For institutional deployment:

1. **Use Bloomberg/FactSet** for institutional ownership
2. **Add short interest** as contrary indicator
3. **Options skew** for sentiment
4. **Earnings estimate revisions** trends
5. **Sector rotation** context
6. **Multi-timeframe** confirmation (daily + weekly)
7. **ML-based** regime classification
8. **Real-time monitoring** of structural violations

## Performance Notes

- **First run**: Slow (API rate limits + cache building)
- **Subsequent runs**: Much faster (cache hits)
- **Full universe scan**: 2-4 hours
- **Symbol list (10-20 stocks)**: 2-5 minutes

## Examples

### Find Next NVIDIA

```bash
python run_minervini.py --symbols NVDA AMD AVGO TSM QCOM MRVL --top 10
```

### Screen Semiconductor Sector

```bash
python run_minervini.py --symbols \
  NVDA AMD INTC AVGO TSM QCOM AMAT LRCX KLAC ASML MU \
  --top 10
```

### Test Single Stock

```bash
python run_minervini.py --symbols AAPL
```

## Interpreting Scores

| Score | Interpretation |
|-------|---------------|
| 80-100 | Elite long-term compounder - structural trend intact |
| 60-80 | Strong candidate - monitor for continuation |
| 40-60 | Mixed - partial qualification |
| 20-40 | Weak - likely disqualified on key filter |
| 0-20 | Disqualified - failed primary filters |

## Warning Signals

Monitor qualified stocks for:

1. **Structural Violation**: Close below 80-week MA + RS breakdown
2. **RS Deterioration**: RS percentile drops below 70
3. **Margin Compression**: Margins declining for 2+ quarters
4. **Institutional Exit**: Large decrease in ownership (when data available)

---

**Built for:** Long-term position building, not tactical trading
**Philosophy:** Quality over quantity, durability over frequency
**Time Horizon:** 3-5 year holds, not 3-5 month swings
