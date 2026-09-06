#!/usr/bin/env python3
"""
Score an international internship out of 100 for this candidate:
a UIUC CS sophomore (graduating May 2028), Indian citizen, currently in the US
on F-1, seeking a paid Summer 2027 internship outside the United States.

Weights come straight from the search brief:
    role relevance      25
    international eligibility 25
    compensation        15
    company/career value 15
    candidate eligibility 10
    location preference 10
"""
from geo import LOCATION_PREFERENCE, TIER_1
from roles import classify_role
from visa import CATEGORY_A, CATEGORY_B, CATEGORY_C

# Role relevance out of 25.
ROLE_POINTS = {
    'Software Engineering': 25,
    'Backend Engineering': 25,
    'Full-Stack Engineering': 25,
    'Frontend Engineering': 23,
    'Machine Learning / AI': 25,
    'Data Engineering': 22,
    'Cloud / DevOps / Infrastructure': 22,
    'Cybersecurity': 21,
    'Mobile Engineering': 20,
    'Data Science': 20,
    'Quantitative Technology': 21,
    'Research': 20,
    'Hardware / Embedded': 16,
    'General Technology': 12,
}

# International eligibility out of 25.
VISA_POINTS = {CATEGORY_A: 25, CATEGORY_B: 14, CATEGORY_C: 2}

# Company/career value out of 15. Everything else scores a neutral 7.
TOP_TIER = {
    'openai', 'anthropic', 'google', 'deepmind', 'isomorphic labs', 'microsoft',
    'meta', 'apple', 'amazon', 'nvidia', 'stripe', 'databricks', 'figma',
    'jane street', 'optiver', 'imc', 'jump trading', 'squarepoint', 'drw',
    'xtx markets', 'g-research', 'man group', 'marshall wace', 'citadel',
    'atlassian', 'canva', 'shopify', 'spotify', 'adyen', 'booking',
    'cloudflare', 'datadog', 'mongodb', 'elastic', 'gitlab', 'palantir',
}
STRONG_TIER = {
    'monzo', 'revolut', 'wise', 'starling', 'gocardless', 'checkout',
    'deliveroo', 'ocado', 'darktrace', 'arm', 'graphcore', 'wayve',
    'cohere', 'perplexity', 'elevenlabs', 'notion', 'linear', 'ramp',
    'celonis', 'personio', 'n26', 'zalando', 'hellofresh', 'klarna',
    'grab', 'sea', 'shopee', 'coupang', 'rakuten', 'wolt', 'supercell',
    'nokia', 'ericsson', 'unity', 'zendesk', 'proton', 'sonarsource',
    'affirm', 'coinbase', 'robinhood', 'instacart', 'airbnb', 'dropbox',
    'discord', 'asana', 'twilio', 'scale ai', 'faire', 'supabase', 'temporal',
}


def _company_in(company, names):
    company = (company or '').lower()
    return any(name in company for name in names)


def score(role='', country='', visa_category=CATEGORY_B, paid=None,
          company='', employment_type='', english='Unclear', is_2027=False):
    """Score an opportunity 0-100.

    Returns (total, breakdown, barriers). barriers names what would stop the
    candidate, so a high score with a real obstacle is not silently promoted.
    """
    breakdown = {}
    barriers = []

    category = classify_role(role)
    breakdown['role'] = ROLE_POINTS.get(category, 0) if category else 0
    if not category:
        barriers.append('not clearly a computer-science role')

    breakdown['visa'] = VISA_POINTS.get(visa_category, 14)
    if visa_category == CATEGORY_C:
        barriers.append('local work authorization likely required')
    elif visa_category == CATEGORY_B:
        barriers.append('work authorization unstated - confirm before investing time')

    # Compensation out of 15. Unknown pay is not the same as unpaid: most
    # employers simply do not publish intern rates.
    if paid is True:
        breakdown['pay'] = 15
    elif paid is None:
        breakdown['pay'] = 10
        barriers.append('compensation not publicly disclosed')
    else:
        breakdown['pay'] = 1
        barriers.append('appears unpaid')

    if _company_in(company, TOP_TIER):
        breakdown['company'] = 15
    elif _company_in(company, STRONG_TIER):
        breakdown['company'] = 11
    else:
        breakdown['company'] = 7

    # Candidate eligibility out of 10. A sophomore graduating May 2028 is
    # eligible for undergraduate internships; PhD-only postings are not a fit.
    eligibility = 10
    role_lower = (role or '').lower()
    if any(term in role_lower for term in ('phd', 'ph.d', 'doctoral', 'postdoc')):
        eligibility = 2
        barriers.append('appears to target PhD candidates')
    elif 'master' in role_lower or 'msc' in role_lower or ' ms,' in role_lower:
        eligibility = 5
        barriers.append('may target masters students')
    if employment_type and 'intern' not in employment_type.lower() \
            and employment_type.lower() not in ('', 'temporary', 'contract', 'parttime'):
        eligibility = min(eligibility, 6)
    breakdown['eligibility'] = eligibility

    # Location preference out of 10, on the brief's ordering.
    if country in LOCATION_PREFERENCE:
        rank = LOCATION_PREFERENCE.index(country)
        breakdown['location'] = max(4, 10 - rank // 2)
    elif country and country not in ('United States',):
        breakdown['location'] = 3
    else:
        breakdown['location'] = 0

    if english == 'No':
        barriers.append('local-language fluency required')
        breakdown['location'] = max(0, breakdown['location'] - 4)
    elif english == 'Unclear' and country not in TIER_1:
        barriers.append('English working environment unconfirmed')

    if not is_2027:
        barriers.append('not confirmed as a Summer 2027 posting')

    total = min(100, sum(breakdown.values()))

    # Hard gates. Without these a prestigious name and a good location can
    # float a role the candidate cannot take, or cannot do, into the top of
    # the shortlist.
    if not category:
        # Not a computer-science role: it does not belong in this search.
        total = 0
    elif visa_category == CATEGORY_C:
        # Local authorization required. The brief says keep these visible but
        # never present them as high-priority.
        total = min(total, 40)
    elif english == 'No':
        total = min(total, 55)

    return total, breakdown, barriers
