#!/usr/bin/env python3
"""
Fetch whole company job boards and keep the international internships.

Boards are pulled in full (one request per company) and filtered locally,
which is both faster and kinder to the APIs than per-job requests. The filter
chain is deliberately ordered cheapest-first: title looks like an internship,
then the role is computer-science, then the location is outside the US, then
the season is plausibly Summer 2027.
"""
import argparse
import concurrent.futures as futures
import logging
import re
import sys
from datetime import date, datetime

import requests

from ats import _strip_html
from geo import detect_country, is_remote
from intl_boards import board_url
from roles import classify_role

logger = logging.getLogger(__name__)

TIMEOUT = 25
USER_AGENT = 'internship-tracker (personal job search)'
MAX_WORKERS = 8

# Underscore is a word character, so \b will not fire in "Intern_OnSite";
# these use an explicit separator class instead.
_SEP = r'(?:^|[^A-Za-z])'
_END = r'(?:[^A-Za-z]|$)'

INTERN_PATTERNS = [
    _SEP + r'interns?' + _END, r'\binternship\b', r'\bplacement\b', r'\bindustrial year\b',
    r'\bsummer analyst\b', _SEP + r'co[- ]?op' + _END, r'\bstudent\b',
    r'\bgraduate scheme\b',
    r'\bworking student\b', r'\bwerkstudent\b', r'\bstage\b', r'\bpraktikum\b',
    r'\bapprentice\b', r'\bcampus\b', r'\bearly careers?\b', r'\btrainee\b',
]
_INTERN_RE = re.compile('|'.join(INTERN_PATTERNS), re.I)

# Titles that say "intern" but are not student internships.
# A graduate/full-time role, not a student internship.
# "FT" is matched case-sensitively; lowercase "ft" appears inside ordinary
# words far too often to treat as a full-time marker.
_FULL_TIME_RE = re.compile(
    r'(?i:\bfull[\s-]?time\b|\bpermanent\b|\bnew ?grad(uate)?\b)|\bFT\b')

_NOT_INTERN_RE = re.compile(
    r'\binternal\b|\binternational sales\b|\bintern(?:al)? audit\b|'
    r'\bmanager, interns\b|\bintern(?:ship)? (?:program )?manager\b|'
    # "2026 Intern Conversion: 2027 FT Software Engineer" is a full-time
    # requisition for someone who already interned, not an internship.
    r'\bintern conversion\b|\bconversion\b.*\bFT\b', re.I)

# A posting is treated as Summer 2027 if it says so, and as a candidate if it
# names no year at all (recruiting for 2027 is open now, and many boards omit
# the year). An explicit 2026 or earlier is stale as of this cycle.
_YEAR_RE = re.compile(r'\b(20\d{2})\b')
CURRENT_CYCLE_YEAR = 2027


def looks_like_internship(title):
    """True if the title is a student internship rather than a graduate hire.

    Campus recruiting titles come in matched pairs - "Campus Engineer (Intern)"
    and "Campus Engineer (Full-Time)" - so a title that says full-time is a
    graduate role even though it matches on "campus".
    """
    if not title:
        return False
    if _NOT_INTERN_RE.search(title):
        return False
    if _FULL_TIME_RE.search(title) and not re.search(r'\bintern', title, re.I):
        return False
    return bool(_INTERN_RE.search(title))


def season_status(title, description='', today=None):
    """Classify a posting's cycle: 'summer-2027', 'undated' or 'stale'.

    'undated' is kept, not discarded: a board that lists "Software Engineer
    Intern" with no year is usually recruiting for the next cycle.
    """
    today = today or date.today()
    text = f'{title} {description[:2000]}'
    years = {int(y) for y in _YEAR_RE.findall(text) if 2020 <= int(y) <= 2035}

    if CURRENT_CYCLE_YEAR in years:
        return 'summer-2027'
    if not years:
        return 'undated'
    if any(y > CURRENT_CYCLE_YEAR for y in years):
        return 'undated'
    # Only years at or before the cycle that has already run.
    if max(years) <= today.year:
        return 'stale'
    return 'undated'


def _get(url):
    return requests.get(url, timeout=TIMEOUT, headers={'User-Agent': USER_AGENT})


