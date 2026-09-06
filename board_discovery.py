#!/usr/bin/env python3
"""
Discover company job-board tokens from URLs the tracker already holds.

The international search can only see companies listed in intl_boards.py, and
a hand-curated list decays. But every Greenhouse, Lever or Ashby job URL in the
existing trackers *contains* that company's board token, and a board token is
the key to the company's entire job list - including the international roles
the aggregator repos never carry.

So the search feeds itself: every new US listing scraped today is a candidate
company board to search tomorrow.

Discovered tokens are validated against the live API before being written, and
kept in a separate file from the hand-curated list so the two never get
confused.

    python3 board_discovery.py            # discover, validate, write
    python3 board_discovery.py --dry-run  # report without writing
"""
import argparse
import concurrent.futures as futures
import json
import logging
import os
import sys
from datetime import date

import ats
from intl_boards import BOARDS
from tracker_io import INTL_TRACKER_FILE, SCRAPED_FILE, TRACKER_FILE, read_csv

logger = logging.getLogger(__name__)

DISCOVERED_FILE = 'discovered_boards.json'
MAX_WORKERS = 10

# Sources to mine for job URLs, and the column holding the link in each.
SOURCES = [
    (TRACKER_FILE, 'Link'),
    (SCRAPED_FILE, 'link'),
    (INTL_TRACKER_FILE, 'Link'),
]


def candidates_from_trackers(sources=None):
    """Board tokens appearing in job URLs, mapped to the company name seen."""
    found = {}
    for path, column in (sources or SOURCES):
        for row in read_csv(path):
            link = row.get(column, '')
            detected = ats.detect_ats(link)
            if not detected:
                continue
            platform, org, _ = detected
            if not org:
                continue
            company = row.get('Company') or row.get('company') or org
            found.setdefault((platform, org), company)
    return found


def validate(platform, org):
    """Confirm a board responds and say how many jobs it lists."""
    from intl_sources import fetch_board
    try:
        return len(fetch_board(platform, org, want_content=False))
    except Exception:
        return 0


def discover(dry_run=False, path=DISCOVERED_FILE):
    """Find, validate and record new board tokens."""
    configured = {(platform, org) for platform, org in BOARDS}
    existing = load_discovered(path)
    known = configured | {tuple(key.split(':', 1)) for key in existing}

    candidates = candidates_from_trackers()
    fresh = {key: company for key, company in candidates.items() if key not in known}

    print(f'{len(candidates)} board tokens present in tracker URLs')
    print(f'  {len(candidates) - len(fresh)} already known, {len(fresh)} new to validate')

    if not fresh:
        return existing, []

    validated = []
    with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        jobs = {pool.submit(validate, platform, org): (platform, org)
                for platform, org in fresh}
        for future in futures.as_completed(jobs):
            platform, org = jobs[future]
            count = future.result()
            if count:
                validated.append((platform, org, count))
            else:
                logger.debug('%s:%s returned nothing, skipping', platform, org)

    validated.sort(key=lambda item: -item[2])
    print(f'  {len(validated)} responded with jobs and were added')
    for platform, org, count in validated[:15]:
        print(f'    {platform:11} {org:28} {count:5} jobs  ({fresh[(platform, org)][:24]})')
    if len(validated) > 15:
        print(f'    ... and {len(validated) - 15} more')

    if dry_run:
        print('  dry run; nothing written.')
        return existing, validated

    today = date.today().isoformat()
    for platform, org, count in validated:
        existing[f'{platform}:{org}'] = {
            'company': fresh[(platform, org)],
            'jobs_at_discovery': count,
            'discovered_on': today,
        }
    save_discovered(existing, path)
    print(f'  {path} now holds {len(existing)} discovered boards')
    return existing, validated


def load_discovered(path=DISCOVERED_FILE):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_discovered(data, path=DISCOVERED_FILE):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def all_boards(path=DISCOVERED_FILE):
    """Curated boards plus validated discovered ones, deduplicated.

    This is what the international search should iterate; intl_boards.BOARDS
    alone misses everything discovery has learned.
    """
    seen = set()
    combined = []
    for platform, org in BOARDS:
        if (platform, org) not in seen:
            seen.add((platform, org))
            combined.append((platform, org))
    for key in load_discovered(path):
        platform, _, org = key.partition(':')
        if org and (platform, org) not in seen:
            seen.add((platform, org))
            combined.append((platform, org))
    return combined


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')

    discover(dry_run=args.dry_run)
    print(f'\nTotal boards available to the international search: {len(all_boards())}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
