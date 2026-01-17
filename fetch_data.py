"""Data fetching module for Finnhub API with caching and rate limiting."""

import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

import finnhub
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config

# Set up logging
logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.call_times = []

    def wait_if_needed(self):
        """Wait if we're about to exceed the rate limit."""
        now = time.time()
        # Remove calls older than 1 minute
        self.call_times = [t for t in self.call_times if now - t < 60]

        if len(self.call_times) >= self.calls_per_minute:
            # Wait until the oldest call is more than 1 minute old
            sleep_time = 60 - (now - self.call_times[0]) + 1
            if sleep_time > 0:
                logger.info(f"Rate limit approaching, sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.call_times = []

        self.call_times.append(time.time())


class CacheManager:
    """Manages caching of API responses."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate a cache key from endpoint and parameters."""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, endpoint: str, params: Dict, max_age: int) -> Optional[Any]:
        """Retrieve cached data if it exists and is not expired."""
        cache_key = self._get_cache_key(endpoint, params)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)

            # Check if cache is expired
            cached_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now() - cached_time > timedelta(seconds=max_age):
                logger.debug(f"Cache expired for {endpoint}")
                return None

            logger.debug(f"Cache hit for {endpoint}")
            return cached_data['data']
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    def set(self, endpoint: str, params: Dict, data: Any):
        """Store data in cache."""
        cache_key = self._get_cache_key(endpoint, params)
        cache_path = self._get_cache_path(cache_key)

        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }, f)
            logger.debug(f"Cached data for {endpoint}")
        except Exception as e:
            logger.warning(f"Error writing cache: {e}")


