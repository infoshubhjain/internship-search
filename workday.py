#!/usr/bin/env python3
"""
Workday support - the largest gap in coverage.

Workday is the dominant enterprise ATS, so it is where the large, formal
employers live: the banks, the F500, the ones most likely to have an
established visa process. Roughly 240 URLs in the trackers point at it, and
none of them could be enriched or searched before this.

Every Workday tenant exposes the same unauthenticated JSON API that its own
career site calls:

    POST /wday/cxs/<tenant>/<site>/jobs      {"limit","offset","searchText"}
    GET  /wday/cxs/<tenant>/<site><externalPath>

Tenants are discovered from URLs already in the trackers rather than curated,
the same self-feeding approach as board_discovery.

    python3 workday.py --discover   # find tenants in tracker URLs
    python3 workday.py --check      # confirm discovered tenants respond
"""
import argparse
import concurrent.futures as futures
import json
import logging
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

TENANTS_FILE = 'workday_tenants.json'
TIMEOUT = 25
PAGE_SIZE = 20
# Measured on four tenants: one term over two pages returned 42 postings in
# 20s; five terms over five pages returned 45 in 76s. Nearly four times the
# requests for 7% more results, so the cheap setting is the right default.
MAX_PAGES = 2
SEARCH_TERMS = ['intern']

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

# /en-US/<site>/job/... - the locale segment is optional and must not be
# mistaken for the site name.
# Region case varies by tenant ("en-US" and "en-us" both occur), so match
# case-insensitively or the locale gets mistaken for the site name.
_LOCALE_RE = re.compile(r'^[a-z]{2}([-_][a-z]{2})?$', re.I)


def parse_url(url):
    """(tenant, datacenter, site) from a myworkdayjobs URL, or None."""
    if not url or 'myworkdayjobs.com' not in url:
        return None
    parsed = urlparse(url)
    host_parts = parsed.netloc.split('.')
    if len(host_parts) < 3:
        return None
    tenant, datacenter = host_parts[0], host_parts[1]

    parts = [p for p in parsed.path.split('/') if p]
    if not parts:
        return None
    if _LOCALE_RE.match(parts[0]) and len(parts) > 1:
        parts = parts[1:]
    site = parts[0]
    if site in ('job', 'details'):
        return None
    return (tenant, datacenter, site)


def discover_tenants(sources=None, path=TENANTS_FILE):
    """Find Workday tenants in tracker URLs and record them."""
    from tracker_io import INTL_TRACKER_FILE, SCRAPED_FILE, TRACKER_FILE, read_csv

    sources = sources or [(TRACKER_FILE, 'Link'), (SCRAPED_FILE, 'link'),
                          (INTL_TRACKER_FILE, 'Link')]
    found = {}
    for csv_path, column in sources:
        for row in read_csv(csv_path):
            parsed = parse_url(row.get(column, ''))
            if not parsed:
                continue
            company = row.get('Company') or row.get('company') or parsed[0]
            # Sites differ only by case on some tenants; keep the first seen.
            key = f'{parsed[0]}|{parsed[1]}|{parsed[2]}'
            found.setdefault(key.lower(), {'tenant': parsed[0], 'datacenter': parsed[1],
                                           'site': parsed[2], 'company': company})

    existing = load_tenants(path)
    added = {k: v for k, v in found.items() if k not in existing}
    existing.update(added)
    save_tenants(existing, path)
    return existing, added


