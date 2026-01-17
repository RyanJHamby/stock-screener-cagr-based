"""Compute financial metrics and growth indicators."""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime

import config

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate financial metrics from raw data."""

    @staticmethod
    def calculate_cagr(start_value: float, end_value: float, years: int) -> Optional[float]:
        """
        Calculate Compound Annual Growth Rate.
        CAGR = (end_value / start_value) ^ (1 / years) - 1
        """
        if start_value <= 0 or end_value <= 0 or years <= 0:
            return None

        try:
            cagr = (end_value / start_value) ** (1 / years) - 1
            return cagr * 100  # Return as percentage
        except Exception as e:
            logger.debug(f"CAGR calculation error: {e}")
            return None

    @staticmethod
    def extract_revenue_history(financials_data: Optional[Dict]) -> List[Tuple[str, float]]:
        """Extract revenue history from financials data."""
        if not financials_data or 'data' not in financials_data:
            return []

        revenues = []
        for report in financials_data.get('data', []):
            try:
                year = report.get('year')
                report_data = report.get('report', {})

                # Try different possible keys for revenue
                revenue = None
                for key in ['ic', 'is']:  # Income statement sections
                    if key in report_data:
                        for item in report_data[key]:
                            if item.get('concept') in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet']:
                                revenue = float(item.get('value', 0))
                                break
                    if revenue:
                        break

                if year and revenue:
                    revenues.append((str(year), revenue))
            except Exception as e:
                logger.debug(f"Error extracting revenue: {e}")
                continue

        # Sort by year descending (most recent first)
        revenues.sort(key=lambda x: x[0], reverse=True)
        return revenues

    @staticmethod
    def extract_eps_history(basic_financials: Optional[Dict]) -> List[Tuple[str, float]]:
        """Extract EPS history from basic financials."""
        if not basic_financials or 'series' not in basic_financials:
            return []

        eps_data = basic_financials.get('series', {}).get('annual', {}).get('eps', [])
        if not eps_data:
            return []

        eps_history = []
        for entry in eps_data:
            try:
                period = entry.get('period')
                value = entry.get('v')
                if period and value is not None:
                    eps_history.append((period, float(value)))
            except Exception as e:
                logger.debug(f"Error extracting EPS: {e}")
                continue

        eps_history.sort(key=lambda x: x[0], reverse=True)
        return eps_history

    def compute_revenue_cagr(self, financials_data: Optional[Dict]) -> Dict[str, Optional[float]]:
        """Compute revenue CAGR for 3 and 5 years."""
        revenues = self.extract_revenue_history(financials_data)

        if len(revenues) < 2:
            return {'revenue_cagr_3yr': None, 'revenue_cagr_5yr': None}

        # 3-year CAGR
        cagr_3yr = None
        if len(revenues) >= 4:  # Need 4 data points for 3 years
            cagr_3yr = self.calculate_cagr(revenues[3][1], revenues[0][1], 3)

        # 5-year CAGR
        cagr_5yr = None
        if len(revenues) >= 6:  # Need 6 data points for 5 years
            cagr_5yr = self.calculate_cagr(revenues[5][1], revenues[0][1], 5)

        return {
            'revenue_cagr_3yr': cagr_3yr,
            'revenue_cagr_5yr': cagr_5yr
        }

    def compute_eps_cagr(self, basic_financials: Optional[Dict]) -> Dict[str, Optional[float]]:
        """Compute EPS CAGR for 3 and 5 years."""
        eps_history = self.extract_eps_history(basic_financials)

        if len(eps_history) < 2:
            return {'eps_cagr_3yr': None, 'eps_cagr_5yr': None}

        # 3-year CAGR
        cagr_3yr = None
        if len(eps_history) >= 4:
            cagr_3yr = self.calculate_cagr(eps_history[3][1], eps_history[0][1], 3)

        # 5-year CAGR
        cagr_5yr = None
        if len(eps_history) >= 6:
            cagr_5yr = self.calculate_cagr(eps_history[5][1], eps_history[0][1], 5)

        return {
            'eps_cagr_3yr': cagr_3yr,
            'eps_cagr_5yr': cagr_5yr
        }

    def compute_qoq_acceleration(self, basic_financials: Optional[Dict]) -> Optional[float]:
        """
        Compute quarter-over-quarter acceleration.
        Acceleration = current QoQ growth - previous QoQ growth
        """
        if not basic_financials or 'series' not in basic_financials:
            return None

        quarterly_revenue = basic_financials.get('series', {}).get('quarterly', {}).get('revenue', [])
        if len(quarterly_revenue) < 3:
            return None

        try:
            # Sort by period (most recent first)
            quarterly_revenue.sort(key=lambda x: x.get('period', ''), reverse=True)

            q1 = quarterly_revenue[0].get('v', 0)
            q2 = quarterly_revenue[1].get('v', 0)
            q3 = quarterly_revenue[2].get('v', 0)

            if q2 == 0 or q3 == 0:
                return None

            # Calculate growth rates
            current_growth = (q1 - q2) / q2
            previous_growth = (q2 - q3) / q3

            # Acceleration is the difference
            acceleration = (current_growth - previous_growth) * 100
            return acceleration
        except Exception as e:
            logger.debug(f"Error computing QoQ acceleration: {e}")
            return None

    def compute_fcf_margin(self, financials_data: Optional[Dict]) -> Optional[float]:
        """
        Compute Free Cash Flow margin.
        FCF Margin = (Operating Cash Flow - CapEx) / Revenue
        """
        if not financials_data or 'data' not in financials_data:
            return None

        try:
            # Get most recent year data
            recent = financials_data['data'][0]
            report = recent.get('report', {})

            ocf = None
            capex = None
            revenue = None

            # Extract from cash flow statement
            if 'cf' in report:
                for item in report['cf']:
                    concept = item.get('concept', '')
                    if 'OperatingCashFlow' in concept or concept == 'NetCashProvidedByUsedInOperatingActivities':
                        ocf = float(item.get('value', 0))
                    if 'CapitalExpenditure' in concept or concept == 'PaymentsToAcquirePropertyPlantAndEquipment':
                        capex = abs(float(item.get('value', 0)))  # Usually negative

            # Extract revenue
            if 'ic' in report or 'is' in report:
                for key in ['ic', 'is']:
                    if key in report:
                        for item in report[key]:
                            if item.get('concept') in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax']:
                                revenue = float(item.get('value', 0))
                                break
                    if revenue:
                        break

            if ocf is not None and capex is not None and revenue and revenue > 0:
                fcf = ocf - capex
                fcf_margin = (fcf / revenue) * 100
                return fcf_margin
        except Exception as e:
            logger.debug(f"Error computing FCF margin: {e}")

        return None

    def compute_roic_roe_trend(self, basic_financials: Optional[Dict]) -> Dict[str, Optional[float]]:
        """Extract ROIC and ROE metrics."""
        result = {
            'roic': None,
            'roe': None,
            'roic_5yr_avg': None,
            'roe_5yr_avg': None
        }

        if not basic_financials or 'metric' not in basic_financials:
            return result

        metrics = basic_financials.get('metric', {})

        # Current values
        result['roic'] = metrics.get('roic')
        result['roe'] = metrics.get('roe')

        # Try to get 5-year averages
        result['roic_5yr_avg'] = metrics.get('roic5Y')
        result['roe_5yr_avg'] = metrics.get('roe5Y')

        return result

    def compute_debt_to_ebitda(self, basic_financials: Optional[Dict]) -> Optional[float]:
        """Compute Net Debt / EBITDA ratio."""
        if not basic_financials or 'metric' not in basic_financials:
            return None

        metrics = basic_financials.get('metric', {})

        # Try to get directly
        debt_ebitda = metrics.get('totalDebt/totalEquityAnnual')
        if debt_ebitda:
            return debt_ebitda

        # Try to calculate
        try:
            total_debt = metrics.get('totalDebtAnnual')
            cash = metrics.get('cashAnnual', 0)
            ebitda = metrics.get('ebitdaAnnual')

            if total_debt is not None and ebitda and ebitda > 0:
                net_debt = total_debt - cash
                return net_debt / ebitda
        except Exception as e:
            logger.debug(f"Error computing debt/EBITDA: {e}")

        return None

    def compute_insider_buying_trend(self, insider_data: Optional[Dict]) -> Dict[str, Optional[float]]:
        """
        Analyze insider transactions to compute buying trend.
        Returns percentage of insider buying vs selling.
        """
        result = {
            'insider_buy_ratio': None,
            'net_insider_shares': None
        }

        if not insider_data or 'data' not in insider_data:
            return result

        try:
            transactions = insider_data['data']
            buy_shares = 0
            sell_shares = 0

            for tx in transactions:
                shares = tx.get('share', 0)
                tx_type = tx.get('transactionCode', '')

                # P = Purchase, S = Sale
                if 'P' in tx_type:
                    buy_shares += shares
                elif 'S' in tx_type:
                    sell_shares += shares

            total_shares = buy_shares + sell_shares
            if total_shares > 0:
                result['insider_buy_ratio'] = (buy_shares / total_shares) * 100
                result['net_insider_shares'] = buy_shares - sell_shares

        except Exception as e:
            logger.debug(f"Error computing insider trends: {e}")

        return result

    def compute_analyst_growth_estimate(self, earnings_data: Optional[Dict], recommendations: Optional[List]) -> Dict[str, Optional[float]]:
        """Extract analyst growth estimates and recommendation trends."""
        result = {
            'forward_eps_growth': None,
            'analyst_buy_ratio': None
        }

        # Analyst EPS growth estimate
        if earnings_data:
            try:
                # Get most recent and next year estimates
                if isinstance(earnings_data, list) and len(earnings_data) >= 2:
                    earnings_data.sort(key=lambda x: x.get('period', ''), reverse=True)
                    current = earnings_data[0].get('actual')
                    next_est = earnings_data[1].get('estimate')

                    if current and next_est and current > 0:
                        growth = ((next_est - current) / current) * 100
                        result['forward_eps_growth'] = growth
            except Exception as e:
                logger.debug(f"Error extracting analyst estimates: {e}")

        # Analyst recommendation ratio
        if recommendations and len(recommendations) > 0:
            try:
                latest = recommendations[0]
                buy = latest.get('buy', 0)
                strong_buy = latest.get('strongBuy', 0)
                hold = latest.get('hold', 0)
                sell = latest.get('sell', 0)
                strong_sell = latest.get('strongSell', 0)

                total = buy + strong_buy + hold + sell + strong_sell
                if total > 0:
                    buy_ratio = ((buy + strong_buy) / total) * 100
                    result['analyst_buy_ratio'] = buy_ratio
            except Exception as e:
                logger.debug(f"Error extracting recommendations: {e}")

        return result

    def classify_thematic(self, profile: Optional[Dict]) -> List[str]:
        """Classify stock into thematic categories based on industry/description."""
        themes = []

        if not profile:
            return themes

        industry = profile.get('finnhubIndustry', '').lower()
        name = profile.get('name', '').lower()

        for theme, keywords in config.THEMATIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in industry or keyword in name:
                    themes.append(theme)
                    break

        return themes

    def compute_all_metrics(self, stock_data: Dict) -> Dict:
        """Compute all metrics for a stock."""
        symbol = stock_data['symbol']
        logger.info(f"Computing metrics for {symbol}")

        metrics = {'symbol': symbol}

        # Revenue CAGR
        revenue_cagr = self.compute_revenue_cagr(stock_data.get('financials'))
        metrics.update(revenue_cagr)

        # EPS CAGR
        eps_cagr = self.compute_eps_cagr(stock_data.get('basic_financials'))
        metrics.update(eps_cagr)

        # QoQ acceleration
        metrics['qoq_acceleration'] = self.compute_qoq_acceleration(stock_data.get('basic_financials'))

        # FCF margin
        metrics['fcf_margin'] = self.compute_fcf_margin(stock_data.get('financials'))

        # ROIC/ROE
        roic_roe = self.compute_roic_roe_trend(stock_data.get('basic_financials'))
        metrics.update(roic_roe)

        # Debt/EBITDA
        metrics['debt_to_ebitda'] = self.compute_debt_to_ebitda(stock_data.get('basic_financials'))

        # Insider trends
        insider = self.compute_insider_buying_trend(stock_data.get('insider_transactions'))
        metrics.update(insider)

        # Analyst estimates
        analyst = self.compute_analyst_growth_estimate(
            stock_data.get('earnings'),
            stock_data.get('recommendations')
        )
        metrics.update(analyst)

        # Thematic classification
        metrics['themes'] = self.classify_thematic(stock_data.get('profile'))

        # Market cap and price
        profile = stock_data.get('profile', {})
        metrics['market_cap'] = profile.get('marketCapitalization')

        quote = stock_data.get('quote', {})
        metrics['current_price'] = quote.get('c')

        return metrics
