#!/usr/bin/env python3
"""
Classify a job title as a technical (CS-relevant) role or not.

The upstream internship repos are "tech internships" lists, not software lists:
they carry product management, design, finance and marketing roles too. Those
pollute the apply queue and, worse, score as Priority 1 whenever the company
name matches. Everything downstream filters through is_technical() first.

Matching is word-boundary based. Substring matching produces false positives
that are hard to spot ("Design" inside "Designated", "ai" inside "Trainee").
"""
import re

# Checked first and win outright: a title naming one of these is not a
# software role even when it also mentions a technical field, as in
# "Product Manager, Machine Learning" or "Technical Recruiter".
NON_TECHNICAL = [
    r'product manager', r'product management', r'\bpm\b', r'program manager',
    r'project manager', r'product marketing',
    r'\bux\b', r'\bui/ux\b', r'user experience', r'\bdesigner\b', r'\bdesign\b',
    r'graphic', r'illustrat', r'\bbrand\b', r'content',
    r'market(ing|er)\b', r'\bsales\b', r'business development', r'account executive',
    r'recruit(er|ing|ment)', r'human resources', r'\bhr\b', r'people operations',
    r'\blegal\b', r'paralegal', r'compliance officer',
    r'accounting', r'\baudit', r'tax\b', r'payroll',
    r'supply chain', r'logistics', r'procurement', r'merchandis',
    r'\bmechanical\b', r'\bcivil\b', r'\bchemical\b', r'aerospace structures',
    r'\bmanufacturing\b', r'industrial engineer', r'process engineer',
    r'\bnursing\b', r'clinical', r'\bpharma', r'\bbiolog', r'chemistry',
    r'communications', r'public relations', r'social media',
    r'customer success', r'customer support', r'technical support',
    r'\bteacher\b', r'\bteaching\b', r'\btutor\b',
]

# Ordered: the first match names the category, so put specific before general.
TECHNICAL_CATEGORIES = [
    ('Cybersecurity', [
        r'cyber', r'\binfosec\b', r'information security', r'security engineer',
        r'security research', r'application security', r'\bappsec\b',
        r'penetration test', r'\bsoc analyst\b', r'threat', r'cryptograph',
    ]),
    ('Machine Learning / AI', [
        r'machine learning', r'\bml\b', r'\bmlops\b',
        r'artificial intelligence', r'\bai\b', r'deep learning',
        r'computer vision', r'\bnlp\b', r'natural language',
        r'generative', r'\bllm\b', r'applied scien',
    ]),
    ('Data Engineering', [
        r'data engineer', r'data infrastructure', r'data platform',
        r'\betl\b', r'analytics engineer', r'big data',
    ]),
    ('Data Science', [
        r'data scien', r'\bdata analyst\b', r'quantitative analy',
        r'statistic', r'business intelligence', r'analytics',
    ]),
    ('Cloud / DevOps / Infrastructure', [
        r'\bdevops\b', r'\bsre\b', r'site reliability', r'platform engineer',
        r'infrastructure', r'cloud engineer', r'cloud infrastructure',
        r'systems engineer', r'network engineer', r'\bkubernetes\b',
        r'\blinux\b', r'\bwindows\b', r'supercomput', r'\bhpc\b', r'distributed comput',
    ]),
    ('Backend Engineering', [
        r'back[- ]?end', r'server[- ]?side', r'\bapi engineer\b', r'distributed systems',
    ]),
    ('Frontend Engineering', [
        r'front[- ]?end', r'\bweb developer\b', r'\bui engineer\b', r'client[- ]?side',
    ]),
    ('Full-Stack Engineering', [
        r'full[- ]?stack',
    ]),
    ('Mobile Engineering', [
        r'\bios\b', r'\bandroid\b', r'\bmobile\b.*(engineer|develop)',
    ]),
    ('Quantitative Technology', [
        r'quantitative (technolog|developer|engineer|trading|research)',
        r'\bquant\b.*(developer|engineer|technolog)',
        r'algorithmic trading', r'trading technolog',
    ]),
    ('Research', [
        r'research (intern|assistant|scientist|engineer|program|scholar)',
        r'undergraduate research', r'\breu\b', r'research experience',
    ]),
    ('Hardware / Embedded', [
        r'embedded', r'firmware', r'hardware engineer', r'\bfpga\b', r'\basic\b',
        r'\bvlsi\b', r'silicon', r'chip design',
    ]),
    ('Software Engineering', [
        r'software engineer', r'software develop', r'\bswe\b', r'\bsde\b',
        r'software intern', r'programmer', r'developer intern',
        r'engineering intern', r'compiler', r'operating system',
        r'application develop', r'\binference\b', r'\bruntime\b',
        r'game develop', r'graphics engineer',
    ]),
    ('General Technology', [
        r'\btechnolog', r'computer scien', r'\bcs intern\b', r'\bit intern\b',
        r'information technology', r'technical intern', r'\bengineering\b',
    ]),
]

# An unambiguous engineering title wins over the exclusion list above, so
# "Software Engineer Intern, Brand Innovation" is not thrown out for the word
# "Brand". Only titles that name the engineering discipline itself belong here.
STRONG_TECHNICAL = [
    r'software engineer', r'software develop', r'\bswe\b', r'\bsde\b',
    r'back[- ]?end', r'front[- ]?end', r'full[- ]?stack',
    r'data engineer', r'machine learning engineer', r'\bdevops\b', r'\bsre\b',
    r'site reliability', r'security engineer', r'infrastructure',
]

_STRONG_RE = re.compile('|'.join(STRONG_TECHNICAL), re.I)
_NON_TECHNICAL_RE = re.compile('|'.join(NON_TECHNICAL), re.I)
_CATEGORY_RES = [(name, re.compile('|'.join(pats), re.I))
                 for name, pats in TECHNICAL_CATEGORIES]


def classify_role(title):
    """Return the technical category of a job title, or None if not technical.

    None means "do not put this in the apply queue" - it is either a
    non-technical role or a title too vague to act on.
    """
    if not title:
        return None
    title = str(title)

    if not _STRONG_RE.search(title) and _NON_TECHNICAL_RE.search(title):
        return None

    for name, pattern in _CATEGORY_RES:
        if pattern.search(title):
            return name
    return None


def is_technical(title):
    """True if the title is a computer-science-relevant role."""
    return classify_role(title) is not None