# Board names that describe the board, not the employer.
_GENERIC_BOARD_NAMES = {'internship list', 'careers', 'jobs', 'job board',
                        'internships', 'university', 'campus', 'early careers'}


def display_company(org, api_name='', platform=''):
    """Best human-readable employer name for a board.

    Lever and Ashby report no company name at all, and some Greenhouse boards
    are named for the programme ("Internship List" is Geotab). Board discovery
    already recorded the company each token was first seen with, so prefer
    that, then the API name, then a prettified token.
    """
    name = (api_name or '').strip()
    if name and name.lower() not in _GENERIC_BOARD_NAMES:
        return name

    try:
        from board_discovery import load_discovered
        entry = load_discovered().get(f'{platform}:{org}') if platform else None
        if entry and entry.get('company'):
            return entry['company']
    except Exception:
        pass

    # "the-exploration-company" -> "The Exploration Company"
    pretty = re.sub(r'[._-]+', ' ', org).strip()
    pretty = re.sub(r'\s+', ' ', pretty)
    return pretty.title() if pretty.islower() or '-' in org or '_' in org else pretty


def _normalize_greenhouse(job, org):
    location = (job.get('location') or {})
    return {
        'company': display_company(org, job.get('company_name'), 'greenhouse'),
        'title': job.get('title', ''),
        'location': location.get('name', '') if isinstance(location, dict) else str(location),
        'link': job.get('absolute_url', ''),
        'description': _strip_html(job.get('content', '')),
        'posted_at': (job.get('first_published') or job.get('updated_at') or '')[:10],
        'employment_type': '',
        'country_hint': '',
        'salary': '',
        'external_id': str(job.get('id', '')),
        'source': f'greenhouse:{org}',
    }


def _normalize_lever(job, org):
    categories = job.get('categories') or {}
    salary = job.get('salaryRange') or {}
    amount = ''
    if salary.get('min') or salary.get('max'):
        low, high = salary.get('min'), salary.get('max')
        amount = (f'{low:,.0f}-{high:,.0f}' if low and high and low != high
                  else f'{(low or high):,.0f}')
        amount = f"{amount} {salary.get('currency', '')}".strip()
    posted = job.get('createdAt')
    return {
        'company': display_company(org, '', 'lever'),
        'title': job.get('text', ''),
        'location': categories.get('location', ''),
        'link': job.get('hostedUrl') or job.get('applyUrl', ''),
        'description': job.get('descriptionPlain') or _strip_html(job.get('description', '')),
        'posted_at': (datetime.fromtimestamp(posted / 1000).date().isoformat()
                      if isinstance(posted, int) else ''),
        'employment_type': categories.get('commitment', ''),
        'country_hint': job.get('country', '') or '',
        'salary': amount,
        'external_id': str(job.get('id', '')),
        'source': f'lever:{org}',
    }


def _normalize_ashby(job, org):
    amount = ''
    for tier in (job.get('compensation') or {}).get('compensationTiers') or []:
        low, high = tier.get('minValue'), tier.get('maxValue')
        if low or high:
            amount = (f'{low:,.0f}-{high:,.0f}' if low and high and low != high
                      else f'{(low or high):,.0f}')
            amount = f"{amount} {tier.get('currencyCode', '')}".strip()
            break
    locations = [job.get('location', '')] + list(job.get('secondaryLocations') or [])
    locations = [loc.get('location') if isinstance(loc, dict) else loc for loc in locations]
    return {
        'company': display_company(org, '', 'ashby'),
        'title': job.get('title', ''),
        'location': ', '.join(filter(None, locations)),
        'link': job.get('jobUrl') or job.get('applyUrl', ''),
        'description': job.get('descriptionPlain') or _strip_html(job.get('descriptionHtml', '')),
        'posted_at': (job.get('publishedAt') or '')[:10],
        'employment_type': job.get('employmentType', '') or '',
        'country_hint': '',
        'salary': amount,
        'external_id': str(job.get('id', '')),
        'source': f'ashby:{org}',
    }


NORMALIZERS = {
    'greenhouse': _normalize_greenhouse,
    'lever': _normalize_lever,
    'ashby': _normalize_ashby,
}


