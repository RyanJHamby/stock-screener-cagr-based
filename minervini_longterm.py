"""
Long-term Minervini Trend Template (3-5 year horizon)
Senior quant implementation for durability over frequency
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TechnicalFilters:
    """Technical regime and trend structure filters"""

    @staticmethod
    def regime_confirmation(prices: pd.DataFrame) -> Dict:
        """
        Price > 40wk MA > 80wk MA
        80wk MA slope positive for 26+ weeks

        Args:
            prices: DataFrame with 'close' column, daily frequency

        Returns:
            Dict with regime metrics
        """
        weekly = prices.resample('W').last()
        current_price = weekly['close'].iloc[-1]

        ma_40w = weekly['close'].rolling(40).mean()
        ma_80w = weekly['close'].rolling(80).mean()

        current_ma40 = ma_40w.iloc[-1]
        current_ma80 = ma_80w.iloc[-1]

        regime_aligned = current_price > current_ma40 > current_ma80

        ma80_slope = ma_80w.diff()
        slope_positive_weeks = (ma80_slope.iloc[-26:] > 0).sum()
        slope_persistent = slope_positive_weeks >= 20

        return {
            'regime_aligned': regime_aligned,
            'price': current_price,
            'ma_40w': current_ma40,
            'ma_80w': current_ma80,
            'slope_persistent': slope_persistent,
            'slope_positive_pct': slope_positive_weeks / 26
        }

    @staticmethod
    def relative_strength_persistent(prices: pd.DataFrame, spy_prices: pd.DataFrame,
                                     lookback_months: int = 18) -> Dict:
        """
        RS percentile ≥85 for 18+ months
        RS drawdown < index drawdown during corrections

        Args:
            prices: Stock daily prices
            spy_prices: S&P 500 daily prices
            lookback_months: Persistence period
        """
        lookback_days = lookback_months * 21

        stock_returns = prices['close'].pct_change()
        spy_returns = spy_prices['close'].pct_change()

        relative_perf = (1 + stock_returns).cumprod() / (1 + spy_returns).cumprod()

        rolling_rs_pct = relative_perf.rolling(252).apply(
            lambda x: 100 * (x.iloc[-1] > x).sum() / len(x)
        )

        rs_above_85 = (rolling_rs_pct.iloc[-lookback_days:] >= 85).sum()
        rs_persistence_pct = rs_above_85 / lookback_days if lookback_days > 0 else 0

        stock_dd = (prices['close'] / prices['close'].cummax() - 1).min()
        spy_dd = (spy_prices['close'] / spy_prices['close'].cummax() - 1).min()

        rs_resilience = stock_dd > spy_dd if spy_dd < -0.05 else True

        return {
            'rs_current': rolling_rs_pct.iloc[-1],
            'rs_persistence_pct': rs_persistence_pct,
            'rs_persistent': rs_persistence_pct >= 0.70,
            'rs_resilience': rs_resilience,
            'stock_max_dd': stock_dd,
            'spy_max_dd': spy_dd
        }

    @staticmethod
    def trend_structure(prices: pd.DataFrame) -> Dict:
        """
        Identify multi-year stair-step advances
        Volatility contraction near rising MAs

        Args:
            prices: Daily price data
        """
        weekly = prices.resample('W').last()

        ma_40w = weekly['close'].rolling(40).mean()

        distance_from_ma = (weekly['close'] - ma_40w) / ma_40w

        recent_distance = distance_from_ma.iloc[-13:].mean()
        avg_distance = distance_from_ma.iloc[-52:].mean()

        near_ma = abs(recent_distance) < 0.05

        volatility_20w = weekly['close'].pct_change().rolling(20).std()
        volatility_52w = weekly['close'].pct_change().rolling(52).std()

        current_vol = volatility_20w.iloc[-1]
        avg_vol = volatility_52w.iloc[-1]

        vol_contracting = current_vol < avg_vol * 0.8 if avg_vol > 0 else False

        returns_52w = weekly['close'].pct_change(52)
        positive_years = (returns_52w > 0).sum()

        stair_step = positive_years >= len(returns_52w) * 0.6

        return {
            'near_rising_ma': near_ma,
            'vol_contracting': vol_contracting,
            'vol_ratio': current_vol / avg_vol if avg_vol > 0 else 1,
            'stair_step_pattern': stair_step,
            'distance_from_ma': recent_distance
        }

    @staticmethod
    def structural_violation(prices: pd.DataFrame, rs_data: Dict) -> Dict:
        """
        Flag: weekly close < 80wk MA + RS breakdown

        Args:
            prices: Daily prices
            rs_data: RS metrics from relative_strength_persistent
        """
        weekly = prices.resample('W').last()
        ma_80w = weekly['close'].rolling(80).mean()

        current_price = weekly['close'].iloc[-1]
        current_ma80 = ma_80w.iloc[-1]

        price_violation = current_price < current_ma80
        rs_breakdown = rs_data['rs_current'] < 70

        structural_break = price_violation and rs_breakdown

        return {
            'structural_violation': structural_break,
            'price_below_80ma': price_violation,
            'rs_breakdown': rs_breakdown
        }


class FundamentalFilters:
    """Earnings quality and fundamental runway"""

    @staticmethod
    def revenue_growth_quality(financials: List[Dict], years: int = 5) -> Dict:
        """
        3-5 year revenue CAGR ≥15%
        Operating margin expansion

        Args:
            financials: List of annual financial data dicts with revenue, operating_margin
            years: Lookback period
        """
        if len(financials) < 2:
            return {'revenue_cagr': None, 'margin_expansion': False, 'quality_score': 0}

        sorted_fin = sorted(financials, key=lambda x: x['year'])

        if len(sorted_fin) >= years + 1:
            start_rev = sorted_fin[-(years+1)].get('revenue')
            end_rev = sorted_fin[-1].get('revenue')
            revenue_cagr = ((end_rev / start_rev) ** (1/years) - 1) * 100 if (start_rev and end_rev and start_rev > 0) else None
        else:
            revenue_cagr = None

        margins = [f.get('operating_margin') for f in sorted_fin[-years:]]
        valid_margins = [m for m in margins if m is not None]
        margin_expansion = all(valid_margins[i] <= valid_margins[i+1] for i in range(len(valid_margins)-1)) if len(valid_margins) >= 2 else False

        margin_trend_positive = valid_margins[-1] > valid_margins[0] if len(valid_margins) >= 2 and valid_margins[0] is not None and valid_margins[-1] is not None else False

        quality_pass = (revenue_cagr and revenue_cagr >= 15) or margin_expansion

        quality_score = 0
        if revenue_cagr and revenue_cagr >= 15:
            quality_score += 0.5
        if margin_expansion:
            quality_score += 0.3
        if margin_trend_positive:
            quality_score += 0.2

        return {
            'revenue_cagr': revenue_cagr,
            'margin_expansion': margin_expansion,
            'margin_trend_positive': margin_trend_positive,
            'quality_pass': quality_pass,
            'quality_score': quality_score
        }

    @staticmethod
    def capital_efficiency(financials: List[Dict], years: int = 5) -> Dict:
        """
        ROIC or gross margin trend positive

        Args:
            financials: Financial data with roic, gross_margin
            years: Trend period
        """
        sorted_fin = sorted(financials, key=lambda x: x['year'])[-years:]

        if len(sorted_fin) < 2:
            return {'roic_trend_positive': False, 'margin_trend_positive': False, 'efficiency_score': 0}

        roics = [f.get('roic') for f in sorted_fin]
        gross_margins = [f.get('gross_margin') for f in sorted_fin]

        valid_roics = [r for r in roics if r is not None]
        valid_margins = [m for m in gross_margins if m is not None]

        roic_trend = valid_roics[-1] > valid_roics[0] if len(valid_roics) >= 2 else False
        margin_trend = valid_margins[-1] > valid_margins[0] if len(valid_margins) >= 2 else False

        roic_slope = np.polyfit(range(len(valid_roics)), valid_roics, 1)[0] if len(valid_roics) >= 2 else 0
        margin_slope = np.polyfit(range(len(valid_margins)), valid_margins, 1)[0] if len(valid_margins) >= 2 else 0

        efficiency_score = 0
        if roic_trend:
            efficiency_score += 0.5
        if margin_trend:
            efficiency_score += 0.5

        return {
            'roic_trend_positive': roic_trend,
            'margin_trend_positive': margin_trend,
            'roic_slope': roic_slope,
            'margin_slope': margin_slope,
            'efficiency_score': efficiency_score
        }

    @staticmethod
    def valuation_disqualifier(price: float, fcf_growth: float, current_pe: float) -> bool:
        """
        Disqualify only if FCF growth cannot justify multiple in 3-5 years

        Args:
            price: Current price
            fcf_growth: Historical FCF CAGR
            current_pe: Current P/E ratio

        Returns:
            True if disqualified
        """
        if current_pe is None or current_pe <= 0:
            return False

        if fcf_growth is None:
            return current_pe > 100

        justified_pe = fcf_growth * 2 if fcf_growth > 0 else 15

        disqualified = current_pe > justified_pe * 2

        return disqualified


class InstitutionalOwnership:
    """Institutional ownership stability metrics"""

    @staticmethod
    def ownership_stability(ownership_history: List[Dict]) -> Dict:
        """
        Track institutional ownership changes over time

        Args:
            ownership_history: List of quarterly ownership data
        """
        if len(ownership_history) < 4:
            return {'stable': False, 'trend': 'unknown', 'stability_score': 0}

        sorted_own = sorted(ownership_history, key=lambda x: x['quarter'])

        inst_pcts = [o['institutional_pct'] for o in sorted_own[-8:]]

        if len(inst_pcts) < 2:
            return {'stable': False, 'trend': 'unknown', 'stability_score': 0}

        pct_changes = [abs(inst_pcts[i] - inst_pcts[i-1]) for i in range(1, len(inst_pcts))]
        avg_change = np.mean(pct_changes)

        stable = avg_change < 5

        trend = 'increasing' if inst_pcts[-1] > inst_pcts[0] else 'decreasing'

        stability_score = max(0, 1 - avg_change / 10)

        return {
            'stable': stable,
            'trend': trend,
            'avg_change': avg_change,
            'current_institutional_pct': inst_pcts[-1],
            'stability_score': stability_score
        }


class LongTermScorer:
    """Composite scoring for long-term durability"""

    WEIGHTS = {
        'trend_durability': 0.30,
        'rs_persistence': 0.30,
        'fundamental_runway': 0.25,
        'institutional_stability': 0.15
    }

    @staticmethod
    def trend_durability_score(regime: Dict, structure: Dict, violation: Dict) -> float:
        """
        Score trend durability (0-100)

        Components:
        - Regime alignment
        - Slope persistence
        - Stair-step pattern
        - No structural violation
        """
        score = 0

        if regime['regime_aligned']:
            score += 30

        score += regime['slope_positive_pct'] * 30

        if structure['stair_step_pattern']:
            score += 20

        if structure['vol_contracting']:
            score += 10

        if not violation['structural_violation']:
            score += 10

        return min(100, score)

    @staticmethod
    def rs_persistence_score(rs: Dict) -> float:
        """
        Score RS persistence (0-100)

        Components:
        - Current RS level
        - Historical persistence
        - Resilience during corrections
        """
        score = 0

        if rs['rs_current'] >= 90:
            score += 40
        elif rs['rs_current'] >= 85:
            score += 30
        elif rs['rs_current'] >= 75:
            score += 20

        score += rs['rs_persistence_pct'] * 40

        if rs['rs_resilience']:
            score += 20

        return min(100, score)

    @staticmethod
    def fundamental_runway_score(revenue_qual: Dict, capital_eff: Dict) -> float:
        """
        Score fundamental runway (0-100)

        Components:
        - Revenue quality
        - Capital efficiency
        """
        score = 0

        score += revenue_qual['quality_score'] * 50
        score += capital_eff['efficiency_score'] * 50

        return min(100, score)

    @staticmethod
    def institutional_score(ownership: Dict) -> float:
        """Score institutional stability (0-100)"""
        score = ownership['stability_score'] * 100
        return min(100, score)

    @staticmethod
    def composite_score(trend_dur: float, rs_persist: float, fund_runway: float, inst: float) -> float:
        """
        Calculate weighted composite score

        Returns:
            Score 0-100
        """
        w = LongTermScorer.WEIGHTS

        composite = (
            trend_dur * w['trend_durability'] +
            rs_persist * w['rs_persistence'] +
            fund_runway * w['fundamental_runway'] +
            inst * w['institutional_stability']
        )

        return composite


class LongTermMinerviniScreener:
    """Main screening engine"""

    def __init__(self, enable_regime: bool = True, enable_rs: bool = True,
                 enable_fundamentals: bool = True, enable_structure: bool = True):
        self.enable_regime = enable_regime
        self.enable_rs = enable_rs
        self.enable_fundamentals = enable_fundamentals
        self.enable_structure = enable_structure

        self.tech_filters = TechnicalFilters()
        self.fund_filters = FundamentalFilters()
        self.inst_filters = InstitutionalOwnership()
        self.scorer = LongTermScorer()

    def screen_stock(self, symbol: str, prices: pd.DataFrame, spy_prices: pd.DataFrame,
                     financials: List[Dict], ownership: List[Dict],
                     current_pe: float = None) -> Dict:
        """
        Screen single stock

        Args:
            symbol: Stock ticker
            prices: Daily OHLC with 'close' column
            spy_prices: S&P 500 daily prices
            financials: Annual financial data
            ownership: Quarterly institutional ownership
            current_pe: Current P/E ratio

        Returns:
            Dict with all metrics and composite score
        """
        result = {'symbol': symbol}

        regime = self.tech_filters.regime_confirmation(prices)
        result['regime'] = regime

        if self.enable_regime:
            if not regime['regime_aligned']:
                result['disqualified'] = 'regime_misalignment'
                result['composite_score'] = 0
                return result

        rs = self.tech_filters.relative_strength_persistent(prices, spy_prices)
        result['rs'] = rs

        if self.enable_rs:
            if not rs['rs_persistent']:
                result['disqualified'] = 'rs_not_persistent'
                result['composite_score'] = 0
                return result

        structure = self.tech_filters.trend_structure(prices)
        result['structure'] = structure

        violation = self.tech_filters.structural_violation(prices, rs)
        result['violation'] = violation

        revenue_qual = self.fund_filters.revenue_growth_quality(financials)
        capital_eff = self.fund_filters.capital_efficiency(financials)
        result['revenue_quality'] = revenue_qual
        result['capital_efficiency'] = capital_eff

        if self.enable_fundamentals:
            if not revenue_qual['quality_pass']:
                result['disqualified'] = 'revenue_quality'
                result['composite_score'] = 0
                return result

            fcf_growth = revenue_qual['revenue_cagr']
            if self.fund_filters.valuation_disqualifier(prices['close'].iloc[-1], fcf_growth, current_pe):
                result['disqualified'] = 'valuation'
                result['composite_score'] = 0
                return result

        inst_own = self.inst_filters.ownership_stability(ownership)
        result['institutional'] = inst_own

        trend_dur_score = self.scorer.trend_durability_score(regime, structure, violation)
        rs_persist_score = self.scorer.rs_persistence_score(rs)
        fund_runway_score = self.scorer.fundamental_runway_score(revenue_qual, capital_eff)
        inst_score = self.scorer.institutional_score(inst_own)

        result['scores'] = {
            'trend_durability': trend_dur_score,
            'rs_persistence': rs_persist_score,
            'fundamental_runway': fund_runway_score,
            'institutional_stability': inst_score
        }

        composite = self.scorer.composite_score(trend_dur_score, rs_persist_score,
                                                fund_runway_score, inst_score)
        result['composite_score'] = composite

        return result

    def rank_stocks(self, screening_results: List[Dict]) -> List[Dict]:
        """
        Rank screened stocks by composite score

        Args:
            screening_results: List of results from screen_stock

        Returns:
            Sorted list with ranks
        """
        qualified = [r for r in screening_results if 'disqualified' not in r]

        ranked = sorted(qualified, key=lambda x: x['composite_score'], reverse=True)

        for i, stock in enumerate(ranked, 1):
            stock['rank'] = i

        return ranked
