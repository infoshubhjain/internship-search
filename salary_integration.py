#!/usr/bin/env python3
"""
Salary data integration for compensation analysis and negotiation
"""
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SalaryIntegration:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.salary_data = {}
        self._load_default_salary_data()
    
    def _load_default_salary_data(self):
        """Load default salary data for known companies"""
        # Placeholder data - in real implementation, would scrape from Levels.fyi, Glassdoor, etc.
        self.salary_data = {
            'google': {
                'intern_monthly': 8500,
                'intern_total': 34000,
                'new_grad_base': 150000,
                'new_grad_total': 200000,
                'currency': 'USD',
                'location': 'Mountain View, CA'
            },
            'microsoft': {
                'intern_monthly': 7800,
                'intern_total': 31200,
                'new_grad_base': 140000,
                'new_grad_total': 180000,
                'currency': 'USD',
                'location': 'Redmond, WA'
            },
            'amazon': {
                'intern_monthly': 8200,
                'intern_total': 32800,
                'new_grad_base': 135000,
                'new_grad_total': 175000,
                'currency': 'USD',
                'location': 'Seattle, WA'
            },
            'meta': {
                'intern_monthly': 9000,
                'intern_total': 36000,
                'new_grad_base': 160000,
                'new_grad_total': 220000,
                'currency': 'USD',
                'location': 'Menlo Park, CA'
            },
            'apple': {
                'intern_monthly': 7500,
                'intern_total': 30000,
                'new_grad_base': 145000,
                'new_grad_total': 190000,
                'currency': 'USD',
                'location': 'Cupertino, CA'
            },
            'netflix': {
                'intern_monthly': 10000,
                'intern_total': 40000,
                'new_grad_base': 180000,
                'new_grad_total': 250000,
                'currency': 'USD',
                'location': 'Los Gatos, CA'
            }
        }
    
    def get_salary_for_company(self, company_name: str) -> Optional[Dict]:
        """Get salary data for a specific company"""
        company_lower = company_name.lower()
        
        for key, data in self.salary_data.items():
            if key in company_lower:
                return data
        
        return None
    
    def get_salary_range(self, role: str, location: str = None) -> Dict:
        """Get salary range for a role and location"""
        # Placeholder implementation
        # In real implementation, would aggregate data from multiple sources
        
        if 'intern' in role.lower():
            return {
                'min_monthly': 6000,
                'max_monthly': 12000,
                'average_monthly': 8000,
                'min_total': 24000,
                'max_total': 48000,
                'average_total': 32000,
                'currency': 'USD',
                'data_points': 0
            }
        elif 'new grad' in role.lower() or 'entry level' in role.lower():
            return {
                'min_base': 100000,
                'max_base': 200000,
                'average_base': 140000,
                'min_total': 130000,
                'max_total': 280000,
                'average_total': 180000,
                'currency': 'USD',
                'data_points': 0
            }
        
        return {}
    
    def compare_offers(self, offers: List[Dict]) -> Dict:
        """Compare multiple job offers"""
        comparison = {
            'offers': offers,
            'best_monthly': None,
            'best_total': None,
            'analysis': []
        }
        
        if not offers:
            return comparison
        
        # Find best by monthly rate
        best_monthly = max(offers, key=lambda x: x.get('monthly_rate', 0))
        comparison['best_monthly'] = best_monthly
        
        # Find best by total compensation
        best_total = max(offers, key=lambda x: x.get('total_compensation', 0))
        comparison['best_total'] = best_total
        
        # Generate analysis
        for i, offer in enumerate(offers):
            analysis = {
                'company': offer.get('company', 'Unknown'),
                'monthly_rate': offer.get('monthly_rate', 0),
                'total_compensation': offer.get('total_compensation', 0),
                'vs_best_monthly': offer.get('monthly_rate', 0) - best_monthly.get('monthly_rate', 0),
                'vs_best_total': offer.get('total_compensation', 0) - best_total.get('total_compensation', 0)
            }
            comparison['analysis'].append(analysis)
        
        return comparison
    
    def calculate_cost_of_living_adjustment(self, base_salary: int, 
                                          from_location: str, to_location: str) -> int:
        """Calculate salary adjustment for cost of living differences"""
        # Placeholder implementation
        # In real implementation, would use cost of living index data
        
        cost_of_living_index = {
            'san francisco': 1.5,
            'new york': 1.4,
            'seattle': 1.2,
            'austin': 0.9,
            'chicago': 1.0,
            'boston': 1.3
        }
        
        from_idx = cost_of_living_index.get(from_location.lower(), 1.0)
        to_idx = cost_of_living_index.get(to_location.lower(), 1.0)
        
        adjustment_factor = to_idx / from_idx
        adjusted_salary = int(base_salary * adjustment_factor)
        
        return adjusted_salary
    
    def get_negotiation_tips(self, company_name: str, offer: Dict) -> List[str]:
        """Get negotiation tips for a specific company"""
        tips = []
        
        company_lower = company_name.lower()
        
        # Company-specific negotiation strategies
        if 'google' in company_lower:
            tips = [
                "Google typically has room for negotiation, especially for strong candidates",
                "Focus on total compensation (base + bonus + stock), not just base salary",
                "Research Google's leveling system to understand your offer level",
                "Consider the value of RSUs and sign-on bonus in your evaluation"
            ]
        elif 'amazon' in company_lower:
            tips = [
                "Amazon's base salary is less negotiable, but signing bonus and RSUs are",
                "Amazon uses a unique stock vesting schedule (5%, 15%, 40%, 40%)",
                "Consider the geographic location's impact on total compensation",
                "Amazon's compensation structure is back-loaded, understand the implications"
            ]
        elif 'meta' in company_lower:
            tips = [
                "Meta is known for competitive compensation, especially for top talent",
                "Meta's stock grants can be significant in total compensation",
                "Consider the long-term value of RSUs in your negotiation",
                "Meta may offer higher base salary but lower bonus structure"
            ]
        else:
            tips = [
                "Research the company's typical compensation structure",
                "Understand the geographic cost of living adjustments",
                "Consider the entire compensation package, not just base salary",
                "Be prepared to discuss your value and unique qualifications"
            ]
        
        return tips

def main():
    """Example usage"""
    salary = SalaryIntegration()
    
    # Get salary for a company
    google_salary = salary.get_salary_for_company("Google")
    print(f"Google salary data: {google_salary}")
    
    # Get salary range
    intern_range = salary.get_salary_range("Software Engineer Intern")
    print(f"Intern salary range: {intern_range}")
    
    # Compare offers
    offers = [
        {'company': 'Google', 'monthly_rate': 8500, 'total_compensation': 34000},
        {'company': 'Microsoft', 'monthly_rate': 7800, 'total_compensation': 31200},
        {'company': 'Amazon', 'monthly_rate': 8200, 'total_compensation': 32800}
    ]
    
    comparison = salary.compare_offers(offers)
    print(f"Offer comparison: {comparison}")
    
    # Get negotiation tips
    tips = salary.get_negotiation_tips("Google", {})
    print(f"Negotiation tips: {tips}")

if __name__ == "__main__":
    main()