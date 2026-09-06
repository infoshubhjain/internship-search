#!/usr/bin/env python3
"""
Comprehensive sponsorship database for F-1 visa status
"""
SPONSORSHIP_DB = {
    # Big Tech - Known Sponsors
    'google': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship, very F-1 friendly', 'tier': 1},
    'alphabet': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'microsoft': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship, very F-1 friendly', 'tier': 1},
    'amazon': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship, large F-1 intern program', 'tier': 1},
    'meta': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'facebook': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (Meta)', 'tier': 1},
    'apple': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'netflix': {'cpt': True, 'opt': True, 'h1b': False, 'notes': 'CPT/OPT only, no H-1B', 'tier': 1},
    'stripe': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'airbnb': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'linkedin': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'salesforce': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'adobe': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'workday': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'servicenow': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'sap': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'oracle': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'ibm': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'intel': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'cisco': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'dell': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'hp': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'vmware': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'nvidia': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'amd': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'qualcomm': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'broadcom': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'texas instruments': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    
    # Banks & Fintech - Known Sponsors
    'jpmorgan': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship, very F-1 friendly', 'tier': 1},
    'jpmorgan chase': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'goldman sachs': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship, very F-1 friendly', 'tier': 1},
    'morgan stanley': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'bank of america': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'citi': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'citigroup': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'wells fargo': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'visa': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship, known CPT sponsor', 'tier': 1},
    'mastercard': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship, known CPT sponsor', 'tier': 1},
    'american express': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'amex': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (Amex)', 'tier': 1},
    'paypal': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'intuit': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'charles schwab': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'schwab': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'blackrock': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'fidelity': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'bloomberg': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'barclays': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'credit suisse': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'deutsche bank': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'capital one': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship, very F-1 friendly', 'tier': 1},
    
    # F500 Companies - Good Sponsors
    'walmart': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'target': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'general motors': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'gm': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'ford': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'john deere': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'caterpillar': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'state farm': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'unitedhealth': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'optum': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'cvs health': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'cvs': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'verizon': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    't-mobile': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'comcast': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'honeywell': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'siemens': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'ge': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'general electric': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'boeing': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 2},
    'lockheed': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (defense contractor)', 'tier': 2},
    'lockheed martin': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (defense contractor)', 'tier': 2},
    'northrop grumman': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (defense contractor)', 'tier': 2},
    'raytheon': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (defense contractor)', 'tier': 2},
    
    # Startups & Unicorns - Variable Sponsorship
    'notion': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'figma': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'slack': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (Salesforce)', 'tier': 1},
    'discord': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'roblox': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'snap': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'datadog': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'atlassian': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'dropbox': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'reddit': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'twitch': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (Amazon)', 'tier': 1},
    'block': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'square': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship (Block)', 'tier': 3},
    'plaid': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'chime': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'brex': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'duolingo': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'ramp': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'replit': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'scale ai': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'anthropic': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'openai': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'stability ai': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    
    # Other Tech Companies
    'uber': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'lyft': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'pinterest': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'twitter': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'x': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (Twitter/X)', 'tier': 1},
    'spotify': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'doordash': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'instacart': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'airtable': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'asana': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'monday.com': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'zoom': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'box': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'adobe': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'autodesk': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'symantec': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'mcafee': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Likely sponsorship', 'tier': 3},
    'palantir': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship (defense contractor)', 'tier': 2},
    
    # Consulting & Professional Services
    'deloitte': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'accenture': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'pwc': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'ey': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'kpmg': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'mckinsey': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'bcg': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    'bain': {'cpt': True, 'opt': True, 'h1b': True, 'notes': 'Full sponsorship', 'tier': 1},
    
    # Known Non-Sponsors (avoid or verify)
    'vertiv': {'cpt': False, 'opt': False, 'h1b': False, 'notes': 'No sponsorship per listing', 'tier': 4},
    'epic games': {'cpt': False, 'opt': False, 'h1b': False, 'notes': 'No sponsorship per listing', 'tier': 4},
    'humana': {'cpt': False, 'opt': False, 'h1b': False, 'notes': 'No sponsorship per listing', 'tier': 4},
}

def get_sponsorship_info(company_name):
    """Get sponsorship information for a company"""
    company_lower = company_name.lower().strip()
    
    # Direct match
    if company_lower in SPONSORSHIP_DB:
        return SPONSORSHIP_DB[company_lower]
    
    # Partial match (handle company name variations)
    for key, value in SPONSORSHIP_DB.items():
        if key in company_lower or company_lower in key:
            return value
    
    # Default unknown
    return {
        'cpt': None,
        'opt': None, 
        'h1b': None,
        'notes': 'Unknown - verify with company',
        'tier': 5
    }

def get_sponsorship_tier(company_name):
    """Get sponsorship tier (1=best, 5=unknown)"""
    info = get_sponsorship_info(company_name)
    return info['tier']

def is_f1_friendly(company_name):
    """Check if company is likely F-1 friendly"""
    info = get_sponsorship_info(company_name)
    return info['cpt'] is True and info['tier'] <= 2