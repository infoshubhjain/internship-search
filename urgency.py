#!/usr/bin/env python3
"""
Urgency from observed listing lifetimes, not from deadlines nobody publishes.

Trying to scrape application deadlines found exactly zero across 851 listings,
because most employers simply do not publish one. That is not a bug to fix, it
is a fact to design around.

What the tracker does know is when it first saw each listing and when a listing
stopped appearing upstream. That gives an observed lifetime per closed listing,
and from those, a median. A live listing's age against that median is a real
urgency signal - derived from this tracker's own observations rather than a
field that does not exist.

Estimates are labelled by where they came from ('observed' vs 'prior'), because
a median over four listings is not the same thing as a published deadline and
should not be displayed as if it were.

    python3 urgency.py            # show the most time-critical open listings
    python3 urgency.py --stats    # what the lifetime data currently supports
"""
import argparse
import logging
import statistics
import sys
from datetime import date, datetime

from store import DB_PATH, connect
from tracker_io import TRACKER_FILE, normalize_link, read_csv

logger = logging.getLogger(__name__)

# Used until enough listings have been observed closing. Internship postings
# commonly run six to eight weeks; this is a stated assumption, not a measurement.
DEFAULT_LIFETIME_DAYS = 45

# Below this many observations a median is noise, so the prior is used instead.
MIN_OBSERVATIONS = 5

URGENT = 'urgent'
SOON = 'soon'
COMFORTABLE = 'comfortable'
FRESH = 'fresh'


def observed_lifetimes(db_path=DB_PATH):
    """Days each listing stayed live, from listings that have since closed.

    A listing is treated as closed when its status became 'Closed', which the
    merge sets when it disappears upstream. first_seen is never overwritten.
    """
    with connect(db_path) as conn:
        rows = conn.execute("""
            SELECT l.link_key, l.company, l.first_seen, h.changed_at
            FROM listings l
            JOIN status_history h ON h.link_key = l.link_key
            WHERE h.new_status = 'Closed'
        """).fetchall()

    lifetimes = []
    for row in rows:
        try:
            start = datetime.fromisoformat(row['first_seen']).date()
            end = datetime.fromisoformat(row['changed_at']).date()
        except (TypeError, ValueError):
            continue
        days = (end - start).days
        # A listing closed the same day it was first seen was almost certainly
        # already old when the tracker found it; it says nothing about lifetime.
        if days > 0:
            lifetimes.append({'company': row['company'], 'days': days})
    return lifetimes


def lifetime_model(db_path=DB_PATH):
    """Median expected lifetime overall and per company, with provenance."""
    lifetimes = observed_lifetimes(db_path)

    by_company = {}
    for item in lifetimes:
        by_company.setdefault(item['company'], []).append(item['days'])

    if len(lifetimes) >= MIN_OBSERVATIONS:
        overall = statistics.median(item['days'] for item in lifetimes)
        overall_source = f'observed from {len(lifetimes)} closed listings'
    else:
        overall = DEFAULT_LIFETIME_DAYS
        overall_source = (f'prior ({DEFAULT_LIFETIME_DAYS}d); only '
                          f'{len(lifetimes)} closures observed so far')

    company_medians = {
        company: statistics.median(days)
        for company, days in by_company.items() if len(days) >= MIN_OBSERVATIONS
    }

    return {'overall': overall, 'overall_source': overall_source,
            'by_company': company_medians, 'observations': len(lifetimes)}


def first_seen_map(db_path=DB_PATH):
    with connect(db_path) as conn:
        return {row['link_key']: row['first_seen']
                for row in conn.execute('SELECT link_key, first_seen FROM listings')}


def score_urgency(age_days, expected_days):
    """Bucket a listing by how much of its expected life has elapsed."""
    if expected_days <= 0:
        return FRESH, 0.0
    ratio = age_days / expected_days
    if ratio >= 0.9:
        return URGENT, ratio
    if ratio >= 0.6:
        return SOON, ratio
    if ratio >= 0.3:
        return COMFORTABLE, ratio
    return FRESH, ratio


def rank_open_listings(tracker_path=TRACKER_FILE, db_path=DB_PATH, today=None):
    """Open, unapplied listings ordered by how little time is likely left."""
    today = today or date.today()
    model = lifetime_model(db_path)
    seen = first_seen_map(db_path)

    ranked = []
    for row in read_csv(tracker_path):
        if row.get('Status') != 'Not Applied':
            continue

        key = normalize_link(row.get('Link', ''))
        raw = seen.get(key)
        if not raw:
            continue
        try:
            first = datetime.fromisoformat(raw).date()
        except (TypeError, ValueError):
            continue

        age = (today - first).days
        expected = model['by_company'].get(row.get('Company'), model['overall'])
        basis = ('company history' if row.get('Company') in model['by_company']
                 else model['overall_source'])
        level, ratio = score_urgency(age, expected)

        # A published deadline, where one exists, always outranks the estimate.
        deadline = row.get('Application Deadline') or ''
        if deadline:
            try:
                remaining = (date.fromisoformat(deadline[:10]) - today).days
                level = URGENT if remaining <= 7 else SOON if remaining <= 21 else COMFORTABLE
                basis = f'published deadline {deadline}'
                ratio = 1.0 if remaining <= 0 else ratio
            except ValueError:
                pass

        ranked.append({
            'company': row.get('Company', ''), 'role': row.get('Role', ''),
            'priority': row.get('Priority', ''), 'score': int(row.get('Score') or 0),
            'link': row.get('Link', ''), 'age_days': age,
            'expected_days': round(expected), 'level': level,
            'elapsed': round(ratio, 2), 'basis': basis,
        })

    order = {URGENT: 0, SOON: 1, COMFORTABLE: 2, FRESH: 3}
    ranked.sort(key=lambda r: (order[r['level']], r['priority'], -r['score']))
    return ranked, model


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stats', action='store_true')
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)

    ranked, model = rank_open_listings()

    print(f"Lifetime model: {round(model['overall'])} days median "
          f"({model['overall_source']})")
    if model['by_company']:
        print(f"  {len(model['by_company'])} companies have enough history "
              "for their own median")

    if args.stats:
        counts = {}
        for item in ranked:
            counts[item['level']] = counts.get(item['level'], 0) + 1
        print(f'\n{len(ranked)} open listings by urgency:')
        for level in (URGENT, SOON, COMFORTABLE, FRESH):
            if counts.get(level):
                print(f'  {level:12} {counts[level]}')
        return 0

    urgent = [r for r in ranked if r['level'] in (URGENT, SOON)][:args.limit]
    if not urgent:
        print('\nNothing is time-critical yet. Every open listing is recently seen.')
        return 0

    print('\nMost time-critical open listings:')
    for item in urgent:
        print(f"  [{item['level']:>10}] P{item['priority']} {item['score']:>3}  "
              f"{item['company'][:22]:24} {item['role'][:38]:40} "
              f"seen {item['age_days']}d ago  ({item['basis']})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
