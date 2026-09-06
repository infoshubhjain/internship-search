#!/usr/bin/env python3
"""
Real H-1B sponsorship evidence from USCIS, replacing hand-maintained guesses.

`sponsorship_database.py` is a hand-written dict. It is small, it is stale the
day it is written, and it was the source of two bad bugs (the 'x' key claiming
RTX and SpaceX; defence contractors marked as sponsoring). Two thirds of the
tracker resolved to "unknown".

USCIS publishes, per employer per fiscal year, how many H-1B petitions were
approved and denied. That is not a guess about policy - it is a count of people
the employer actually sponsored. This module downloads that file once, reduces
it to a compact lookup, and commits the derived table so the repo and CI do not
depend on the download.

    python3 h1b_data.py --refresh    # re-download and rebuild the lookup
    python3 h1b_data.py              # show what is in the current lookup

Note the limits: this covers H-1B, not CPT/OPT. A company that sponsors H-1B is
very likely to be comfortable hosting an F-1 intern on CPT, but the inference
runs one way - a company with no H-1B filings may still take CPT interns, so
zero filings lowers confidence rather than ruling a company out.
"""
import argparse
import csv
import gzip
import io
import json
import logging
import os
import re
import sys

import requests

logger = logging.getLogger(__name__)

LOOKUP_FILE = 'h1b_sponsors.json.gz'
SOURCE_URL = 'https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-{year}.csv'
# USCIS publishes about two years behind. Probe downward from here.
NEWEST_PROBE_YEAR = 2026
OLDEST_USEFUL_YEAR = 2019
USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36')

# Legal-entity noise that stops "GOOGLE LLC" matching "Google".
_SUFFIXES = re.compile(
    r'\b(inc|llc|ltd|limited|corp|corporation|co|plc|group|holdings|holding|'
    r'technologies|technology|labs|laboratories|systems|services|solutions|'
    r'usa|us|america|american|na|the|dba|lp|llp|gmbh|sa|nv|ag|pte|pty|bv)\b')

_cache = None


