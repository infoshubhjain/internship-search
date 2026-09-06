#!/usr/bin/env python3
"""
Classify how reachable an international internship is for an F-1 student who
is an Indian citizen studying in the US.

Three categories, from the search brief:

  A  Clearly international-friendly - says it sponsors, relocates, or runs an
     established international intake.
  B  Potentially eligible - says nothing either way. Most postings land here,
     and that is the honest answer: "unclear" is not "no".
  C  Local authorization likely required - says it needs existing work rights,
     citizenship, or a clearance, or is a nationality-restricted employer.

Classification reads the posting text, so it is only as good as what the
company wrote. Every result carries the phrase that decided it, so a
surprising call can be checked against the source rather than trusted blindly.
"""
import re

CATEGORY_A = 'A'
CATEGORY_B = 'B'
CATEGORY_C = 'C'

CATEGORY_LABELS = {
    CATEGORY_A: 'A - Clearly international-friendly',
    CATEGORY_B: 'B - Potentially eligible, needs checking',
    CATEGORY_C: 'C - Local work authorization likely required',
}

# Phrases that state a restriction. Checked first: an explicit "no sponsorship"
# outranks generic diversity boilerplate about welcoming applicants.
RESTRICTION_PATTERNS = [
    (r'(?:not|unable to|cannot|will not|do not|does not|no)\s+(?:be able to\s+)?'
     r'(?:offer|provide|sponsor)\w*\s+(?:visa\s+)?sponsor', 'states it does not sponsor visas'),
    (r'without (?:the need for )?(?:visa )?sponsorship', 'requires no-sponsorship status'),
    (r'sponsorship is not (?:available|offered|provided)', 'sponsorship not available'),
    (r'must (?:already )?(?:have|possess|hold)[^.\n]{0,60}(?:right to work|work authorisation|'
     r'work authorization|work permit|valid visa)', 'requires existing work rights'),
    (r'(?:permanent resident|citizens? only|must be a citizen)', 'citizenship or PR required'),
    (r'security clearance|sc cleared|dv cleared|baseline security', 'security clearance required'),
    (r'eligible to work in [^.\n]{0,40}without', 'requires unrestricted local work rights'),
    (r'(?:right to work|work authorisation|work authorization) in [^.\n]{0,40}is (?:required|essential)',
     'local work rights required'),
    (r'currently enrolled at (?:a|an) (?:uk|australian|irish|canadian|singapore\w*|'
     r'german|dutch|swedish|danish|norwegian|finnish|swiss)[^.\n]{0,30}(?:university|institution)',
     'requires enrolment at a local university'),
]

# Phrases that state international friendliness.
SUPPORT_PATTERNS = [
    (r'(?:visa|immigration) sponsorship (?:is )?(?:available|provided|offered|supported)',
     'states visa sponsorship is available'),
    (r'we (?:will )?(?:offer|provide|support|sponsor)[^.\n]{0,40}(?:visa|work permit|immigration)',
     'offers visa or work-permit support'),
    (r'relocation (?:package|assistance|support|allowance|bonus)', 'offers relocation support'),
    (r'we sponsor visas', 'states it sponsors visas'),
    (r'international (?:students|applicants|candidates) (?:are )?(?:welcome|encouraged|eligible)',
     'explicitly welcomes international applicants'),
    (r'open to (?:candidates|students|applicants) (?:from )?(?:worldwide|globally|any country|'
     r'all(?:\s+\w+){0,2} nationalit)', 'open to applicants worldwide'),
    (r'(?:global|international) intern(?:ship)? programme?', 'runs an international internship programme'),
    (r'(?:tier 2|tier 4|skilled worker|graduate route|482|485|subclass 407|subclass 408|'
     r'blue card|working holiday)', 'names a specific visa route'),
    (r'we (?:are )?(?:able to )?sponsor', 'states it can sponsor'),
]

_RESTRICTION_RES = [(re.compile(p, re.I), why) for p, why in RESTRICTION_PATTERNS]
_SUPPORT_RES = [(re.compile(p, re.I), why) for p, why in SUPPORT_PATTERNS]

