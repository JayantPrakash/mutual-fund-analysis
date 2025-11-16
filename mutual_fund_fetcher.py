"""
Mutual Fund Data Fetcher for Indian Mutual Funds
Uses the MFAPI (https://www.mfapi.in/) to fetch mutual fund data
"""

import requests
from typing import Dict, List, Optional
from datetime import datetime


class MutualFundFetcher:
    """Fetch mutual fund data from Indian markets"""
    
    BASE_URL = "https://api.mfapi.in/mf"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_all_schemes(self) -> List[Dict]:
        """
        Get list of all available mutual fund schemes
        
        Returns:
            List of dictionaries containing scheme code and name
        """
        try:
            response = self.session.get(self.BASE_URL)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching schemes: {e}")
            return []
    
    def get_scheme_details(self, scheme_code: str) -> Optional[Dict]:
        """
        Get detailed information about a specific mutual fund scheme
        
        Args:
            scheme_code: The scheme code (e.g., '119551' for SBI Bluechip Fund)
        
        Returns:
            Dictionary containing scheme details and NAV history
        """
        try:
            url = f"{self.BASE_URL}/{scheme_code}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching scheme {scheme_code}: {e}")
            return None
    
    def get_latest_nav(self, scheme_code: str) -> Optional[Dict]:
        """
        Get the latest NAV (Net Asset Value) for a scheme
        
        Args:
            scheme_code: The scheme code
        
        Returns:
            Dictionary with latest NAV data
        """
        data = self.get_scheme_details(scheme_code)
        if data and 'data' in data and len(data['data']) > 0:
            latest = data['data'][0]
            return {
                'scheme_code': scheme_code,
                'scheme_name': data['meta']['scheme_name'],
                'nav': latest['nav'],
                'date': latest['date']
            }
        return None
    
    def search_schemes(self, keyword: str) -> List[Dict]:
        """
        Search for mutual fund schemes by keyword
        
        Args:
            keyword: Search term (e.g., 'SBI', 'HDFC', 'Equity')
        
        Returns:
            List of matching schemes
        """
        all_schemes = self.get_all_schemes()
        keyword_lower = keyword.lower()
        return [
            scheme for scheme in all_schemes 
            if keyword_lower in scheme['schemeName'].lower()
        ]
    
    def get_nav_history(self, scheme_code: str, days: Optional[int] = None) -> List[Dict]:
        """
        Get NAV history for a scheme
        
        Args:
            scheme_code: The scheme code
            days: Number of recent days to fetch (None for all history)
        
        Returns:
            List of NAV records
        """
        data = self.get_scheme_details(scheme_code)
        if data and 'data' in data:
            history = data['data']
            if days:
                return history[:days]
            return history
        return []


# Example usage
if __name__ == "__main__":
    fetcher = MutualFundFetcher()
    
    # Search for SBI mutual funds
    print("Searching for SBI mutual funds...")
    sbi_funds = fetcher.search_schemes("SBI")
    print(f"Found {len(sbi_funds)} SBI schemes\n")
    
    # Display first 5 schemes
    for scheme in sbi_funds[:5]:
        print(f"Code: {scheme['schemeCode']}, Name: {scheme['schemeName']}")
    
    # Get details for a specific scheme (SBI Bluechip Fund)
    print("\n" + "="*80)
    print("Fetching SBI Bluechip Fund details...")
    scheme_code = "119551"
    
    latest_nav = fetcher.get_latest_nav(scheme_code)
    if latest_nav:
        print(f"\nScheme: {latest_nav['scheme_name']}")
        print(f"Latest NAV: ₹{latest_nav['nav']}")
        print(f"Date: {latest_nav['date']}")
    
    # Get last 10 days NAV history
    print("\nLast 31 days NAV history:")
    history = fetcher.get_nav_history(scheme_code, days=31)
    for record in history:
        print(f"Date: {record['date']}, NAV: ₹{record['nav']}")
