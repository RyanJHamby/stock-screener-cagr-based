#!/usr/bin/env python3
"""
Test script to verify the stock screener setup.

This script tests:
1. API key configuration
2. Finnhub API connectivity
3. Data fetching
4. Metrics calculation
5. Scoring system

Run this after setup to ensure everything is working correctly.
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_config():
    """Test configuration loading."""
    logger.info("Testing configuration...")
    try:
        import config
        assert config.FINNHUB_API_KEY, "API key is empty"
        assert len(config.FINNHUB_API_KEY) > 10, "API key looks invalid"
        logger.info("✓ Configuration loaded successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False


def test_data_fetcher():
    """Test data fetching module."""
    logger.info("Testing data fetcher...")
    try:
        from fetch_data import get_fetcher

        fetcher = get_fetcher()
        logger.info("  Fetching test stock data for AAPL...")

        # Test basic API call
        profile = fetcher.get_company_profile('AAPL')
        if not profile:
            logger.error("✗ Failed to fetch company profile")
            return False

        logger.info(f"  Retrieved profile: {profile.get('name', 'N/A')}")

        # Test quote
        quote = fetcher.get_quote('AAPL')
        if quote and quote.get('c'):
            logger.info(f"  Current price: ${quote['c']:.2f}")

        logger.info("✓ Data fetcher working correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Data fetcher test failed: {e}")
        return False


def test_metrics_calculator():
    """Test metrics calculation."""
    logger.info("Testing metrics calculator...")
    try:
        from compute_metrics import MetricsCalculator

        calc = MetricsCalculator()

        # Test CAGR calculation
        cagr = calc.calculate_cagr(100, 200, 3)
        assert cagr is not None, "CAGR calculation returned None"
        assert 25 < cagr < 30, f"CAGR calculation incorrect: {cagr}"

        logger.info(f"  CAGR test: 100 → 200 over 3 years = {cagr:.2f}%")
        logger.info("✓ Metrics calculator working correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Metrics calculator test failed: {e}")
        return False


def test_scorer():
    """Test scoring system."""
    logger.info("Testing scorer...")
    try:
        from score_stocks import StockScorer

        scorer = StockScorer()

        # Test with sample metrics
        sample_metrics = {
            'symbol': 'TEST',
            'revenue_cagr_3yr': 35.0,
            'revenue_cagr_5yr': 32.0,
            'eps_cagr_3yr': 40.0,
            'eps_cagr_5yr': 38.0,
            'fcf_margin': 20.0,
            'roic': 18.0,
            'roe': 22.0,
            'qoq_acceleration': 5.0,
            'insider_buy_ratio': 75.0,
            'analyst_buy_ratio': 80.0,
        }

        scored = scorer.score_stock(sample_metrics)
        score = scored.get('hyperperformance_score', 0)

        assert score > 0, "Score should be positive for good metrics"
        assert score <= 100, "Score should not exceed 100"

        logger.info(f"  Sample stock score: {score:.2f}")
        logger.info(f"  Moat score: {scored.get('moat_score', 0):.2f}")
        logger.info("✓ Scorer working correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Scorer test failed: {e}")
        return False


def test_full_pipeline():
    """Test the full pipeline with a real stock."""
    logger.info("Testing full pipeline with AAPL...")
    try:
        from fetch_data import get_fetcher
        from compute_metrics import MetricsCalculator
        from score_stocks import StockScorer

        fetcher = get_fetcher()
        calculator = MetricsCalculator()
        scorer = StockScorer()

        # Fetch data
        logger.info("  Fetching data...")
        stock_data = fetcher.get_all_stock_data('AAPL')

        # Compute metrics
        logger.info("  Computing metrics...")
        metrics = calculator.compute_all_metrics(stock_data)

        # Score
        logger.info("  Scoring...")
        scored = scorer.score_stock(metrics)

        score = scored.get('hyperperformance_score', 0)
        logger.info(f"  AAPL Hyperperformance Score: {score:.2f}")

        if score > 0:
            logger.info("✓ Full pipeline working correctly")
            return True
        else:
            logger.warning("! Pipeline ran but score is 0 (may indicate missing data)")
            return True
    except Exception as e:
        logger.error(f"✗ Full pipeline test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("STOCK SCREENER SETUP VERIFICATION")
    print("=" * 70)
    print()

    tests = [
        ("Configuration", test_config),
        ("Data Fetcher", test_data_fetcher),
        ("Metrics Calculator", test_metrics_calculator),
        ("Scorer", test_scorer),
        ("Full Pipeline", test_full_pipeline),
    ]

    results = []
    for name, test_func in tests:
        print()
        success = test_func()
        results.append((name, success))
        print()

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:10} {name}")
        if not success:
            all_passed = False

    print()
    if all_passed:
        print("All tests passed! Your screener is ready to use.")
        print("\nRun the screener with:")
        print("  python main.py --limit 10")
        return 0
    else:
        print("Some tests failed. Please check the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