def load_tenants(path=TENANTS_FILE):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_tenants(data, path=TENANTS_FILE):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def search_jobs(tenant, datacenter, site, term='intern', max_pages=MAX_PAGES):
    """Postings matching a search term. [] on any failure."""
    url = f'https://{tenant}.{datacenter}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs'
    out = []
    for page in range(max_pages):
        payload = {'limit': PAGE_SIZE, 'offset': page * PAGE_SIZE,
                   'searchText': term, 'appliedFacets': {}}
        try:
            response = requests.post(url, headers=HEADERS, json=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            logger.debug('workday %s/%s failed: %s', tenant, site, e)
            return out
        if response.status_code != 200:
            return out
        try:
            data = response.json()
        except ValueError:
            return out

        postings = data.get('jobPostings') or []
        out.extend(postings)
        if len(postings) < PAGE_SIZE:
            break
        if page + 1 < max_pages:
            time.sleep(0.2)
    return out


def fetch_detail(tenant, datacenter, site, external_path):
    """Full posting detail: description, structured location, country."""
    url = (f'https://{tenant}.{datacenter}.myworkdayjobs.com/wday/cxs/'
           f'{tenant}/{site}{external_path}')
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException:
        return {}
    if response.status_code != 200:
        return {}
    try:
        return (response.json() or {}).get('jobPostingInfo', {}) or {}
    except ValueError:
        return {}


def job_url(tenant, datacenter, site, external_path):
    return f'https://{tenant}.{datacenter}.myworkdayjobs.com/{site}{external_path}'


def normalize(posting, detail, entry):
    """Normalize to the shape intl_sources uses for every other board."""
    from ats import _strip_html

    tenant, datacenter = entry['tenant'], entry['datacenter']
    site, company = entry['site'], entry.get('company') or entry['tenant']
    external_path = posting.get('externalPath', '')

    location = (detail.get('location')
                or posting.get('locationsText')
                or '')
    # "2 Locations" is a rollup, not a place - the detail record is better.
    if isinstance(location, str) and re.fullmatch(r'\d+ Locations?', location.strip()):
        location = detail.get('location') or ''

    return {
        'company': company,
        'title': posting.get('title', '') or detail.get('title', ''),
        'location': location,
        'link': job_url(tenant, datacenter, site, external_path),
        'description': _strip_html(detail.get('jobDescription', '')),
        'posted_at': '',
        'employment_type': detail.get('timeType', '') or '',
        'country_hint': (detail.get('country') or {}).get('descriptor', '')
                        if isinstance(detail.get('country'), dict) else '',
        'salary': '',
        'external_id': detail.get('jobReqId') or external_path,
        'source': f'workday:{tenant}',
    }


def scrape_tenant(entry, terms=SEARCH_TERMS, want_detail=True, detail_cap=25):
    """Search one tenant for internships and return normalized postings.

    Details are fetched only for postings whose title survives the internship
    filter, because a detail call per posting across 96 tenants would be
    thousands of requests for jobs that get discarded anyway.
    """
    from intl_sources import looks_like_internship
    from roles import classify_role

    tenant, datacenter, site = entry['tenant'], entry['datacenter'], entry['site']

    seen_paths = {}
    for term in terms:
        for posting in search_jobs(tenant, datacenter, site, term):
            path = posting.get('externalPath')
            if path and path not in seen_paths:
                seen_paths[path] = posting

    interesting = [p for p in seen_paths.values()
                   if looks_like_internship(p.get('title', ''))
                   and classify_role(p.get('title', ''))]

    out = []
    for posting in interesting[:detail_cap]:
        detail = fetch_detail(tenant, datacenter, site,
                              posting['externalPath']) if want_detail else {}
        out.append(normalize(posting, detail, entry))
        if want_detail:
            time.sleep(0.15)
    return out


def scrape_all(tenants=None, max_workers=6, progress=None):
    """Search every discovered tenant for internships."""
    tenants = tenants or load_tenants()
    entries = list(tenants.values())
    results, done = [], 0

    with futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        jobs = {pool.submit(scrape_tenant, entry): entry for entry in entries}
        for future in futures.as_completed(jobs):
            entry = jobs[future]
            try:
                postings = future.result()
            except Exception as e:
                logger.debug('workday %s failed: %s', entry['tenant'], e)
                postings = []
            results.extend(postings)
            done += 1
            if progress:
                progress(done, len(entries), entry['tenant'], len(postings))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--discover', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

    if args.discover:
        all_tenants, added = discover_tenants()
        print(f'{len(all_tenants)} Workday tenants known ({len(added)} new)')
        for entry in list(added.values())[:15]:
            print(f"    {entry['tenant']:22} {entry['site'][:30]:32} ({entry['company'][:24]})")
        return 0

    if args.check:
        tenants = load_tenants()
        alive = 0
        for key, entry in sorted(tenants.items()):
            count = len(search_jobs(entry['tenant'], entry['datacenter'],
                                    entry['site'], 'intern', max_pages=1))
            alive += bool(count)
            print(f"  {'ok  ' if count else 'DEAD'} {entry['tenant']:22} {count}")
        print(f'\n{alive}/{len(tenants)} tenants responding.')
        return 0

    postings = scrape_all(progress=lambda d, t, name, n:
                          print(f'  [{d}/{t}] {name}: {n}', end='\r', flush=True))
    print(' ' * 70, end='\r')
    print(f'{len(postings)} Workday internship postings found.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
