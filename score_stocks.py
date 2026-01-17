"""Scoring system for identifying hyperperformance stocks."""

import logging
from typing import Dict, List
import numpy as np

import config

logger = logging.getLogger(__name__)


class StockScorer:
    """Calculate moat scores and hyperperformance scores for stocks."""

    def __init__(self):
        self.weights = config.SCORING_WEIGHTS
        self.moat_thresholds = config.MOAT_THRESHOLDS

    def normalize_score(self, value: float, min_val: float, max_val: float, reverse: bool = False) -> float:
        """
        Normalize a value to 0-100 scale.
        If reverse=True, lower values get higher scores.
        """
        if value is None:
            return 0.0

        if max_val == min_val:
            return 50.0

        if reverse:
            normalized = 100 * (max_val - value) / (max_val - min_val)
        else:
            normalized = 100 * (value - min_val) / (max_val - min_val)

        return max(0.0, min(100.0, normalized))

    def calculate_moat_score(self, metrics: Dict) -> float:
        """
        Calculate moat score (0-1) based on competitive advantage proxies.

        Proxies:
        - High ROIC (>15%) → operational moat
        - Stable gross margin → pricing power
        - Revenue/EPS acceleration → execution advantage
        - Insider buying → confidence signal
        - Analyst upward revisions → market perception
        """
        moat_components = []

        # 1. High ROIC (weight: 30%)
        roic = metrics.get('roic')
        if roic is not None:
            if roic >= self.moat_thresholds['high_roic']:
                moat_components.append(0.30)
            elif roic >= 10:
                moat_components.append(0.15)

        # 2. Revenue growth consistency (weight: 25%)
        revenue_cagr_3 = metrics.get('revenue_cagr_3yr')
        revenue_cagr_5 = metrics.get('revenue_cagr_5yr')

        if revenue_cagr_3 and revenue_cagr_5:
            avg_growth = (revenue_cagr_3 + revenue_cagr_5) / 2
            if avg_growth >= self.moat_thresholds['min_revenue_cagr']:
                consistency = 1 - abs(revenue_cagr_3 - revenue_cagr_5) / max(revenue_cagr_3, revenue_cagr_5, 1)
                moat_components.append(0.25 * consistency)

        # 3. Execution (acceleration) (weight: 20%)
        acceleration = metrics.get('qoq_acceleration')
        if acceleration is not None and acceleration > 0:
            # Positive acceleration is good
            moat_components.append(min(0.20, 0.20 * (acceleration / 10)))

        # 4. Insider confidence (weight: 15%)
        insider_buy_ratio = metrics.get('insider_buy_ratio')
        if insider_buy_ratio is not None:
            if insider_buy_ratio >= 70:  # Strong buying
                moat_components.append(0.15)
            elif insider_buy_ratio >= 50:
                moat_components.append(0.10)

        # 5. Analyst perception (weight: 10%)
        analyst_buy_ratio = metrics.get('analyst_buy_ratio')
        if analyst_buy_ratio is not None:
            if analyst_buy_ratio >= 70:
                moat_components.append(0.10)
            elif analyst_buy_ratio >= 50:
                moat_components.append(0.05)

        # Sum up to get final moat score (0-1)
        moat_score = sum(moat_components)
        return min(1.0, moat_score)

    def calculate_revenue_cagr_score(self, metrics: Dict) -> float:
        """Score based on revenue CAGR (30% weight)."""
        cagr_3 = metrics.get('revenue_cagr_3yr')
        cagr_5 = metrics.get('revenue_cagr_5yr')

        if cagr_3 is None and cagr_5 is None:
            return 0.0

        # Use best available
        cagr = cagr_3 if cagr_3 is not None else cagr_5
        if cagr_3 and cagr_5:
            cagr = max(cagr_3, cagr_5)  # Use the better one

        # Normalize: 0% = 0, 50%+ = 100
        score = self.normalize_score(cagr, 0, 50)

        # Bonus for exceeding 30% target
        if cagr >= 30:
            score = min(100, score * 1.2)

        return score

    def calculate_eps_cagr_score(self, metrics: Dict) -> float:
        """Score based on EPS CAGR (30% weight)."""
        cagr_3 = metrics.get('eps_cagr_3yr')
        cagr_5 = metrics.get('eps_cagr_5yr')

        if cagr_3 is None and cagr_5 is None:
            return 0.0

        # Use best available
        cagr = cagr_3 if cagr_3 is not None else cagr_5
        if cagr_3 and cagr_5:
            cagr = max(cagr_3, cagr_5)

        # Normalize: 0% = 0, 50%+ = 100
        score = self.normalize_score(cagr, 0, 50)

        # Bonus for exceeding 30% target
        if cagr >= 30:
            score = min(100, score * 1.2)

        return score

    def calculate_fcf_score(self, metrics: Dict) -> float:
        """Score based on FCF margin and growth (15% weight)."""
        fcf_margin = metrics.get('fcf_margin')

        if fcf_margin is None:
            return 0.0

        # Normalize: -10% = 0, 30%+ = 100
        score = self.normalize_score(fcf_margin, -10, 30)

        return score

    def calculate_roic_roe_score(self, metrics: Dict) -> float:
        """Score based on ROIC and ROE (10% weight)."""
        roic = metrics.get('roic')
        roe = metrics.get('roe')

        if roic is None and roe is None:
            return 0.0

        scores = []

        if roic is not None:
            # ROIC: 0% = 0, 30%+ = 100
            scores.append(self.normalize_score(roic, 0, 30))

        if roe is not None:
            # ROE: 0% = 0, 30%+ = 100
            scores.append(self.normalize_score(roe, 0, 30))

        return np.mean(scores) if scores else 0.0

    def calculate_insider_analyst_score(self, metrics: Dict) -> float:
        """Score based on insider buying and analyst sentiment (10% weight)."""
        insider_buy_ratio = metrics.get('insider_buy_ratio')
        analyst_buy_ratio = metrics.get('analyst_buy_ratio')
        forward_eps_growth = metrics.get('forward_eps_growth')

        scores = []

        if insider_buy_ratio is not None:
            # 50% buying = 50, 100% = 100
            scores.append(self.normalize_score(insider_buy_ratio, 0, 100))

        if analyst_buy_ratio is not None:
            # 50% buy = 50, 100% = 100
            scores.append(self.normalize_score(analyst_buy_ratio, 0, 100))

        if forward_eps_growth is not None:
            # 0% = 0, 50%+ = 100
            scores.append(self.normalize_score(forward_eps_growth, 0, 50))

        return np.mean(scores) if scores else 0.0

    def calculate_acceleration_score(self, metrics: Dict) -> float:
        """Score based on QoQ acceleration (5% weight)."""
        acceleration = metrics.get('qoq_acceleration')

        if acceleration is None:
            return 0.0

        # Normalize: -10% = 0, 10%+ = 100
        score = self.normalize_score(acceleration, -10, 10)

        return score

    def calculate_hyperperformance_score(self, metrics: Dict) -> Dict:
        """
        Calculate final Hyperperformance Score (0-100).

        Weighted components:
        - Revenue CAGR: 30%
        - EPS CAGR: 30%
        - FCF margin & growth: 15%
        - ROIC/ROE: 10%
        - Insider + analyst: 10%
        - Acceleration: 5%
        """
        # Calculate component scores
        revenue_score = self.calculate_revenue_cagr_score(metrics)
        eps_score = self.calculate_eps_cagr_score(metrics)
        fcf_score = self.calculate_fcf_score(metrics)
        roic_roe_score = self.calculate_roic_roe_score(metrics)
        insider_analyst_score = self.calculate_insider_analyst_score(metrics)
        acceleration_score = self.calculate_acceleration_score(metrics)

        # Calculate moat score
        moat_score = self.calculate_moat_score(metrics)

        # Weighted sum
        final_score = (
            revenue_score * self.weights['revenue_cagr'] +
            eps_score * self.weights['eps_cagr'] +
            fcf_score * self.weights['fcf_margin_growth'] +
            roic_roe_score * self.weights['roic_roe'] +
            insider_analyst_score * self.weights['insider_analyst'] +
            acceleration_score * self.weights['acceleration']
        )

        # Apply moat multiplier (up to 1.2x for perfect moat)
        moat_multiplier = 1 + (moat_score * 0.2)
        final_score = min(100, final_score * moat_multiplier)

        return {
            'hyperperformance_score': final_score,
            'moat_score': moat_score,
            'component_scores': {
                'revenue_cagr': revenue_score,
                'eps_cagr': eps_score,
                'fcf': fcf_score,
                'roic_roe': roic_roe_score,
                'insider_analyst': insider_analyst_score,
                'acceleration': acceleration_score
            }
        }

    def score_stock(self, metrics: Dict) -> Dict:
        """Score a single stock and return enhanced metrics."""
        scoring_result = self.calculate_hyperperformance_score(metrics)

        # Merge with original metrics
        result = metrics.copy()
        result.update(scoring_result)

        return result

    def rank_stocks(self, scored_stocks: List[Dict]) -> List[Dict]:
        """
        Rank stocks by hyperperformance score.
        Apply filters for minimum requirements.
        """
        # Filter out stocks with insufficient data or low scores
        filtered = []

        for stock in scored_stocks:
            symbol = stock.get('symbol', 'UNKNOWN')
            score = stock.get('hyperperformance_score', 0)

            # Must have hyperperformance score > 0
            if score == 0:
                logger.debug(f"{symbol}: Filtered out - zero score")
                continue

            # Check for minimum data requirements (only if strict filtering)
            if config.STRICT_FILTERING:
                # Must have at least one of revenue or EPS CAGR
                has_revenue_cagr = stock.get('revenue_cagr_3yr') or stock.get('revenue_cagr_5yr')
                has_eps_cagr = stock.get('eps_cagr_3yr') or stock.get('eps_cagr_5yr')

                if not has_revenue_cagr and not has_eps_cagr:
                    logger.debug(f"{symbol}: Filtered out - no CAGR data")
                    continue

            # Optional: Check minimum market cap (only if strict filtering is enabled)
            # Note: Finnhub returns market cap in millions of USD
            if config.STRICT_FILTERING and config.MIN_MARKET_CAP > 0:
                market_cap = stock.get('market_cap')
                if market_cap is not None and market_cap > 0:
                    # Convert to actual value (Finnhub gives it in millions)
                    market_cap_actual = market_cap * 1_000_000
                    if market_cap_actual < config.MIN_MARKET_CAP:
                        logger.debug(f"{symbol}: Filtered out - market cap ${market_cap_actual:,.0f} < ${config.MIN_MARKET_CAP:,.0f}")
                        continue

            filtered.append(stock)
            logger.debug(f"{symbol}: Included - score {score:.2f}")

        # Sort by hyperperformance score (descending)
        ranked = sorted(filtered, key=lambda x: x.get('hyperperformance_score', 0), reverse=True)

        # Add rank
        for i, stock in enumerate(ranked, 1):
            stock['rank'] = i

        return ranked