def normalize_employer(name):
    """Reduce an employer name to a comparable key."""
    name = (name or '').lower().strip()
    name = re.sub(r"[(),.\-/&'\"]", ' ', name)
    name = _SUFFIXES.sub(' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def _fetch_year(year):
    response = requests.get(SOURCE_URL.format(year=year),
                            headers={'User-Agent': USER_AGENT}, timeout=300)
    if response.status_code != 200:
        return None
    return response.text


def build_lookup(path=LOOKUP_FILE):
    """Download the newest USCIS export and write the compact lookup."""
    text = year = None
    for candidate in range(NEWEST_PROBE_YEAR, OLDEST_USEFUL_YEAR - 1, -1):
        logger.info('trying USCIS export for FY%s', candidate)
        text = _fetch_year(candidate)
        if text:
            year = candidate
            break

    if not text:
        raise RuntimeError('no USCIS H-1B export could be downloaded')

    totals = {}
    for row in csv.DictReader(io.StringIO(text)):
        key = normalize_employer(row.get('Employer'))
        if not key:
            continue
        approvals = _int(row.get('Initial Approval')) + _int(row.get('Continuing Approval'))
        denials = _int(row.get('Initial Denial')) + _int(row.get('Continuing Denial'))
        entry = totals.setdefault(key, [0, 0])
        entry[0] += approvals
        entry[1] += denials

    payload = {'fiscal_year': year, 'source': SOURCE_URL.format(year=year),
               'employers': totals}
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        json.dump(payload, f, separators=(',', ':'))

    logger.info('wrote %s with %d employers (FY%s)', path, len(totals), year)
    return payload


def newest_available_year():
    """Newest fiscal year USCIS is currently publishing, or None if unreachable."""
    for candidate in range(NEWEST_PROBE_YEAR, OLDEST_USEFUL_YEAR - 1, -1):
        try:
            response = requests.head(SOURCE_URL.format(year=candidate),
                                     headers={'User-Agent': USER_AGENT},
                                     timeout=30, allow_redirects=True)
        except requests.RequestException:
            return None
        if response.status_code == 200:
            return candidate
    return None


def refresh_if_stale(path=LOOKUP_FILE):
    """Rebuild only when USCIS has published a newer year.

    The export is ~2 MB and changes once a year, so re-downloading it on every
    daily run would be pure waste. A HEAD request per candidate year is cheap
    enough to check every run.
    """
    current = load_lookup(path)
    newest = newest_available_year()

    if newest is None:
        logger.info('USCIS unreachable; keeping existing H-1B lookup')
        return False
    if current and current.get('fiscal_year', 0) >= newest:
        logger.info('H-1B lookup already at FY%s', current['fiscal_year'])
        return False

    logger.info('newer USCIS export available (FY%s); rebuilding', newest)
    global _cache
    _cache = None
    build_lookup(path)
    return True


def load_lookup(path=LOOKUP_FILE):
    """Load the committed lookup. Returns None when it has not been built."""
    global _cache
    if _cache is not None:
        return _cache
    if not os.path.exists(path):
        return None
    try:
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            _cache = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning('could not read %s: %s', path, e)
        return None
    return _cache


def lookup(company, path=LOOKUP_FILE):
    """H-1B record for a company, or None if it does not appear.

    Returns {'approvals', 'denials', 'matched_as', 'fiscal_year'}. Matching is
    exact on the normalized name first, then a two-word prefix, which catches
    "Amazon" against "AMAZON COM SERVICES" without letting "Apex" match
    "Apex Systems Staffing".
    """
    data = load_lookup(path)
    if not data:
        return None

    employers = data['employers']
    key = normalize_employer(company)
    if not key:
        return None

    hit = employers.get(key)
    matched_as = key

    if hit is None:
        words = key.split()
        # Require at least two words for a prefix match; one-word prefixes
        # match far too much ("apex" -> "apex systems staffing").
        if len(words) >= 2:
            prefix = ' '.join(words[:2])
            candidates = [(name, counts) for name, counts in employers.items()
                          if name.startswith(prefix)]
            if candidates:
                # Prefer the entity with the most approvals: for a company with
                # many legal entities that is the operating one.
                matched_as, hit = max(candidates, key=lambda item: item[1][0])
        elif len(words) == 1 and len(words[0]) >= 6:
            # A single distinctive word ("cloudflare") may still be exact-only.
            hit = employers.get(words[0])

    if hit is None:
        return None

    return {'approvals': hit[0], 'denials': hit[1],
            'matched_as': matched_as, 'fiscal_year': data['fiscal_year']}


def sponsorship_tier(company, path=LOOKUP_FILE):
    """Map H-1B filing volume to the tier scale used across the tracker.

    Volume is a proxy for how routine sponsorship is at the company, not a
    promise about any one role. Absence is returned as None, not tier 5, so the
    caller can tell "no H-1B record" apart from "we checked and it is unknown".
    """
    record = lookup(company, path)
    if record is None:
        return None, None

    approvals = record['approvals']
    if approvals >= 100:
        tier = 1
    elif approvals >= 25:
        tier = 2
    elif approvals >= 5:
        tier = 3
    elif approvals >= 1:
        tier = 4
    else:
        # Appears in the data but with no approvals - filings were denied or
        # withdrawn. That is weaker than never having filed.
        return 5, record

    return tier, record


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true',
                        help='re-download from USCIS and rebuild the lookup')
    parser.add_argument('--refresh-if-stale', action='store_true',
                        help='rebuild only when USCIS has published a newer year')
    parser.add_argument('--check', nargs='*', metavar='COMPANY',
                        help='look up specific companies')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

    if args.refresh:
        build_lookup()
    elif args.refresh_if_stale:
        refresh_if_stale()

    data = load_lookup()
    if not data:
        print(f'{LOOKUP_FILE} not built yet. Run: python3 h1b_data.py --refresh')
        return 1

    print(f"USCIS H-1B data FY{data['fiscal_year']}: {len(data['employers'])} employers")

    for company in (args.check or ['Google', 'Stripe', 'RTX', 'Nobody Inc']):
        tier, record = sponsorship_tier(company)
        if record:
            print(f"  {company:24} tier {tier}  "
                  f"{record['approvals']} approvals / {record['denials']} denials "
                  f"(matched '{record['matched_as']}')")
        else:
            print(f'  {company:24} no H-1B record')
    return 0


if __name__ == '__main__':
    sys.exit(main())