# Employers that are nationality-restricted by the nature of the work,
# regardless of what a given posting says.
RESTRICTED_EMPLOYERS = {
    'helsing', 'anduril', 'palantir', 'bae systems', 'qinetiq', 'dstl',
    'lockheed', 'raytheon', 'rtx', 'northrop', 'l3harris', 'leonardo',
    'thales', 'rheinmetall', 'saab', 'mbda', 'babcock', 'serco',
}

# Countries that run a well-established route usable by a student enrolled at a
# foreign university. This does not make an offer certain - it means the legal
# pathway exists and is worth pursuing.
INTERNSHIP_VISA_ROUTES = {
    'United Kingdom': 'Government Authorised Exchange (Tier 5 / GAE) covers student internships',
    'Ireland': 'Atypical Working Scheme covers short internships for non-EEA students',
    'Germany': 'Internship visa for students enrolled abroad; recognised for degree-relevant placements',
    'Netherlands': 'Intern residence permit sponsored by a recognised employer',
    'Switzerland': 'Trainee permit under bilateral trainee agreements',
    'Sweden': 'Residence permit for interns tied to a specific employer',
    'Denmark': 'Internship residence permit for students in a relevant field',
    'Norway': 'Skilled-worker or trainee permit route',
    'Finland': 'Residence permit for an internship',
    'Australia': 'Subclass 407 Training visa for occupational training',
    'New Zealand': 'Specific Purpose Work Visa for short placements',
    'Canada': 'Co-op / internship work permit; often needs the placement to be degree-required',
    'Singapore': 'Training Employment Pass or Work Holiday Pass',
    'Japan': 'Designated Activities (internship) visa',
    'India': 'Home country - no visa needed',
}


def classify(description='', company='', country='', title=''):
    """Classify one posting.

    Returns {'category', 'reason', 'evidence', 'visa_route'}.
    """
    text = ' '.join(str(x or '') for x in (title, description))
    company_lower = (company or '').lower()

    if any(re.search(r'\b' + re.escape(name) + r'\b', company_lower)
           for name in RESTRICTED_EMPLOYERS):
        return {
            'category': CATEGORY_C,
            'reason': 'defence or nationality-restricted employer',
            'evidence': company,
            'visa_route': '',
        }

    for pattern, why in _RESTRICTION_RES:
        match = pattern.search(text)
        if match:
            return {
                'category': CATEGORY_C,
                'reason': why,
                'evidence': _snippet(text, match),
                'visa_route': '',
            }

    route = INTERNSHIP_VISA_ROUTES.get(country, '')

    for pattern, why in _SUPPORT_RES:
        match = pattern.search(text)
        if match:
            return {
                'category': CATEGORY_A,
                'reason': why,
                'evidence': _snippet(text, match),
                'visa_route': route,
            }

    return {
        'category': CATEGORY_B,
        'reason': 'no work-authorization statement found; eligibility must be confirmed',
        'evidence': '',
        'visa_route': route,
    }


def _snippet(text, match, width=90):
    """The sentence fragment around a match, for showing why a call was made."""
    start = max(0, match.start() - width // 2)
    end = min(len(text), match.end() + width // 2)
    return re.sub(r'\s+', ' ', text[start:end]).strip()


def english_working_language(description='', country=''):
    """Whether the role looks like it operates in English.

    Tier 1 countries are English-speaking by default. Elsewhere, only an
    explicit statement counts - assuming English in a German posting is how a
    shortlist fills up with roles the candidate cannot actually do.
    """
    from geo import TIER_1

    text = str(description or '')
    if re.search(r'(fluent|native|proficient)\s+(?:in\s+)?'
                 r'(german|french|dutch|swedish|danish|norwegian|finnish|japanese|'
                 r'mandarin|korean|spanish|italian|portuguese|polish)', text, re.I):
        return 'No'
    if country in TIER_1:
        return 'Yes'
    if re.search(r'(english is (?:our|the) (?:working|company|official) language|'
                 r'working language is english|all[^.\n]{0,20}in english|'
                 r'english[- ]speaking (?:environment|team))', text, re.I):
        return 'Yes'
    return 'Unclear'
