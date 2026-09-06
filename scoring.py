#!/usr/bin/env python3
"""
Score a listing instead of bucketing it by first keyword match.

The old assign_priority() returned on the first matching keyword list, so
"Google Product Manager" scored Priority 1 purely because the company name
matched, and a well-sponsored startup SWE role scored Priority 5 because no
list mentioned it. Scoring on independent axes and bucketing at the end fixes
both: every signal contributes, and the ranking degrades gracefully for
companies nobody has hand-listed.

score_listing() returns (score, priority, reasons). Priority stays 1-5 so the
existing tracker, dashboard and workflow keep working.
"""
import re

from roles import classify_role
from sponsorship_database import get_sponsorship_info, requires_citizenship

# Role relevance. A direct software role is worth more than a general tech one.
ROLE_POINTS = {
    'Software Engineering': 30,
    'Backend Engineering': 30,
    'Full-Stack Engineering': 30,
    'Frontend Engineering': 28,
    'Machine Learning / AI': 30,
    'Data Engineering': 27,
    'Cloud / DevOps / Infrastructure': 27,
    'Cybersecurity': 26,
    'Mobile Engineering': 25,
    'Data Science': 24,
    'Quantitative Technology': 24,
    'Hardware / Embedded': 20,
    'Research': 22,
    'General Technology': 15,
}

# Sponsorship tier from sponsorship_database.py (1 = full sponsorship).
# Tier 6 is the citizenship/clearance barrier, which for an F-1 student is
# worse than simply unknown - hence below tier 5.
TIER_POINTS = {1: 30, 2: 24, 3: 16, 4: 8, 5: 10, 6: 0}

# Programs aimed at first- and second-year students. These have the narrowest
# windows and the least competition, so they outrank everything else.
UNDERCLASSMAN_PATTERNS = [
    r'\bstep\b', r'\bexplore\b', r'university (swe|program)', r'\bengaging\b',
    r'freshman', r'sophomore', r'first[- ]year', r'second[- ]year',
    r'underclass', r'early career', r'\bemerging\b', r'\bdiscovery\b',
    r'\bignite\b', r'\blaunch\b.*intern', r'\bpathways?\b',
]
_UNDERCLASSMAN_RE = re.compile('|'.join(UNDERCLASSMAN_PATTERNS), re.I)

# Companies whose internships are worth extra weight for career value.
TOP_ENGINEERING = [
    'google', 'microsoft', 'meta', 'amazon', 'apple', 'netflix', 'nvidia',
    'openai', 'anthropic', 'stripe', 'databricks', 'snowflake', 'figma',
    'jane street', 'two sigma', 'citadel', 'hudson river', 'jump trading',
    'de shaw', 'optiver', 'imc', 'susquehanna', 'sig', 'bloomberg',
    'palantir', 'airbnb', 'uber', 'lyft', 'pinterest', 'linkedin', 'datadog',
]


def _company_matches(company, names):
    company = (company or '').lower()
    return any(name in company for name in names)


def score_listing(company, role, sponsorship_tier=None, no_sponsorship=False):
    """Score a listing 0-100 and bucket it into priority 1-5.

    Returns (score, priority, reasons). reasons explains the score so a
    surprising ranking can be traced back to the signal that caused it.
    """
    reasons = []

    category = classify_role(role)
    is_underclassman = bool(_UNDERCLASSMAN_RE.search(role or ''))

    # The aggregator repos carry the occasional full-time requisition - a
    # "2026 Intern Conversion: 2027 FT Software Engineer" is a graduate hire,
    # not something a sophomore can apply to.
    from intl_sources import looks_like_internship
    if role and not looks_like_internship(role) and not is_underclassman:
        return 0, '5', ['not an internship posting']

    if category is None:
        # Named early-career programs ("STEP", "Explore") do not say
        # "software" anywhere in the title, but they are the single most
        # valuable listings for a sophomore, so they are not rejected.
        if not is_underclassman:
            # Non-technical roles stay in the tracker but rank last; they must
            # never displace a software role in the apply queue.
            return 0, '5', ['not a technical role']
        category = 'General Technology'

    role_score = ROLE_POINTS.get(category, 15)
    reasons.append(f'{category} (+{role_score})')

    # Sponsorship: the binding constraint for an F-1 student.
    citizenship_blocked = False
    if no_sponsorship:
        sponsor_score = 0
        reasons.append('no sponsorship (+0)')
    else:
        # A cached tier from an earlier scrape can be stale or wrong, but a
        # citizenship requirement is a property of the employer, so it is
        # always re-checked against the company name rather than trusted from
        # the row.
        if requires_citizenship(company):
            tier = 6
        else:
            tier = sponsorship_tier
            if tier in (None, ''):
                tier = get_sponsorship_info(company).get('tier', 5)
            try:
                tier = int(tier)
            except (TypeError, ValueError):
                tier = 5
        sponsor_score = TIER_POINTS.get(tier, 10)
        citizenship_blocked = tier == 6
        label = 'citizenship/clearance required' if citizenship_blocked else f'sponsorship tier {tier}'
        reasons.append(f'{label} (+{sponsor_score})')

    # Underclassman programs: narrow windows, so rank them to the top.
    underclassman_score = 0
    if is_underclassman:
        underclassman_score = 25
        reasons.append('underclassman program (+25)')

    # Career value.
    company_score = 0
    if _company_matches(company, TOP_ENGINEERING):
        company_score = 15
        reasons.append('top engineering org (+15)')

    score = min(100, role_score + sponsor_score + underclassman_score + company_score)

    # A citizenship or clearance requirement is a hard barrier, not a penalty
    # to be outweighed by a prestigious company name.
    if citizenship_blocked or no_sponsorship:
        return min(score, 25), '5', reasons

    # Buckets chosen so priority 1-2 stays a realistically sized daily queue.
    if score >= 75:
        priority = '1'
    elif score >= 60:
        priority = '2'
    elif score >= 45:
        priority = '3'
    elif score >= 30:
        priority = '4'
    else:
        priority = '5'

    return score, priority, reasons
