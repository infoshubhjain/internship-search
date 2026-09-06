#!/usr/bin/env python3
"""
Pull structured data straight from applicant tracking systems.

Greenhouse, Lever, Ashby and SmartRecruiters all publish an unauthenticated
JSON API for their job boards. That is far better than scraping the rendered
page: it gives the real application deadline, the posted salary range, the
country, and - most usefully - whether the posting still exists at all.

Everything here degrades to None rather than raising: enrichment is a bonus
pass over the tracker, and one dead endpoint must never break a run.
"""
import json
import logging
import os
import re
import time
from datetime import date, datetime
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

CACHE_FILE = '.ats_cache.json'
CACHE_TTL_DAYS = 3
TIMEOUT = 20
USER_AGENT = 'internship-tracker (personal job search; +https://github.com/)'

# Deadline phrasings seen in real postings. Ordered most explicit first.
DEADLINE_PATTERNS = [
    r'appl(?:ications?|y)\s+(?:closes?|close|closing|deadline)\s*(?:on|:|is)?\s*([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})',
    r'appl(?:ications?|y)\s+by\s*:?\s*([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})',
    r'deadline\s*(?:to apply)?\s*(?:is|:)?\s*([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})',
    r'(?:closes?|closing)\s+(?:on\s+)?([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})',
    r'appl(?:ications?|y)\s+(?:closes?|close|by|deadline)[^.\n]{0,20}?(\d{4}-\d{2}-\d{2})',
    r'deadline[^.\n]{0,20}?(\d{4}-\d{2}-\d{2})',
]
_DEADLINE_RES = [re.compile(p, re.I) for p in DEADLINE_PATTERNS]


# --------------------------------------------------------------------------
# cache
# --------------------------------------------------------------------------

def _load_cache(path=CACHE_FILE):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache, path=CACHE_FILE):
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        os.replace(tmp, path)
    except OSError as e:
        logger.warning('could not write ATS cache: %s', e)


def _is_fresh(entry, today=None):
    today = today or date.today()
    try:
        fetched = date.fromisoformat(entry['fetched_at'])
    except (KeyError, TypeError, ValueError):
        return False
    return (today - fetched).days < CACHE_TTL_DAYS


# --------------------------------------------------------------------------
# URL -> API endpoint
# --------------------------------------------------------------------------

def detect_ats(url):
    """Identify the ATS behind a job URL.

    Returns (platform, org, job_id) or None. job_id is None for boards whose
    API only serves the whole board (Ashby).
    """
    if not url:
        return None
    parsed = urlparse(url)
    host, path = parsed.netloc.lower(), parsed.path.strip('/')
    parts = [p for p in path.split('/') if p]

    if 'greenhouse.io' in host:
        # /<org>/jobs/<id> or /embed/job_app?for=<org>&token=<id>
        if len(parts) >= 3 and parts[1] == 'jobs':
            return ('greenhouse', parts[0], parts[2])
        if len(parts) >= 2 and parts[0] == 'jobs':
            return ('greenhouse', None, parts[1])
        return None

    if 'lever.co' in host:
        if len(parts) >= 2:
            job_id = parts[1]
            return ('lever', parts[0], job_id)
        return None

    if 'ashbyhq.com' in host:
        if parts:
            return ('ashby', parts[0], parts[1] if len(parts) > 1 else None)
        return None

    if 'myworkdayjobs.com' in host:
        import workday
        parsed_wd = workday.parse_url(url)
        if not parsed_wd:
            return None
        tenant, datacenter, site = parsed_wd
        # The job path is everything after the site segment.
        after = path.split(f'{site}/', 1)
        job_path = '/' + after[1] if len(after) > 1 else ''
        if not job_path.startswith('/job'):
            return None
        return ('workday', f'{tenant}|{datacenter}|{site}', job_path)

    if 'smartrecruiters.com' in host:
        if len(parts) >= 2:
            return ('smartrecruiters', parts[0], parts[1])
        return None

    return None


def _get(url):
    response = requests.get(url, timeout=TIMEOUT, headers={'User-Agent': USER_AGENT})
    return response


