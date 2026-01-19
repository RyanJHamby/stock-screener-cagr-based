#!/usr/bin/env python3
"""
Long-term Minervini Screener Runner
Integrates with existing Finnhub infrastructure
"""

import logging
from datetime import datetime
from pathlib import Path
import json
import pandas as pd
from typing import List, Dict

import config
from fetch_data import get_fetcher
from price_data import PriceDataFetcher, validate_us_listing, build_financial_series, build_ownership_series
from minervini_longterm import LongTermMinerviniScreener

logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.OUTPUT_DIR / f'minervini_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MinerviniRunner:
    """Main runner for long-term Minervini screening"""

    def __init__(self, symbols: List[str] = None, limit: int = None,
                 enable_regime: bool = True, enable_rs: bool = True,
                 enable_fundamentals: bool = True, enable_structure: bool = True):
        self.finnhub_fetcher = get_fetcher()
        self.price_fetcher = PriceDataFetcher(self.finnhub_fetcher.client)
        self.screener = LongTermMinerviniScreener(
            enable_regime=enable_regime,
            enable_rs=enable_rs,
            enable_fundamentals=enable_fundamentals,
            enable_structure=enable_structure
        )

        self.symbols = symbols
        self.limit = limit
        self.spy_prices = None

    def get_stock_universe(self) -> List[str]:
        """Get US-listed stock symbols"""
        if self.symbols:
            return self.symbols

        logger.info("Fetching US stock universe...")
        all_symbols = self.finnhub_fetcher.get_us_stock_symbols()

        us_symbols = []
        for i, symbol in enumerate(all_symbols[:self.limit] if self.limit else all_symbols):
            if i % 100 == 0:
                logger.info(f"Filtering US stocks: {i}/{len(all_symbols)}")

            profile = self.finnhub_fetcher.get_company_profile(symbol)

            if validate_us_listing(symbol, profile):
                us_symbols.append(symbol)

        logger.info(f"US-listed stocks: {len(us_symbols)}/{len(all_symbols)}")
        return us_symbols

    def load_spy_benchmark(self):
        """Load S&P 500 data for RS calculations"""
        if self.spy_prices is None:
            logger.info("Loading SPY benchmark data...")
            self.spy_prices = self.price_fetcher.get_spy_prices(years=5)

            if self.spy_prices is None or len(self.spy_prices) < 1000:
                logger.error("Failed to load SPY data - RS calculations will fail")
                raise ValueError("SPY benchmark data required")

            logger.info(f"Loaded SPY data: {len(self.spy_prices)} days")

    def screen_stock(self, symbol: str) -> Dict:
        """Screen single stock through full pipeline"""
        logger.info(f"Screening {symbol}...")

        profile = self.finnhub_fetcher.get_company_profile(symbol)

        if not validate_us_listing(symbol, profile):
            logger.info(f"{symbol}: Not US-listed, skipping")
            return None

        prices = self.price_fetcher.get_daily_prices(symbol, years=5)
        if prices is None or len(prices) < 500:
            logger.warning(f"{symbol}: Insufficient price history")
            return None

        financials_reported = self.finnhub_fetcher.get_financials_reported(symbol)
        basic_financials = self.finnhub_fetcher.get_basic_financials(symbol)

        financials = build_financial_series(financials_reported, basic_financials)

        if len(financials) < 3:
            logger.warning(f"{symbol}: Insufficient financial history")
            return None

        insider_data = self.finnhub_fetcher.get_insider_transactions(symbol)
        ownership = build_ownership_series(insider_data)

        quote = self.finnhub_fetcher.get_quote(symbol)
        current_price = quote.get('c') if quote else None

        basic_metrics = basic_financials.get('metric', {}) if basic_financials else {}
        current_pe = basic_metrics.get('peNormalizedAnnual')

        try:
            result = self.screener.screen_stock(
                symbol=symbol,
                prices=prices,
                spy_prices=self.spy_prices,
                financials=financials,
                ownership=ownership,
                current_pe=current_pe
            )

            result['current_price'] = current_price
            result['market_cap'] = profile.get('marketCapitalization') if profile else None
            result['sector'] = profile.get('finnhubIndustry') if profile else None

            return result

        except Exception as e:
            logger.error(f"{symbol}: Screening error: {e}", exc_info=True)
            return None

    def run(self) -> List[Dict]:
        """Execute full screening run"""
        logger.info("=" * 100)
        logger.info("LONG-TERM MINERVINI TREND SCREENER")
        logger.info(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 100)

        self.load_spy_benchmark()

        symbols = self.get_stock_universe()
        logger.info(f"Screening {len(symbols)} stocks...")

        results = []
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{len(symbols)}] Processing {symbol}")

            result = self.screen_stock(symbol)

            if result:
                results.append(result)

                if 'disqualified' not in result:
                    score = result.get('composite_score', 0)
                    logger.info(f"{symbol}: QUALIFIED - Score: {score:.2f}")
                else:
                    logger.info(f"{symbol}: Disqualified - {result['disqualified']}")

            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(symbols)} processed, {len(results)} results")

        logger.info(f"Screening complete: {len(results)} stocks processed")

        ranked = self.screener.rank_stocks(results)
        logger.info(f"Qualified stocks: {len(ranked)}")

        return ranked

    def save_results(self, ranked_stocks: List[Dict], prefix: str = "minervini"):
        """Save results to JSON and CSV"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_path = config.OUTPUT_DIR / f"{prefix}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(ranked_stocks, f, indent=2, default=str)
        logger.info(f"Saved JSON: {json_path}")

        if ranked_stocks:
            rows = []
            for stock in ranked_stocks:
                row = {
                    'rank': stock.get('rank'),
                    'symbol': stock['symbol'],
                    'composite_score': stock.get('composite_score', 0),
                    'trend_durability': stock.get('scores', {}).get('trend_durability', 0),
                    'rs_persistence': stock.get('scores', {}).get('rs_persistence', 0),
                    'fundamental_runway': stock.get('scores', {}).get('fundamental_runway', 0),
                    'institutional_stability': stock.get('scores', {}).get('institutional_stability', 0),
                    'current_price': stock.get('current_price'),
                    'market_cap': stock.get('market_cap'),
                    'sector': stock.get('sector'),
                    'regime_aligned': stock.get('regime', {}).get('regime_aligned'),
                    'rs_current': stock.get('rs', {}).get('rs_current'),
                    'revenue_cagr': stock.get('revenue_quality', {}).get('revenue_cagr'),
                    'structural_violation': stock.get('violation', {}).get('structural_violation')
                }
                rows.append(row)

            df = pd.DataFrame(rows)
            csv_path = config.OUTPUT_DIR / f"{prefix}_{timestamp}.csv"
            df.to_csv(csv_path, index=False, float_format='%.2f')
            logger.info(f"Saved CSV: {csv_path}")

        return json_path, csv_path

    def print_top_stocks(self, ranked_stocks: List[Dict], top_n: int = 20):
        """Print top qualified stocks"""
        print("\n" + "=" * 120)
        print(f"TOP {top_n} LONG-TERM MINERVINI STOCKS")
        print("=" * 120)
        print(f"{'Rank':<6} {'Symbol':<10} {'Score':<8} {'Trend':<8} {'RS':<8} {'Fundmtl':<8} {'Inst':<8} {'Price':<12} {'Sector':<25}")
        print("-" * 120)

        for stock in ranked_stocks[:top_n]:
            rank = stock.get('rank', '-')
            symbol = stock['symbol']
            score = stock.get('composite_score', 0)

            scores = stock.get('scores', {})
            trend = scores.get('trend_durability', 0)
            rs = scores.get('rs_persistence', 0)
            fund = scores.get('fundamental_runway', 0)
            inst = scores.get('institutional_stability', 0)

            price = stock.get('current_price', 0)
            sector = stock.get('sector', 'N/A')[:24]

            print(f"{rank:<6} {symbol:<10} {score:<8.1f} {trend:<8.1f} {rs:<8.1f} {fund:<8.1f} {inst:<8.1f} ${price:<11.2f} {sector:<25}")

        print("=" * 120 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Long-term Minervini Trend Screener')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to screen')
    parser.add_argument('--limit', type=int, help='Limit number of stocks')
    parser.add_argument('--top', type=int, default=20, help='Number of top results to display')
    parser.add_argument('--no-regime', action='store_true', help='Disable regime filter')
    parser.add_argument('--no-rs', action='store_true', help='Disable RS filter')
    parser.add_argument('--no-fundamentals', action='store_true', help='Disable fundamental filters')
    parser.add_argument('--no-structure', action='store_true', help='Disable trend structure filter')

    args = parser.parse_args()

    runner = MinerviniRunner(
        symbols=args.symbols,
        limit=args.limit,
        enable_regime=not args.no_regime,
        enable_rs=not args.no_rs,
        enable_fundamentals=not args.no_fundamentals,
        enable_structure=not args.no_structure
    )

    try:
        ranked = runner.run()

        if not ranked:
            logger.warning("No stocks qualified!")
            return

        runner.save_results(ranked)
        runner.print_top_stocks(ranked, top_n=args.top)

        logger.info(f"Screening complete! {len(ranked)} stocks qualified")

    except KeyboardInterrupt:
        logger.info("Screening interrupted by user")
    except Exception as e:
        logger.error(f"Screening failed: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