def fetch_board(platform, org, want_content=True):
    """Return every posting on one board, normalized. [] on any failure."""
    url = board_url(platform, org, content=want_content and platform == 'greenhouse')
    try:
        response = _get(url)
    except requests.RequestException as e:
        logger.warning('%s:%s unreachable: %s', platform, org, e)
        return []

    if response.status_code != 200:
        logger.warning('%s:%s returned HTTP %s', platform, org, response.status_code)
        return []

    try:
        payload = response.json()
    except ValueError:
        logger.warning('%s:%s returned non-JSON', platform, org)
        return []

    jobs = payload.get('jobs', payload) if isinstance(payload, dict) else payload
    if not isinstance(jobs, list):
        return []

    normalize = NORMALIZERS[platform]
    out = []
    for job in jobs:
        try:
            out.append(normalize(job, org))
        except (AttributeError, TypeError, KeyError):
            continue
    return out


def filter_international_internships(postings):
    """Keep the postings that are CS internships outside the United States."""
    kept = []
    for posting in postings:
        title = posting.get('title', '')
        if not looks_like_internship(title):
            continue

        category = classify_role(title)
        if not category:
            continue

        location = posting.get('location', '')
        country = detect_country(location, posting.get('country_hint'))
        if not country or country == 'United States':
            # A fully remote posting with no country is worth keeping only if
            # the description names somewhere; otherwise it is unactionable.
            if not (is_remote(location) and country is None):
                continue
            country = detect_country(posting.get('description', '')[:400])
            if not country or country == 'United States':
                continue

        season = season_status(title, posting.get('description', ''))
        if season == 'stale':
            continue

        posting = dict(posting)
        posting['country'] = country
        posting['category'] = category
        posting['season'] = season
        kept.append(posting)
    return kept


def scrape_all(boards=None, max_workers=MAX_WORKERS, progress=None,
               include_workday=True):
    """Fetch every board in parallel and filter the results.

    Defaults to the curated list plus everything board_discovery has learned
    from job URLs already in the trackers, so coverage grows on its own.
    """
    if boards is None:
        from board_discovery import all_boards
        boards = all_boards()
    all_postings = []
    done = 0

    with futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        jobs = {pool.submit(fetch_board, platform, org): (platform, org)
                for platform, org in boards}
        for future in futures.as_completed(jobs):
            platform, org = jobs[future]
            try:
                postings = future.result()
            except Exception as e:
                logger.warning('%s:%s failed: %s', platform, org, e)
                postings = []
            all_postings.extend(postings)
            done += 1
            if progress:
                progress(done, len(boards), org, len(postings))

    logger.info('Fetched %d postings from %d boards', len(all_postings), len(boards))

    if include_workday:
        # Workday is where the large formal employers live - the banks and
        # F500 most likely to have an established visa process - so it is
        # worth the extra pass even though it is slower than a board API.
        try:
            import workday
            wd = workday.scrape_all(progress=progress)
            logger.info('Fetched %d postings from %d Workday tenants',
                        len(wd), len(workday.load_tenants()))
            all_postings.extend(wd)
        except Exception as e:
            logger.warning('Workday pass failed, continuing without it: %s', e)

    kept = filter_international_internships(all_postings)
    logger.info('%d are international CS internships', len(kept))
    return kept


def check_boards(boards=None):
    """Report which boards still respond, for maintaining the list."""
    if boards is None:
        from board_discovery import all_boards
        boards = all_boards()
    dead = []
    with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        jobs = {pool.submit(fetch_board, p, o, False): (p, o) for p, o in boards}
        for future in futures.as_completed(jobs):
            platform, org = jobs[future]
            count = len(future.result())
            status = 'ok' if count else 'DEAD'
            if not count:
                dead.append(f'{platform}:{org}')
            print(f'  {status:5} {platform:12} {org:26} {count}')
    print(f'\n{len(boards) - len(dead)}/{len(boards)} boards responding.')
    if dead:
        print('Not responding: ' + ', '.join(sorted(dead)))
    return dead


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='check that every configured board still responds')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

    if args.check:
        check_boards()
        return 0

    found = scrape_all(progress=lambda d, t, org, n: print(f'  [{d}/{t}] {org}: {n}'))
    for posting in found[:20]:
        print(f"  {posting['country']:16} {posting['company'][:18]:20} {posting['title'][:52]}")
    print(f'\n{len(found)} international CS internships found.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