# --------------------------------------------------------------------------
# per-platform fetch, normalized to one shape
# --------------------------------------------------------------------------

def _blank(alive=None):
    return {'alive': alive, 'deadline': '', 'salary_min': None, 'salary_max': None,
            'currency': '', 'location': '', 'country': '', 'employment_type': '',
            'remote': None, 'description': '', 'posted_at': ''}


def _fetch_greenhouse(org, job_id):
    if not org:
        return _blank()
    response = _get(f'https://boards-api.greenhouse.io/v1/boards/{org}/jobs/{job_id}?content=true')
    if response.status_code in (404, 410):
        return _blank(alive=False)
    if response.status_code != 200:
        return _blank()

    data = response.json()
    result = _blank(alive=True)
    result['deadline'] = normalize_deadline(data.get('application_deadline'))
    location = data.get('location') or {}
    result['location'] = location.get('name', '') if isinstance(location, dict) else str(location)
    result['description'] = _strip_html(data.get('content', ''))
    result['posted_at'] = (data.get('first_published') or '')[:10]

    ranges = data.get('pay_input_ranges') or []
    if ranges:
        first = ranges[0]
        result['salary_min'] = first.get('min_cents')
        result['salary_max'] = first.get('max_cents')
        result['currency'] = first.get('currency_type', '')
        # Greenhouse reports cents.
        for key in ('salary_min', 'salary_max'):
            if isinstance(result[key], int):
                result[key] = result[key] // 100
    return result


def _fetch_lever(org, job_id):
    response = _get(f'https://api.lever.co/v0/postings/{org}/{job_id}')
    if response.status_code in (404, 410):
        return _blank(alive=False)
    if response.status_code != 200:
        return _blank()

    data = response.json()
    result = _blank(alive=True)
    categories = data.get('categories') or {}
    result['location'] = categories.get('location', '')
    result['employment_type'] = categories.get('commitment', '')
    result['country'] = data.get('country', '') or ''
    result['remote'] = (data.get('workplaceType') or '').lower() == 'remote'
    result['description'] = data.get('descriptionPlain') or _strip_html(data.get('description', ''))

    salary = data.get('salaryRange') or {}
    result['salary_min'] = salary.get('min')
    result['salary_max'] = salary.get('max')
    result['currency'] = salary.get('currency', '')

    created = data.get('createdAt')
    if isinstance(created, int):
        # Lever sends epoch milliseconds.
        result['posted_at'] = datetime.fromtimestamp(created / 1000).date().isoformat()
    return result


def _fetch_ashby(org, job_id):
    """Ashby serves the whole board at once, so one call covers every job."""
    response = _get(f'https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true')
    if response.status_code in (404, 410):
        return _blank(alive=False)
    if response.status_code != 200:
        return _blank()

    jobs = (response.json() or {}).get('jobs', [])
    job = next((j for j in jobs if j.get('id') == job_id), None)
    if job is None:
        # The board exists but this posting is gone from it.
        return _blank(alive=False)

    result = _blank(alive=bool(job.get('isListed', True)))
    result['location'] = job.get('location', '') or ''
    result['employment_type'] = job.get('employmentType', '') or ''
    result['remote'] = bool(job.get('isRemote'))
    result['description'] = job.get('descriptionPlain') or _strip_html(job.get('descriptionHtml', ''))
    result['posted_at'] = (job.get('publishedAt') or '')[:10]

    compensation = job.get('compensation') or {}
    for tier in compensation.get('compensationTiers') or []:
        low, high = tier.get('minValue'), tier.get('maxValue')
        if low or high:
            result['salary_min'], result['salary_max'] = low, high
            result['currency'] = tier.get('currencyCode', '') or ''
            break
    return result


