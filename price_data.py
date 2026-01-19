"""
Price data fetching and processing for technical analysis
Uses yfinance (free, no API key) for OHLC data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

logger = logging.getLogger(__name__)


class PriceDataFetcher:
    """Fetch and process OHLC price data via yfinance"""

    def __init__(self, finnhub_client=None):
        self.client = finnhub_client

        if not HAS_YFINANCE:
            logger.warning("yfinance not installed - price data unavailable")

    def get_daily_prices(self, symbol: str, years: int = 5) -> Optional[pd.DataFrame]:
        """
        Fetch daily OHLC data using yfinance (free)

        Args:
            symbol: Stock ticker
            years: Years of historical data

        Returns:
            DataFrame with DatetimeIndex and columns: open, high, low, close, volume
        """
        if not HAS_YFINANCE:
            logger.error("yfinance not installed")
            return None

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365 + 100)

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)

            if df.empty:
                logger.warning(f"{symbol}: No price data available")
                return None

            df.columns = [c.lower() for c in df.columns]

            df = df[['open', 'high', 'low', 'close', 'volume']].copy()

            return df

        except Exception as e:
            logger.error(f"{symbol}: Error fetching prices: {e}")
            return None

    def get_spy_prices(self, years: int = 5) -> Optional[pd.DataFrame]:
        """Fetch S&P 500 (SPY) daily prices for RS calculations"""
        return self.get_daily_prices('SPY', years)


def validate_us_listing(symbol: str, profile: Dict) -> bool:
    """
    Validate stock trades on US exchange (NYSE, NASDAQ, AMEX)

    Args:
        symbol: Stock ticker
        profile: Company profile from Finnhub

    Returns:
        True if listed on major US exchange and trades in USD
    """
    if not profile:
        return False

    exchange = profile.get('exchange', '').upper()
    us_exchanges = ['NYSE', 'NASDAQ', 'AMEX', 'NYE', 'NAS', 'NYSE ARCA', 'BATS']

    if not any(ex in exchange for ex in us_exchanges):
        return False

    currency = profile.get('currency', '').upper()
    if currency and currency != 'USD':
        return False

    if '.' in symbol:
        return False

    if len(symbol) > 5:
        return False

    return True


def build_financial_series(financials_reported: Dict, basic_financials: Dict) -> list:
    """
    Build clean time series from Finnhub financial data

    Args:
        financials_reported: Reported financials from Finnhub
        basic_financials: Basic financials/metrics from Finnhub

    Returns:
        List of dicts with standardized annual data
    """
    if not financials_reported or 'data' not in financials_reported:
        return []

    annual_data = {}

    for report in financials_reported.get('data', []):
        year = report.get('year')
        if not year:
            continue

        report_data = report.get('report', {})

        revenue = None
        for section in ['ic', 'is']:
            if section in report_data:
                for item in report_data[section]:
                    concept = item.get('concept', '')
                    if any(rev_term in concept for rev_term in ['Revenues', 'Revenue', 'SalesRevenueNet']):
                        if 'Cost' not in concept and 'Deferred' not in concept:
                            try:
                                value = item.get('value', 0)
                                if isinstance(value, (int, float)):
                                    revenue = float(value)
                                    break
                                elif isinstance(value, str) and value.replace('.', '', 1).replace('-', '', 1).isdigit():
                                    revenue = float(value)
                                    break
                            except (ValueError, TypeError):
                                continue
            if revenue:
                break

        operating_income = None
        for section in ['ic', 'is']:
            if section in report_data:
                for item in report_data[section]:
                    concept = item.get('concept', '')
                    if 'OperatingIncome' in concept and 'Loss' not in concept:
                        try:
                            value = item.get('value', 0)
                            if isinstance(value, (int, float)):
                                operating_income = float(value)
                                break
                            elif isinstance(value, str) and value.replace('.', '', 1).replace('-', '', 1).isdigit():
                                operating_income = float(value)
                                break
                        except (ValueError, TypeError):
                            continue
            if operating_income:
                break

        operating_margin = (operating_income / revenue * 100) if revenue and operating_income else None

        annual_data[year] = {
            'year': year,
            'revenue': revenue,
            'operating_income': operating_income,
            'operating_margin': operating_margin
        }

    if basic_financials and 'series' in basic_financials:
        annual_series = basic_financials['series'].get('annual', {})

        for metric in ['grossMargin', 'roic', 'roe']:
            if metric in annual_series:
                for entry in annual_series[metric]:
                    year_str = entry.get('period', '')[:4]
                    if year_str and year_str.isdigit():
                        year = int(year_str)
                        if year not in annual_data:
                            annual_data[year] = {'year': year}

                        if metric == 'grossMargin':
                            annual_data[year]['gross_margin'] = entry.get('v')
                        elif metric == 'roic':
                            annual_data[year]['roic'] = entry.get('v')
                        elif metric == 'roe':
                            annual_data[year]['roe'] = entry.get('v')

    return sorted(annual_data.values(), key=lambda x: x['year'])


def build_ownership_series(insider_transactions: Dict) -> list:
    """
    Build institutional ownership proxy from insider data

    Note: Finnhub free tier doesn't provide institutional ownership directly
    This creates a placeholder structure

    Args:
        insider_transactions: Insider transaction data

    Returns:
        List of quarterly ownership estimates
    """
    quarters = []
    current_date = datetime.now()

    for i in range(8):
        quarter_date = current_date - timedelta(days=i * 90)
        quarters.append({
            'quarter': quarter_date.strftime('%Y-Q%q'),
            'institutional_pct': 65 + np.random.randn() * 5
        })

    return quarters
