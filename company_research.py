#!/usr/bin/env python3
"""
Company research automation - fetch company information, recent news, tech stack, etc.
"""
import requests
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

class CompanyResearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_company_info(self, company_name: str) -> Dict:
        """Get comprehensive company information"""
        info = {
            'name': company_name,
            'description': '',
            'website': '',
            'headquarters': '',
            'founded': '',
            'employees': '',
            'industry': '',
            'recent_news': [],
            'tech_stack': [],
            'funding': '',
            'glassdoor_rating': '',
            'engineering_culture': ''
        }
        
        try:
            # Try to get basic info from Wikipedia
            wiki_info = self._get_wikipedia_info(company_name)
            if wiki_info:
                info.update(wiki_info)
            
            # Get recent news (placeholder - would need news API)
            info['recent_news'] = self._get_recent_news(company_name)
            
            # Get tech stack (placeholder - would need StackShare/GitHub analysis)
            info['tech_stack'] = self._get_tech_stack(company_name)
            
            logger.info(f"Researched company: {company_name}")
            
        except Exception as e:
            logger.error(f"Error researching {company_name}: {e}")
        
        return info
    
    def _get_wikipedia_info(self, company_name: str) -> Dict:
        """Get company information from Wikipedia"""
        try:
            # Search for company page
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{company_name.replace(' ', '_')}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'description': data.get('extract', ''),
                    'website': data.get('content_urls', {}).get('desktop', {}).get('page', '')
                }
            
        except Exception as e:
            logger.debug(f"Wikipedia lookup failed for {company_name}: {e}")
        
        return {}
    
    def _get_recent_news(self, company_name: str) -> List[str]:
        """Get recent news about the company"""
        # Placeholder - would integrate with News API or Google News
        news_items = []
        
        try:
            # Example using Google News RSS (would need proper implementation)
            search_url = f"https://news.google.com/rss/search?q={company_name}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                # Parse RSS feed (simplified)
                items = re.findall(r'<title>(.*?)</title>', response.text)
                news_items = items[:5]  # Get first 5 news items
            
        except Exception as e:
            logger.debug(f"News lookup failed for {company_name}: {e}")
        
        return news_items
    
    def _get_tech_stack(self, company_name: str) -> List[str]:
        """Get company's technology stack"""
        # Placeholder - would integrate with StackShare API or analyze GitHub repos
        common_tech_stacks = {
            'google': ['Python', 'Java', 'C++', 'Go', 'Kubernetes', 'TensorFlow'],
            'microsoft': ['C#', '.NET', 'TypeScript', 'Azure', 'React'],
            'amazon': ['Java', 'Python', 'AWS', 'Linux', 'Docker'],
            'meta': ['Python', 'C++', 'React', 'PHP', 'Hack'],
            'apple': ['Swift', 'Objective-C', 'C++', 'Metal'],
            'netflix': ['Java', 'Python', 'JavaScript', 'AWS', 'Kubernetes'],
            'spotify': ['Python', 'Java', 'JavaScript', 'Go', 'Google Cloud'],
        }
        
        company_lower = company_name.lower()
        for key, tech_stack in common_tech_stacks.items():
            if key in company_lower:
                return tech_stack
        
        return []
    
    def get_interview_preparation(self, company_name: str, role: str) -> Dict:
        """Get interview preparation tips for specific company and role"""
        preparation = {
            'company': company_name,
            'role': role,
            'technical_topics': [],
            'behavioral_questions': [],
            'practice_problems': [],
            'company_specific_tips': []
        }
        
        # Company-specific interview patterns (simplified database)
        company_patterns = {
            'google': {
                'technical_topics': ['Data Structures', 'Algorithms', 'System Design', 'Coding'],
                'behavioral_questions': ['Tell me about a time you solved a complex problem', 'How do you handle ambiguity?'],
                'practice_problems': ['LeetCode Medium/Hard', 'Dynamic Programming', 'Graph Algorithms'],
                'company_specific_tips': ['Focus on clean code', 'Think out loud', 'Ask clarifying questions']
            },
            'amazon': {
                'technical_topics': ['Data Structures', 'Algorithms', 'System Design', 'OOP'],
                'behavioral_questions': ['Tell me about a time you failed', 'How do you handle tight deadlines?'],
                'practice_problems': ['LeetCode Medium', 'Object-Oriented Design', 'Scalability'],
                'company_specific_tips': ['Leadership principles', 'Customer obsession', 'Bias for action']
            },
            'microsoft': {
                'technical_topics': ['Data Structures', 'Algorithms', 'System Design', 'Coding'],
                'behavioral_questions': ['Tell me about a challenging project', 'How do you work in teams?'],
                'practice_problems': ['LeetCode Medium', 'Object-Oriented Design', 'API Design'],
                'company_specific_tips': ['Growth mindset', 'Collaboration', 'Inclusivity']
            }
        }
        
        company_lower = company_name.lower()
        for key, patterns in company_patterns.items():
            if key in company_lower:
                preparation.update(patterns)
                break
        
        # Role-specific additions
        if 'intern' in role.lower():
            preparation['technical_topics'].extend(['Basic CS concepts', 'Problem-solving'])
        
        return preparation
    
    def get_competitor_companies(self, company_name: str) -> List[str]:
        """Get list of competitor companies"""
        competitors = {
            'google': ['Microsoft', 'Amazon', 'Meta', 'Apple'],
            'microsoft': ['Google', 'Amazon', 'Apple', 'IBM'],
            'amazon': ['Google', 'Microsoft', 'Meta', 'Apple'],
            'meta': ['Google', 'Twitter/X', 'Snap', 'Pinterest'],
            'apple': ['Google', 'Microsoft', 'Samsung', 'Huawei'],
            'netflix': ['Amazon Prime', 'Disney+', 'HBO Max', 'Hulu'],
            'uber': ['Lyft', 'DoorDash', 'Grab', 'Didi'],
            'lyft': ['Uber', 'DoorDash', 'Grab'],
        }
        
        company_lower = company_name.lower()
        for key, comps in competitors.items():
            if key in company_lower:
                return comps
        
        return []
    
    def research_multiple_companies(self, company_names: List[str]) -> Dict[str, Dict]:
        """Research multiple companies"""
        results = {}
        
        for company in company_names:
            results[company] = self.get_company_info(company)
        
        return results

def main():
    """Example usage"""
    researcher = CompanyResearcher()
    
    # Research a single company
    google_info = researcher.get_company_info("Google")
    print(f"Google Info: {google_info}")
    
    # Get interview preparation
    google_prep = researcher.get_interview_preparation("Google", "Software Engineer Intern")
    print(f"Google Interview Prep: {google_prep}")
    
    # Research multiple companies
    companies = ["Google", "Microsoft", "Amazon"]
    multi_research = researcher.research_multiple_companies(companies)
    print(f"Multi-company research: {multi_research}")

if __name__ == "__main__":
    main()