def _fetch_smartrecruiters(org, job_id):
    response = _get(f'https://api.smartrecruiters.com/v1/companies/{org}/postings/{job_id}')
    if response.status_code in (404, 410):
        return _blank(alive=False)
    if response.status_code != 200:
        return _blank()

    data = response.json()
    result = _blank(alive=True)
    location = data.get('location') or {}
    result['location'] = ', '.join(
        str(location.get(k)) for k in ('city', 'region', 'country') if location.get(k))
    result['country'] = (location.get('country') or '').upper()
    result['remote'] = bool(location.get('remote'))
    result['employment_type'] = ((data.get('typeOfEmployment') or {}).get('label') or '')
    result['posted_at'] = (data.get('releasedDate') or '')[:10]

    sections = ((data.get('jobAd') or {}).get('sections') or {})
    result['description'] = _strip_html(' '.join(
        (sections.get(k) or {}).get('text', '') for k in sections))
    return result


def _fetch_workday(org, job_id):
    """Enrich one Workday posting. org is 'tenant|datacenter|site'."""
    import workday

    try:
        tenant, datacenter, site = org.split('|')
    except ValueError:
        return _blank()

    detail = workday.fetch_detail(tenant, datacenter, site, job_id)
    if not detail:
        # Workday returns an empty body for a pulled posting as well as for a
        # transport error, so this cannot distinguish them; report unknown
        # rather than closing a listing that might still be live.
        return _blank()

    result = _blank(alive=True)
    result['location'] = detail.get('location', '') or ''
    country = detail.get('country')
    result['country'] = (country.get('descriptor', '') if isinstance(country, dict)
                         else str(country or ''))
    result['employment_type'] = detail.get('timeType', '') or ''
    result['description'] = _strip_html(detail.get('jobDescription', ''))
    result['posted_at'] = ''
    result['deadline'] = normalize_deadline(detail.get('endDate'))
    return result


FETCHERS = {
    'greenhouse': _fetch_greenhouse,
    'workday': _fetch_workday,
    'lever': _fetch_lever,
    'ashby': _fetch_ashby,
    'smartrecruiters': _fetch_smartrecruiters,
}


def _strip_html(html):
    if not html:
        return ''
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = (text.replace('&nbsp;', ' ').replace('&amp;', '&')
                .replace('&lt;', '<').replace('&gt;', '>').replace('&#39;', "'"))
    return re.sub(r'\s+', ' ', text).strip()


def normalize_deadline(value):
    """Coerce an ATS deadline value to ISO YYYY-MM-DD, or '' if unusable."""
    if not value:
        return ''
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        pass
    for fmt in ('%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return ''


def extract_deadline(text):
    """Find an application deadline stated in a job description."""
    if not text:
        return ''
    for pattern in _DEADLINE_RES:
        match = pattern.search(text)
        if match:
            parsed = normalize_deadline(match.group(1).replace(',', ', ').replace(', ,', ','))
            if parsed:
                return parsed
    return ''


def fetch_job(url, cache=None, use_cache=True):
    """Fetch and normalize one posting. Returns the blank shape on any failure."""
    detected = detect_ats(url)
    if not detected:
        return _blank()

    platform, org, job_id = detected
    if not job_id:
        return _blank()

    cache_key = f'{platform}:{org}:{job_id}'
    if use_cache and cache is not None:
        entry = cache.get(cache_key)
        if entry and _is_fresh(entry):
            return entry['data']

    try:
        result = FETCHERS[platform](org, job_id)
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        logger.debug('ATS fetch failed for %s: %s', url, e)
        return _blank()

    # A deadline stated only in the description is still a real deadline.
    if not result['deadline']:
        result['deadline'] = extract_deadline(result.get('description', ''))

    if cache is not None:
        cache[cache_key] = {'fetched_at': date.today().isoformat(), 'data': result}
    return result


def enrich_urls(urls, limit=None, delay=0.4, progress=None):
    """Fetch many postings, caching and rate-limiting. Returns {url: result}.

    Only URLs on a supported ATS are fetched; everything else is skipped
    without a request, so the limit is spent on listings that can answer.
    """
    cache = _load_cache()
    results = {}
    fetched = 0

    for url in urls:
        if not detect_ats(url):
            continue
        if limit is not None and fetched >= limit:
            break
        before = len(cache)
        results[url] = fetch_job(url, cache=cache)
        if len(cache) != before:
            # Only sleep when an actual request went out.
            fetched += 1
            if progress and fetched % 25 == 0:
                progress(fetched)
            time.sleep(delay)

    _save_cache(cache)
    return results