class FinnhubDataFetcher:
    """Fetches stock data from Finnhub API with caching and rate limiting."""

    def __init__(self):
        self.client = finnhub.Client(api_key=config.FINNHUB_API_KEY)
        self.rate_limiter = RateLimiter(config.API_CALLS_PER_MINUTE)
        self.cache = CacheManager(config.CACHE_DIR)

    @retry(
        stop=stop_after_attempt(config.API_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=config.API_RETRY_DELAY, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def _api_call(self, func, *args, **kwargs):
        """Make an API call with rate limiting and retry logic."""
        self.rate_limiter.wait_if_needed()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise

    def get_us_stock_symbols(self) -> List[str]:
        """Fetch all US stock symbols."""
        endpoint = 'stock_symbols'
        params = {'exchange': 'US'}

        # Check cache
        cached = self.cache.get(endpoint, params, config.CACHE_EXPIRY['stock_list'])
        if cached is not None:
            return cached

        logger.info("Fetching US stock symbols from Finnhub")
        symbols_data = self._api_call(self.client.stock_symbols, 'US')

        # Extract symbol list and filter
        symbols = [
            item['symbol'] for item in symbols_data
            if item.get('type') == 'Common Stock' and '.' not in item['symbol']
        ]

        self.cache.set(endpoint, params, symbols)
        logger.info(f"Fetched {len(symbols)} US stock symbols")
        return symbols

    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """Fetch company profile for a symbol."""
        endpoint = 'company_profile'
        params = {'symbol': symbol}

        cached = self.cache.get(endpoint, params, config.CACHE_EXPIRY['financials'])
        if cached is not None:
            return cached

        try:
            profile = self._api_call(self.client.company_profile2, symbol=symbol)
            self.cache.set(endpoint, params, profile)
            return profile
        except Exception as e:
            logger.warning(f"Failed to fetch profile for {symbol}: {e}")
            return None

    def get_financials_reported(self, symbol: str) -> Optional[Dict]:
        """Fetch reported financials (income statement, balance sheet, cash flow)."""
        endpoint = 'financials_reported'
        params = {'symbol': symbol}

        cached = self.cache.get(endpoint, params, config.CACHE_EXPIRY['financials'])
        if cached is not None:
            return cached

        try:
            financials = self._api_call(self.client.financials_reported, symbol=symbol, freq='annual')
            self.cache.set(endpoint, params, financials)
            return financials
        except Exception as e:
            logger.warning(f"Failed to fetch financials for {symbol}: {e}")
            return None

    def get_basic_financials(self, symbol: str) -> Optional[Dict]:
        """Fetch basic financials and metrics."""
        endpoint = 'basic_financials'
        params = {'symbol': symbol}

        cached = self.cache.get(endpoint, params, config.CACHE_EXPIRY['metrics'])
        if cached is not None:
            return cached

        try:
            metrics = self._api_call(self.client.company_basic_financials, symbol, 'all')
            self.cache.set(endpoint, params, metrics)
            return metrics
        except Exception as e:
            logger.warning(f"Failed to fetch basic financials for {symbol}: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Fetch current stock price quote."""
        endpoint = 'quote'
        params = {'symbol': symbol}

        cached = self.cache.get(endpoint, params, config.CACHE_EXPIRY['price'])
        if cached is not None:
            return cached

        try:
            quote = self._api_call(self.client.quote, symbol)
            self.cache.set(endpoint, params, quote)
            return quote
        except Exception as e:
            logger.warning(f"Failed to fetch quote for {symbol}: {e}")
            return None

    def get_insider_transactions(self, symbol: str) -> Optional[Dict]:
        """Fetch insider transactions for the last 12 months."""
        endpoint = 'insider_transactions'
        # Get transactions from last year
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        params = {'symbol': symbol, 'from': from_date, 'to': to_date}

        cached = self.cache.get(endpoint, params, config.CACHE_EXPIRY['insider'])
        if cached is not None:
            return cached

        try:
            transactions = self._api_call(
                self.client.stock_insider_transactions,
                symbol,
                from_date,
                to_date
            )
            self.cache.set(endpoint, params, transactions)
            return transactions
        except Exception as e:
            logger.warning(f"Failed to fetch insider transactions for {symbol}: {e}")
            return None

    def get_earnings_estimates(self, symbol: str) -> Optional[Dict]:
        """Fetch analyst earnings estimates."""
        endpoint = 'earnings_estimates'
        params = {'symbol': symbol}

        cached = self.cache.get(endpoint, params, config.CACHE_EXPIRY['estimates'])
        if cached is not None:
            return cached

        try:
            estimates = self._api_call(self.client.company_earnings, symbol, limit=5)
            self.cache.set(endpoint, params, estimates)
            return estimates
        except Exception as e:
            logger.warning(f"Failed to fetch earnings estimates for {symbol}: {e}")
            return None

    def get_recommendation_trends(self, symbol: str) -> Optional[List]:
        """Fetch analyst recommendation trends."""
        endpoint = 'recommendation_trends'
        params = {'symbol': symbol}

        cached = self.cache.get(endpoint, params, config.CACHE_EXPIRY['estimates'])
        if cached is not None:
            return cached

        try:
            recommendations = self._api_call(self.client.recommendation_trends, symbol)
            self.cache.set(endpoint, params, recommendations)
            return recommendations
        except Exception as e:
            logger.warning(f"Failed to fetch recommendations for {symbol}: {e}")
            return None

    def get_all_stock_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch all available data for a stock symbol."""
        logger.info(f"Fetching all data for {symbol}")

        return {
            'symbol': symbol,
            'profile': self.get_company_profile(symbol),
            'financials': self.get_financials_reported(symbol),
            'basic_financials': self.get_basic_financials(symbol),
            'quote': self.get_quote(symbol),
            'insider_transactions': self.get_insider_transactions(symbol),
            'earnings': self.get_earnings_estimates(symbol),
            'recommendations': self.get_recommendation_trends(symbol),
        }


# Singleton instance
_fetcher_instance = None

def get_fetcher() -> FinnhubDataFetcher:
    """Get or create the FinnhubDataFetcher singleton."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = FinnhubDataFetcher()
    return _fetcher_instance
