#!/usr/bin/env python3
"""
Comprehensive sponsorship database for F-1 visa status
"""
import re

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

# Employers whose work is ITAR/EAR-controlled or requires a security clearance.
# These generally require US citizenship or permanent residency regardless of
# what their general sponsorship policy says, so for an F-1 student they are a
# hard barrier rather than a sponsorship question. Kept visible (not deleted)
# so the listings can still be seen and judged.
CITIZENSHIP_REQUIRED = {
    'rtx', 'raytheon', 'lockheed', 'lockheed martin', 'northrop grumman',
    'northrop', 'general dynamics', 'l3harris', 'l3 harris', 'boeing',
    'spacex', 'anduril', 'palantir', 'blue origin', 'sierra nevada',
    'aerojet', 'bae systems', 'leidos', 'booz allen', 'mitre', 'draper',
    'johns hopkins apl', 'sandia', 'los alamos', 'lawrence livermore',
    'ball aerospace', 'peraton', 'caci', 'saic', 'mantech',
}

CITIZENSHIP_INFO = {
    'cpt': False, 'opt': False, 'h1b': False,
    'notes': 'US citizenship / clearance typically required (ITAR or cleared work)',
    'tier': 6,
}

UNKNOWN_INFO = {
    'cpt': None, 'opt': None, 'h1b': None,
    'notes': 'Unknown - verify with company',
    'tier': 5,
}

# Keys shorter than this only match as whole words. Substring matching on a
# key like 'x' (Twitter/X) silently claimed RTX, SpaceX, Cox and Apex as fully
# sponsoring; 'ge' claimed General Dynamics. Short keys are the dangerous ones.
_MIN_SUBSTRING_KEY = 4


def _normalize(name):
    """Lowercase and strip corporate suffixes and punctuation for matching."""
    name = (name or '').lower().strip()
    name = re.sub(r'[(),.]', ' ', name)
    name = re.sub(r'\b(inc|llc|ltd|corp|corporation|co|plc|group|holdings|ab|sa|nv|gmbh)\b',
                  ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def _word_match(key, name):
    """True if key appears in name on word boundaries."""
    return re.search(r'\b' + re.escape(key) + r'\b', name) is not None


def requires_citizenship(company_name):
    """True if the employer generally requires US citizenship or a clearance."""
    name = _normalize(company_name)
    return any(_word_match(key, name) for key in CITIZENSHIP_REQUIRED)


def get_sponsorship_info(company_name):
    """Look up sponsorship info for a company.

    Sources in priority order, strongest evidence first:

      1. Citizenship / clearance requirement. A hard barrier for an F-1
         student, and it outranks filing volume - Booz Allen files plenty of
         H-1Bs but still needs a clearance for most roles.
      2. A hand-recorded NON-sponsor. These come from listings that said so
         outright, which is knowledge the H-1B data cannot express.
      3. USCIS H-1B filings. Counts of people the employer actually
         sponsored, which beats any hand-written policy guess.
      4. The hand-curated table, for companies with no H-1B record.
      5. Unknown.
    """
    name = _normalize(company_name)
    if not name:
        return dict(UNKNOWN_INFO)

    if any(_word_match(key, name) for key in CITIZENSHIP_REQUIRED):
        return dict(CITIZENSHIP_INFO)

    curated = _curated_lookup(name)
    if curated and curated.get('cpt') is False:
        return curated

    h1b = _h1b_lookup(company_name)
    if h1b:
        return h1b

    if curated:
        return curated

    return dict(UNKNOWN_INFO)


def _h1b_lookup(company_name):
    """Sponsorship info derived from USCIS filing counts, or None."""
    try:
        import h1b_data
    except ImportError:
        return None

    tier, record = h1b_data.sponsorship_tier(company_name)
    if not record:
        return None

    approvals, denials = record['approvals'], record['denials']
    if approvals:
        notes = (f"{approvals} H-1B approvals in FY{record['fiscal_year']} "
                 f"({denials} denied) - sponsors in practice")
    else:
        notes = (f"Filed H-1B petitions in FY{record['fiscal_year']} but none "
                 f"approved ({denials} denied)")

    return {
        # H-1B volume says the employer handles work visas as a matter of
        # routine. CPT/OPT for an intern is a lower bar, so it is inferred,
        # but marked as inference rather than a stated policy.
        'cpt': approvals > 0,
        'opt': approvals > 0,
        'h1b': approvals > 0,
        'notes': notes,
        'tier': tier,
        'source': 'uscis_h1b',
        'approvals': approvals,
    }


def _curated_lookup(name):
    """The hand-maintained table, matched on word boundaries, longest first."""
    if name in SPONSORSHIP_DB:
        return dict(SPONSORSHIP_DB[name], source='curated')

    for key in sorted(SPONSORSHIP_DB, key=len, reverse=True):
        if len(key) < _MIN_SUBSTRING_KEY:
            continue
        if _word_match(key, name):
            return dict(SPONSORSHIP_DB[key], source='curated')

    words = set(name.split())
    for key in SPONSORSHIP_DB:
        if len(key) < _MIN_SUBSTRING_KEY and key in words:
            return dict(SPONSORSHIP_DB[key], source='curated')

    return None


def get_sponsorship_tier(company_name):
    """Get sponsorship tier (1=best, 5=unknown)"""
    info = get_sponsorship_info(company_name)
    return info['tier']

def is_f1_friendly(company_name):
    """Check if company is likely F-1 friendly"""
    info = get_sponsorship_info(company_name)
    return info['cpt'] is True and info['tier'] <= 2