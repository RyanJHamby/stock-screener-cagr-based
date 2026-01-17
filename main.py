#!/usr/bin/env python3
"""
Daily Hyperperformance Stock Screener

Fetches, computes, and ranks all US stocks to identify companies with
expected annualized growth ≥30% for the next 3-5 years.
"""

import logging
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import argparse

import pandas as pd

import config
from fetch_data import get_fetcher
from compute_metrics import MetricsCalculator
from score_stocks import StockScorer

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.OUTPUT_DIR / f'screener_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StockScreener:
    """Main orchestrator for the stock screening process."""

    def __init__(self, limit: int = None, symbols: List[str] = None):
        """
        Initialize the stock screener.

        Args:
            limit: Maximum number of stocks to process (for testing)
            symbols: Specific symbols to process (overrides limit)
        """
        self.fetcher = get_fetcher()
        self.calculator = MetricsCalculator()
        self.scorer = StockScorer()
        self.limit = limit
        self.symbols = symbols

    def get_stock_symbols(self) -> List[str]:
        """Get the list of stock symbols to process."""
        if self.symbols:
            logger.info(f"Using provided symbols: {self.symbols}")
            return self.symbols

        logger.info("Fetching all US stock symbols...")
        symbols = self.fetcher.get_us_stock_symbols()

        if self.limit:
            symbols = symbols[:self.limit]
            logger.info(f"Limited to first {self.limit} symbols for testing")

        return symbols

    def process_stock(self, symbol: str) -> Dict:
        """
        Process a single stock: fetch data, compute metrics, and score.

        Returns:
            Dictionary with all metrics and scores, or None if processing failed
        """
        try:
            # Fetch all data
            stock_data = self.fetcher.get_all_stock_data(symbol)

            # Check if we have minimum required data
            if not stock_data.get('profile'):
                logger.warning(f"{symbol}: No profile data, skipping")
                return None

            # Compute metrics
            metrics = self.calculator.compute_all_metrics(stock_data)

            # Score the stock
            scored = self.scorer.score_stock(metrics)

            logger.info(f"{symbol}: Score = {scored.get('hyperperformance_score', 0):.2f}")
            return scored

        except Exception as e:
            logger.error(f"{symbol}: Error processing stock: {e}")
            return None

    def run_screening(self) -> List[Dict]:
        """
        Run the complete screening process on all stocks.

        Returns:
            List of scored and ranked stocks
        """
        logger.info("=" * 80)
        logger.info("Starting Daily Hyperperformance Stock Screener")
        logger.info(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # Get symbols
        symbols = self.get_stock_symbols()
        logger.info(f"Processing {len(symbols)} stocks...")

        # Process each stock
        scored_stocks = []
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{len(symbols)}] Processing {symbol}...")

            result = self.process_stock(symbol)
            if result:
                scored_stocks.append(result)

            # Progress update every 10 stocks
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(symbols)} stocks processed, {len(scored_stocks)} scored")

        logger.info(f"Completed processing. {len(scored_stocks)}/{len(symbols)} stocks successfully scored")

        # Rank stocks
        logger.info("Ranking stocks...")
        ranked_stocks = self.scorer.rank_stocks(scored_stocks)

        logger.info(f"Final ranking complete. Top performers: {len(ranked_stocks)}")
        return ranked_stocks

    def save_results(self, ranked_stocks: List[Dict], output_prefix: str = "screener_results"):
        """
        Save results to CSV and JSON files.

        Args:
            ranked_stocks: List of ranked stock data
            output_prefix: Prefix for output filenames
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON (full data)
        json_path = config.OUTPUT_DIR / f"{output_prefix}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(ranked_stocks, f, indent=2, default=str)
        logger.info(f"Saved full results to {json_path}")

        # Save as CSV (summary)
        csv_path = config.OUTPUT_DIR / f"{output_prefix}_{timestamp}.csv"
        if ranked_stocks:
            df = pd.DataFrame(ranked_stocks)

            # Select key columns for CSV
            key_columns = [
                'rank', 'symbol', 'hyperperformance_score', 'moat_score',
                'revenue_cagr_3yr', 'revenue_cagr_5yr',
                'eps_cagr_3yr', 'eps_cagr_5yr',
                'fcf_margin', 'roic', 'roe',
                'qoq_acceleration', 'insider_buy_ratio', 'analyst_buy_ratio',
                'market_cap', 'current_price', 'themes'
            ]

            # Only include columns that exist
            available_columns = [col for col in key_columns if col in df.columns]
            df_summary = df[available_columns]

            df_summary.to_csv(csv_path, index=False, float_format='%.2f')
            logger.info(f"Saved summary to {csv_path}")

        return json_path, csv_path

    def print_top_performers(self, ranked_stocks: List[Dict], top_n: int = 10):
        """Print top N performers to console."""
        print("\n" + "=" * 100)
        print(f"TOP {top_n} HYPERPERFORMANCE STOCKS")
        print("=" * 100)
        print(f"{'Rank':<6} {'Symbol':<10} {'Score':<8} {'Moat':<8} {'Rev CAGR':<12} {'EPS CAGR':<12} {'Themes':<30}")
        print("-" * 100)

        for stock in ranked_stocks[:top_n]:
            rank = stock.get('rank', '-')
            symbol = stock.get('symbol', '-')
            score = stock.get('hyperperformance_score', 0)
            moat = stock.get('moat_score', 0)

            # Get best CAGR values
            rev_cagr = stock.get('revenue_cagr_3yr') or stock.get('revenue_cagr_5yr') or 0
            eps_cagr = stock.get('eps_cagr_3yr') or stock.get('eps_cagr_5yr') or 0

            themes = ', '.join(stock.get('themes', [])) or 'N/A'

            print(f"{rank:<6} {symbol:<10} {score:<8.2f} {moat:<8.2f} {rev_cagr:<12.2f} {eps_cagr:<12.2f} {themes:<30}")

        print("=" * 100 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Daily Hyperperformance Stock Screener')
    parser.add_argument('--limit', type=int, help='Limit number of stocks to process (for testing)')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to process')
    parser.add_argument('--top', type=int, default=10, help='Number of top performers to display')
    args = parser.parse_args()

    try:
        # Initialize screener
        screener = StockScreener(limit=args.limit, symbols=args.symbols)

        # Run screening
        ranked_stocks = screener.run_screening()

        if not ranked_stocks:
            logger.warning("No stocks were successfully ranked!")
            return

        # Save results
        json_path, csv_path = screener.save_results(ranked_stocks)

        # Print top performers
        screener.print_top_performers(ranked_stocks, top_n=args.top)

        logger.info("Screening complete!")
        logger.info(f"Results saved to:")
        logger.info(f"  JSON: {json_path}")
        logger.info(f"  CSV: {csv_path}")

    except KeyboardInterrupt:
        logger.info("Screening interrupted by user")
    except Exception as e:
        logger.error(f"Screening failed with error: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
