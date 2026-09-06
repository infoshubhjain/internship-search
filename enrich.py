#!/usr/bin/env python3
"""
Enrich the tracker from applicant tracking system APIs.

Adds the three things the aggregator repos never carry:
  - the real application deadline (Greenhouse publishes it; others state it in
    the description, which ats.extract_deadline finds)
  - the posted salary range
  - whether the posting still exists, so dead listings leave the apply queue

Deadlines are a user-editable column, so a deadline the user typed is never
overwritten - only empty ones are filled.
"""
import argparse
import logging
import sys

import ats
from tracker_io import TRACKER_FIELDNAMES, TRACKER_FILE, read_csv, write_csv

logger = logging.getLogger(__name__)

# Statuses that mean the user has acted. A dead posting must not overwrite
# these - an application already submitted is still part of the history.
ACTIVE_STATUSES = {'Applied', 'Interviewing', 'Offer', 'Rejected'}


def format_salary(result):
    """Human-readable salary from an ATS result, or '' when not disclosed."""
    low, high = result.get('salary_min'), result.get('salary_max')
    if not low and not high:
        return ''
    currency = result.get('currency') or ''
    if low and high and low != high:
        amount = f'{low:,.0f}-{high:,.0f}'
    else:
        amount = f'{(low or high):,.0f}'
    return f'{amount} {currency}'.strip()


def enrich_tracker(path=TRACKER_FILE, limit=200, dry_run=False):
    """Fetch ATS data for tracker rows and write back what it finds."""
    rows = read_csv(path)
    if not rows:
        print(f'{path} is empty; nothing to enrich.')
        return None

    # Prefer the listings the user is most likely to act on, and skip rows
    # already closed - spending the request budget on dead rows is waste.
    candidates = [
        r for r in rows
        if r.get('Link') and r.get('Status') != 'Closed' and ats.detect_ats(r['Link'])
    ]
    candidates.sort(key=lambda r: (r.get('Priority') or '9', -int(r.get('Score') or 0)))

    print(f'{len(candidates)} rows are on a supported ATS; fetching up to {limit}.')
    results = ats.enrich_urls(
        [r['Link'] for r in candidates], limit=limit,
        progress=lambda n: print(f'  fetched {n}...'),
    )

    stats = {'deadlines': 0, 'salaries': 0, 'closed': 0, 'locations': 0}

    for row in rows:
        result = results.get(row.get('Link'))
        if not result:
            continue

        if result.get('alive') is False and row.get('Status') not in ACTIVE_STATUSES:
            if row.get('Status') != 'Closed':
                row['Status'] = 'Closed'
                row['Notes'] = row.get('Notes') or 'Posting no longer live (ATS returned 404)'
                stats['closed'] += 1
            continue

        # Application Deadline is user-editable; only fill a blank one.
        if result.get('deadline') and not row.get('Application Deadline'):
            row['Application Deadline'] = result['deadline']
            stats['deadlines'] += 1

        salary = format_salary(result)
        if salary and row.get('Salary') != salary:
            row['Salary'] = salary
            stats['salaries'] += 1

        # A vague aggregator location loses to the employer's own value.
        location = result.get('location')
        if location and len(location) > len(row.get('Location') or ''):
            if row.get('Location', '').strip().lower() in ('', 'multiple', 'various'):
                row['Location'] = location
                stats['locations'] += 1

    if dry_run:
        print('dry run; nothing written.')
    else:
        write_csv(path, rows, TRACKER_FIELDNAMES)

    print(f"Enriched: {stats['deadlines']} deadlines, {stats['salaries']} salaries, "
          f"{stats['locations']} locations, {stats['closed']} closed as dead.")
    return stats


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=200,
                        help='maximum ATS requests this run (default 200)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    return 0 if enrich_tracker(limit=args.limit, dry_run=args.dry_run) is not None else 1


if __name__ == '__main__':
    sys.exit(main())
