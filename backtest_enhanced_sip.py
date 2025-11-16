"""
Backtest Enhanced SIP Strategy vs Regular SIP
Compares returns using rolling investment strategy
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from mutual_fund_fetcher import MutualFundFetcher
import matplotlib.pyplot as plt


class SIPBacktest:
    """Backtest Enhanced SIP vs Regular SIP strategy"""
    
    def __init__(self):
        self.fetcher = MutualFundFetcher()
    
    def get_historical_data(self, scheme_code: str, days: int = 1000) -> pd.DataFrame:
        """
        Get historical NAV data and prepare for backtesting
        
        Args:
            scheme_code: The scheme code
            days: Number of days of history
        
        Returns:
            DataFrame with processed NAV data
        """
        history = self.fetcher.get_nav_history(scheme_code, days=days)
        
        if not history:
            return pd.DataFrame()
        
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df['nav'] = pd.to_numeric(df['nav'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calculate daily returns
        df['nav_change'] = df['nav'].pct_change() * 100
        df['nav_ma_30'] = df['nav'].rolling(window=30).mean()
        
        return df
    
    def calculate_enhanced_multiplier(self, current_nav: float, 
                                     previous_nav: float,
                                     nav_change: float) -> float:
        """
        Calculate investment multiplier based on Enhanced SIP logic
        
        Args:
            current_nav: Current NAV
            previous_nav: Previous day NAV
            nav_change: Percentage change in NAV
        
        Returns:
            Multiplier for investment amount
        """
        # Invest more when NAV drops significantly
        if nav_change <= -3.0:  # Drop >= 3%
            return 2.0  # Double investment
        elif nav_change <= -2.0:  # Drop >= 2%
            return 1.5
        elif nav_change <= -1.0:  # Drop >= 1%
            return 1.25
        elif current_nav < previous_nav * 0.98:  # 2% below previous
            return 1.15
        elif current_nav > previous_nav * 1.02:  # 2% above previous
            return 0.85
        else:
            return 1.0  # Regular investment
    
    def simulate_sip(self, df: pd.DataFrame, 
                    base_amount: float = 10000,
                    investment_day: int = 1,
                    strategy: str = 'regular') -> Dict:
        """
        Simulate SIP investments over historical period
        
        Args:
            df: DataFrame with historical NAV data
            base_amount: Base monthly SIP amount
            investment_day: Day of month to invest (1-28)
            strategy: 'regular' or 'enhanced'
        
        Returns:
            Dictionary with investment results
        """
        df = df.copy()
        df['year_month'] = df['date'].dt.to_period('M')
        
        total_invested = 0
        total_units = 0
        investments = []
        
        # Group by month and get investment date
        for period, group in df.groupby('year_month'):
            # Get the first trading day of the month (or closest to investment_day)
            month_data = group.sort_values('date')
            
            if len(month_data) == 0:
                continue
            
            # Use first available date in the month
            invest_row = month_data.iloc[0]
            
            if strategy == 'enhanced':
                # Calculate multiplier based on NAV change
                if pd.notna(invest_row['nav_change']):
                    prev_nav = invest_row['nav'] / (1 + invest_row['nav_change']/100)
                    multiplier = self.calculate_enhanced_multiplier(
                        invest_row['nav'], 
                        prev_nav,
                        invest_row['nav_change']
                    )
                else:
                    multiplier = 1.0
                
                investment_amount = base_amount * multiplier
            else:
                investment_amount = base_amount
            
            # Calculate units purchased
            units = investment_amount / invest_row['nav']
            
            total_invested += investment_amount
            total_units += units
            
            investments.append({
                'date': invest_row['date'],
                'nav': invest_row['nav'],
                'nav_change': invest_row['nav_change'],
                'amount': investment_amount,
                'units': units,
                'total_units': total_units,
                'total_invested': total_invested
            })
        
        # Calculate final value
        final_nav = df.iloc[-1]['nav']
        final_value = total_units * final_nav
        absolute_return = final_value - total_invested
        return_percent = (absolute_return / total_invested) * 100 if total_invested > 0 else 0
        
        # Calculate XIRR (approximate using CAGR)
        years = (df.iloc[-1]['date'] - df.iloc[0]['date']).days / 365.25
        cagr = ((final_value / total_invested) ** (1/years) - 1) * 100 if years > 0 else 0
        
        return {
            'strategy': strategy,
            'total_invested': round(total_invested, 2),
            'total_units': round(total_units, 3),
            'final_nav': round(final_nav, 2),
            'final_value': round(final_value, 2),
            'absolute_return': round(absolute_return, 2),
            'return_percent': round(return_percent, 2),
            'cagr': round(cagr, 2),
            'num_investments': len(investments),
            'investments': investments
        }
    
    def calculate_rolling_returns(self, investments: List[Dict], 
                                  df: pd.DataFrame,
                                  window_months: int = 12) -> pd.DataFrame:
        """
        Calculate rolling returns for the investment
        
        Args:
            investments: List of investment records
            df: DataFrame with NAV data
            window_months: Rolling window in months
        
        Returns:
            DataFrame with rolling returns
        """
        inv_df = pd.DataFrame(investments)
        inv_df['date'] = pd.to_datetime(inv_df['date'])
        
        rolling_returns = []
        
        for i in range(window_months, len(inv_df)):
            window_start = i - window_months
            window_end = i
            
            invested = inv_df.iloc[window_start:window_end]['amount'].sum()
            units = inv_df.iloc[window_start:window_end]['units'].sum()
            current_nav = inv_df.iloc[window_end-1]['nav']
            current_value = units * current_nav
            
            returns = ((current_value - invested) / invested * 100) if invested > 0 else 0
            
            rolling_returns.append({
                'date': inv_df.iloc[window_end-1]['date'],
                'invested': invested,
                'value': current_value,
                'return_percent': returns
            })
        
        return pd.DataFrame(rolling_returns)
    
    def compare_strategies(self, scheme_code: str, 
                          base_amount: float = 10000,
                          days: int = 1000) -> Dict:
        """
        Compare Regular SIP vs Enhanced SIP
        
        Args:
            scheme_code: The scheme code
            base_amount: Base monthly SIP amount
            days: Historical period to backtest
        
        Returns:
            Comparison results
        """
        print(f"\n{'='*80}")
        print("BACKTESTING: Enhanced SIP vs Regular SIP")
        print(f"{'='*80}\n")
        
        # Get historical data
        df = self.get_historical_data(scheme_code, days)
        
        if df.empty:
            print("No historical data available")
            return {}
        
        print(f"Period: {df.iloc[0]['date'].strftime('%d-%m-%Y')} to {df.iloc[-1]['date'].strftime('%d-%m-%Y')}")
        print(f"Total Days: {len(df)}")
        print(f"Base SIP Amount: ₹{base_amount:,.0f}\n")
        
        # Simulate Regular SIP
        print("Simulating Regular SIP...")
        regular_results = self.simulate_sip(df, base_amount, strategy='regular')
        
        # Simulate Enhanced SIP
        print("Simulating Enhanced SIP...")
        enhanced_results = self.simulate_sip(df, base_amount, strategy='enhanced')
        
        # Calculate rolling returns
        regular_rolling = self.calculate_rolling_returns(
            regular_results['investments'], df, window_months=12
        )
        enhanced_rolling = self.calculate_rolling_returns(
            enhanced_results['investments'], df, window_months=12
        )
        
        # Print comparison
        print(f"\n{'='*80}")
        print("RESULTS COMPARISON")
        print(f"{'='*80}\n")
        
        print(f"{'Metric':<30} {'Regular SIP':>20} {'Enhanced SIP':>20}")
        print(f"{'-'*70}")
        print(f"{'Total Invested':<30} ₹{regular_results['total_invested']:>18,.0f} ₹{enhanced_results['total_invested']:>18,.0f}")
        print(f"{'Total Units':<30} {regular_results['total_units']:>20,.3f} {enhanced_results['total_units']:>20,.3f}")
        print(f"{'Final Value':<30} ₹{regular_results['final_value']:>18,.0f} ₹{enhanced_results['final_value']:>18,.0f}")
        print(f"{'Absolute Return':<30} ₹{regular_results['absolute_return']:>18,.0f} ₹{enhanced_results['absolute_return']:>18,.0f}")
        print(f"{'Return %':<30} {regular_results['return_percent']:>19,.2f}% {enhanced_results['return_percent']:>19,.2f}%")
        print(f"{'CAGR':<30} {regular_results['cagr']:>19,.2f}% {enhanced_results['cagr']:>19,.2f}%")
        
        # Calculate outperformance
        extra_return = enhanced_results['absolute_return'] - regular_results['absolute_return']
        extra_return_pct = enhanced_results['return_percent'] - regular_results['return_percent']
        
        print(f"\n{'='*80}")
        print(f"Enhanced SIP Outperformance: ₹{extra_return:,.0f} ({extra_return_pct:+.2f}%)")
        print(f"{'='*80}\n")
        
        # Average rolling returns
        if not regular_rolling.empty and not enhanced_rolling.empty:
            print(f"Average 12-Month Rolling Returns:")
            print(f"  Regular SIP: {regular_rolling['return_percent'].mean():.2f}%")
            print(f"  Enhanced SIP: {enhanced_rolling['return_percent'].mean():.2f}%")
        
        return {
            'regular': regular_results,
            'enhanced': enhanced_results,
            'regular_rolling': regular_rolling,
            'enhanced_rolling': enhanced_rolling,
            'outperformance': extra_return,
            'outperformance_pct': extra_return_pct
        }
    
    def backtest_fund(self, fund_name: str, 
                     base_amount: float = 10000,
                     days: int = 1000) -> Dict:
        """
        Search for a fund and backtest Enhanced SIP strategy
        
        Args:
            fund_name: Fund name or keyword
            base_amount: Base monthly SIP amount
            days: Historical period
        
        Returns:
            Backtest results
        """
        # Search for the fund
        schemes = self.fetcher.search_schemes(fund_name)
        
        if not schemes:
            print(f"No schemes found for '{fund_name}'")
            return {}
        
        scheme = schemes[0]
        scheme_code = scheme['schemeCode']
        scheme_name = scheme['schemeName']
        
        print(f"\nBacktesting: {scheme_name}")
        print(f"Scheme Code: {scheme_code}")
        
        return self.compare_strategies(scheme_code, base_amount, days)


# Example usage
if __name__ == "__main__":
    backtest = SIPBacktest()
    
    # Get fund name from user
    fund_name = input("Enter fund name to backtest (e.g., 'Parag Parikh', 'DSP Small Cap'): ").strip()
    
    if not fund_name:
        fund_name = "Parag Parikh Flexi Cap"
        print(f"Using default: {fund_name}")
    
    base_amount = input("\nEnter monthly SIP amount (default 10000): ").strip()
    base_amount = float(base_amount) if base_amount else 10000
    
    # Run backtest
    results = backtest.backtest_fund(fund_name, base_amount=base_amount, days=1000)
    
    print("\n" + "="*80)
    print("✅ Backtest Complete!")
    print("\nKey Insights:")
    print("1. Enhanced SIP invests more during market dips")
    print("2. This strategy can generate higher returns over time")
    print("3. Requires flexible cash flow to handle variable investments")
    print("4. Best suited for long-term investors (3+ years)")