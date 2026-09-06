#!/usr/bin/env python3
"""
Check whether the scores actually predict outcomes.

The score weights in scoring.py and intl_scoring.py are my judgment, not
measurements. Judgment is a fine starting point and a bad stopping point: if
priority 1 and priority 3 produce the same response rate, the ranking is
decoration and you are spending your best hours on the wrong listings.

status_history records every application and every outcome, so the loop can be
closed. This reports response rate by score band and says plainly whether the
data supports any conclusion yet.

    python3 calibrate.py

It deliberately does not auto-tune the weights. With a few dozen applications,
any fit would be noise; the useful output is the evidence, and a clear
statement of how much more is needed before it means anything.
"""
import argparse
import logging
import sys
from collections import defaultdict

from store import DB_PATH, connect

logger = logging.getLogger(__name__)

# A positive response: the employer engaged rather than filtered you out.
POSITIVE = {'Interviewing', 'Offer'}
NEGATIVE = {'Rejected'}
TERMINAL = POSITIVE | NEGATIVE

# Below this, per-band rates are noise. Binomial spread on 10 samples is huge.
MIN_PER_BAND = 10
MIN_TOTAL = 30

BANDS = [(0, 30, '0-29'), (30, 45, '30-44'), (45, 60, '45-59'),
         (60, 75, '60-74'), (75, 101, '75-100')]


def band_for(score):
    for low, high, label in BANDS:
        if low <= score < high:
            return label
    return BANDS[-1][2]


def applications(db_path=DB_PATH):
    """Every application, with its score at the time and its outcome so far."""
    with connect(db_path) as conn:
        applied = conn.execute("""
            SELECT h.link_key, MIN(h.changed_at) AS applied_at
            FROM status_history h
            WHERE h.new_status = 'Applied'
            GROUP BY h.link_key
        """).fetchall()

        outcomes = defaultdict(list)
        for row in conn.execute("""
            SELECT link_key, new_status, changed_at FROM status_history
            WHERE new_status IN ('Interviewing', 'Offer', 'Rejected')
            ORDER BY changed_at
        """):
            outcomes[row['link_key']].append((row['new_status'], row['changed_at']))

        meta = {r['link_key']: r for r in conn.execute(
            'SELECT link_key, company, role, score, priority, category FROM listings')}

    records = []
    for row in applied:
        key = row['link_key']
        info = meta.get(key)
        if not info:
            continue
        later = [o for o in outcomes.get(key, []) if o[1] >= row['applied_at']]
        outcome = later[-1][0] if later else 'Pending'
        records.append({
            'link_key': key, 'company': info['company'], 'role': info['role'],
            'score': int(info['score'] or 0), 'priority': info['priority'],
            'category': info['category'], 'applied_at': row['applied_at'],
            'outcome': outcome,
        })
    return records


def rates_by(records, key_fn):
    """Response rate grouped by some attribute of the application."""
    groups = defaultdict(lambda: {'applied': 0, 'positive': 0, 'negative': 0, 'pending': 0})
    for record in records:
        bucket = groups[key_fn(record)]
        bucket['applied'] += 1
        if record['outcome'] in POSITIVE:
            bucket['positive'] += 1
        elif record['outcome'] in NEGATIVE:
            bucket['negative'] += 1
        else:
            bucket['pending'] += 1

    for bucket in groups.values():
        decided = bucket['positive'] + bucket['negative']
        # Rate over decided applications only: pending ones have not answered
        # yet, and counting them as rejections understates early results.
        bucket['decided'] = decided
        bucket['rate'] = (bucket['positive'] / decided) if decided else None
    return dict(groups)


def report(db_path=DB_PATH):
    records = applications(db_path)
    total = len(records)

    print(f'Applications recorded: {total}')
    if total < MIN_TOTAL:
        print(f'\nNot enough data to calibrate. Need about {MIN_TOTAL} '
              f'applications with outcomes before any per-band rate means '
              f'anything; you have {total}.')
        print('Nothing is wrong - the scores are still my judgment, unverified.')
        print('Keep applying and marking outcomes, then re-run this.')
        return records, None

    decided = sum(1 for r in records if r['outcome'] in TERMINAL)
    print(f'  decided: {decided}   pending: {total - decided}')

    by_band = rates_by(records, lambda r: band_for(r['score']))
    print('\nResponse rate by score band:')
    usable = []
    for _, _, label in BANDS:
        bucket = by_band.get(label)
        if not bucket:
            continue
        if bucket['decided'] >= MIN_PER_BAND:
            print(f"  {label:>7}  {bucket['rate']:.0%}  "
                  f"({bucket['positive']}/{bucket['decided']} decided)")
            usable.append((label, bucket['rate']))
        else:
            print(f"  {label:>7}  -     ({bucket['decided']} decided, "
                  f"need {MIN_PER_BAND})")

    by_priority = rates_by(records, lambda r: r['priority'])
    print('\nResponse rate by priority:')
    for priority in sorted(by_priority):
        bucket = by_priority[priority]
        rate = f"{bucket['rate']:.0%}" if bucket['decided'] >= MIN_PER_BAND else '-'
        print(f"  P{priority}  {rate:>5}  ({bucket['decided']} decided)")

    by_category = rates_by(records, lambda r: r['category'] or 'unknown')
    ranked = [(c, b) for c, b in by_category.items() if b['decided'] >= MIN_PER_BAND]
    if ranked:
        print('\nResponse rate by role category:')
        for category, bucket in sorted(ranked, key=lambda i: -(i[1]['rate'] or 0)):
            print(f"  {category[:32]:34} {bucket['rate']:.0%}  ({bucket['decided']})")

    verdict = None
    if len(usable) >= 2:
        top = max(usable, key=lambda i: i[1])
        bottom = min(usable, key=lambda i: i[1])
        spread = top[1] - bottom[1]
        print(f'\nSpread between best and worst usable band: {spread:.0%}')
        if spread < 0.05:
            verdict = 'flat'
            print('  The ranking is not discriminating. Scores are not predicting '
                  'outcomes,\n  so reweighting or a different signal is warranted.')
        elif top[0] < bottom[0]:
            verdict = 'inverted'
            print('  Lower-scored listings are responding better. The weights are '
                  'backwards\n  for your situation - worth inspecting before trusting '
                  'the ranking.')
        else:
            verdict = 'working'
            print('  Higher scores are responding better. The ranking is earning '
                  'its keep.')
    return records, verdict


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    report()
    return 0


if __name__ == '__main__':
    sys.exit(main())
