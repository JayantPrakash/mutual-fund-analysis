"""
Enhanced SIP Strategy - Identifies best investment dates based on NAV drops
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from mutual_fund_fetcher import MutualFundFetcher


class EnhancedSIP:
    """Enhanced SIP strategy that identifies optimal investment dates"""
    
    def __init__(self):
        self.fetcher = MutualFundFetcher()
    
    def analyze_nav_trends(self, scheme_code: str, days: int = 600) -> pd.DataFrame:
        """
        Analyze NAV trends for a mutual fund scheme
        
        Args:
            scheme_code: The scheme code
            days: Number of days to analyze
        
        Returns:
            DataFrame with NAV analysis
        """
        history = self.fetcher.get_nav_history(scheme_code, days=days)
        
        if not history:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df['nav'] = pd.to_numeric(df['nav'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calculate metrics
        df['nav_change'] = df['nav'].pct_change() * 100  # Percentage change
        df['nav_ma_7'] = df['nav'].rolling(window=7).mean()  # 7-day moving average
        df['nav_ma_30'] = df['nav'].rolling(window=30).mean()  # 30-day moving average
        df['volatility'] = df['nav'].rolling(window=7).std()  # 7-day volatility
        
        # Identify significant drops
        df['is_significant_drop'] = df['nav_change'] < -1.0  # Drop > 1%
        df['is_below_ma'] = df['nav'] < df['nav_ma_30']  # Below 30-day average
        
        return df
    
    def find_best_investment_dates(self, scheme_code: str, 
                                   drop_threshold: float = -2,
                                   days: int = 600) -> List[Dict]:
        """
        Find the best dates to invest based on NAV drops
        
        Args:
            scheme_code: The scheme code
            drop_threshold: Minimum percentage drop to consider (negative value)
            days: Number of days to analyze
        
        Returns:
            List of recommended investment dates with details
        """
        df = self.analyze_nav_trends(scheme_code, days)
        
        if df.empty:
            return []
        
        # Filter significant drops
        opportunities = df[df['nav_change'] <= drop_threshold].copy()
        
        # Calculate opportunity score based only on NAV change (higher is better)
        opportunities['opportunity_score'] = abs(opportunities['nav_change'])
        
        # Sort by opportunity score
        opportunities = opportunities.sort_values('opportunity_score', ascending=False)
        
        # Prepare results
        results = []
        #for _, row in opportunities.head(10).iterrows():
        for _, row in opportunities.iterrows():
            results.append({
                'date': row['date'].strftime('%d-%m-%Y'),
                'nav': round(row['nav'], 2),
                'nav_change_percent': round(row['nav_change'], 2),
                'nav_30day_avg': round(row['nav_ma_30'], 2) if pd.notna(row['nav_ma_30']) else None,
                'opportunity_score': round(row['opportunity_score'], 2),
                'recommendation': self._get_recommendation(row['opportunity_score'])
            })
        
        return results
    
    def _get_recommendation(self, score: float) -> str:
        """Get investment recommendation based on opportunity score"""
        if score >= 3.0:
            return "Excellent - Invest 150-200% of regular SIP"
        elif score >= 2.0:
            return "Very Good - Invest 125-150% of regular SIP"
        elif score >= 1.5:
            return "Good - Invest 110-125% of regular SIP"
        else:
            return "Moderate - Invest regular SIP amount"
    
    def get_monthly_investment_strategy(self, scheme_code: str, 
                                       base_amount: float = 10000) -> Dict:
        """
        Get monthly investment strategy with recommended amounts
        
        Args:
            scheme_code: The scheme code
            base_amount: Base SIP amount in rupees
        
        Returns:
            Dictionary with current month strategy
        """
        df = self.analyze_nav_trends(scheme_code, days=30)
        
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        avg_nav = df['nav'].mean()
        current_nav = latest['nav']
        previous_nav = previous['nav']
        recent_drop = latest['nav_change']
        
        # Calculate multiplier
        if current_nav < previous_nav * 0.95:  # 5% below average
            multiplier = 1.5
        elif current_nav < previous_nav * 0.98:  # 2% below average
            multiplier = 1.25
        elif current_nav > previous_nav * 1.02:  # 2% above average
            multiplier = 0.85
        else:
            multiplier = 1.0
        
        recommended_amount = base_amount * multiplier
        
        return {
            'scheme_code': scheme_code,
            'current_nav': round(current_nav, 2),
            'previous_nav': round(previous_nav, 2),
            'average_nav_30d': round(avg_nav, 2),
            'recent_change_percent': round(recent_drop, 2),
            'base_sip_amount': base_amount,
            'recommended_amount': round(recommended_amount, 2),
            'multiplier': round(multiplier, 2),
            'units_to_buy': round(recommended_amount / current_nav, 3),
            'strategy': self._get_strategy_message(multiplier)
        }
    
    def _get_strategy_message(self, multiplier: float) -> str:
        """Get strategy message based on multiplier"""
        if multiplier >= 1.5:
            return "Market is down significantly - Great buying opportunity!"
        elif multiplier >= 1.25:
            return "Market correction - Good time to invest more"
        elif multiplier <= 0.85:
            return "Market is high - Reduce investment amount"
        else:
            return "Market is stable - Continue regular SIP"
    
    def search_and_analyze(self, fund_name: str, 
                          drop_threshold: float = -2) -> Optional[Dict]:
        """
        Search for a fund and provide enhanced SIP analysis
        
        Args:
            fund_name: Name or keyword to search for
            drop_threshold: Minimum percentage drop to consider
        
        Returns:
            Complete analysis with recommendations
        """
        # Search for the fund
        schemes = self.fetcher.search_schemes(fund_name)
        
        if not schemes:
            print(f"No schemes found for '{fund_name}'")
            return None
        
        # Use the first matching scheme
        scheme = schemes[0]
        scheme_code = scheme['schemeCode']
        scheme_name = scheme['schemeName']
        
        print(f"\nAnalyzing: {scheme_name}")
        print(f"Scheme Code: {scheme_code}")
        print("=" * 80)
        
        # Get current NAV
        latest_nav = self.fetcher.get_latest_nav(scheme_code)
        if latest_nav:
            print(f"\nCurrent NAV: ₹{latest_nav['nav']} (as of {latest_nav['date']})")
        
        # Get best investment dates
        print(f"\n📊 Best Investment Opportunities (NAV drops > {abs(drop_threshold)}%):")
        print("-" * 80)
        best_dates = self.find_best_investment_dates(scheme_code, drop_threshold=-2)
        
        if best_dates:
            for i, opportunity in enumerate(best_dates, 1):
                print(f"\n{i}. Date: {opportunity['date']}")
                print(f"   NAV: ₹{opportunity['nav']}")
                print(f"   Drop: {opportunity['nav_change_percent']}%")
                print(f"   30-Day Avg: ₹{opportunity['nav_30day_avg']}")
                print(f"   Score: {opportunity['opportunity_score']}")
                print(f"   💡 {opportunity['recommendation']}")
        else:
            print("No significant drops found in the analyzed period.")
        
        # Get monthly strategy
        print("\n" + "=" * 80)
        print("📈 Current Month Investment Strategy:")
        print("-" * 80)
        strategy = self.get_monthly_investment_strategy(scheme_code)

        if strategy:
            print(f"\nScheme Code: {strategy['scheme_code']}")
            print(f"\nCurrent Nav: ₹{strategy['current_nav']}")
            print(f"\nPrevious Nav: ₹{strategy['previous_nav']}")
            print(f"\nRecent change percent: {strategy['recent_change_percent']}")
            print(f"\nBase SIP Amount: ₹{strategy['base_sip_amount']:,.0f}")
            print(f"\nBase SIP Amount: ₹{strategy['base_sip_amount']:,.0f}")
            print(f"Recommended Amount: ₹{strategy['recommended_amount']:,.0f}")
            print(f"Multiplier: {strategy['multiplier']}x")
            print(f"Units to Buy: {strategy['units_to_buy']}")
            print(f"\n💡 Strategy: {strategy['strategy']}")
        
        return {
            'scheme_name': scheme_name,
            'scheme_code': scheme_code,
            'best_dates': best_dates,
            'monthly_strategy': strategy
        }


# Example usage
if __name__ == "__main__":
    enhanced_sip = EnhancedSIP()
    
    # Analyze a fund

    fund_name = input("Enter fund name to analyze (e.g., 'SBI Bluechip', 'HDFC Equity'): ").strip()
    
    if not fund_name:
        fund_name = "SBI Bluechip"
        print(f"Using default: {fund_name}")
    
    # Analyze with 1% drop threshold
    result = enhanced_sip.search_and_analyze(fund_name, drop_threshold=-0.2)
    
    print("\n" + "=" * 80)
    print("✅ Analysis Complete!")
    print("\nKey Takeaways:")
    print("1. Invest more when NAV drops significantly")
    print("2. Use the opportunity score to prioritize investment dates")
    print("3. Follow the monthly strategy for optimal returns")
    print("4. Stay disciplined and invest regularly")