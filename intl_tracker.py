#!/usr/bin/env python3
"""
The international internship agent.

One run: fetch every configured company board, keep the CS internships outside
the United States, work out whether the candidate could legally take each one,
score the fit out of 100, merge into the tracker without touching anything the
user has entered, and write a prioritized report.

Run it on a schedule and it becomes the "continuous monitoring" the brief asks
for: each run diffs against the previous tracker, so newly opened roles are
reported as new rather than lost in a list of 60.

    python3 intl_tracker.py            # full run
    python3 intl_tracker.py --report   # re-render the report from the tracker
"""
import argparse
import logging
import re
import sys
from datetime import date

import intl_scoring
import visa as visa_mod
from geo import country_tier, is_remote
from intl_sources import scrape_all
from tracker_io import (
    INTL_FIELDNAMES, INTL_REPORT_FILE, INTL_TRACKER_FILE, INTL_USER_FIELDS,
    listing_key, read_csv, write_csv,
)

logger = logging.getLogger(__name__)

# The four buckets the brief asks the results to be organized into.
BUCKET_APPLY = '🔥 Apply Immediately'
BUCKET_INVESTIGATE = '👀 Investigate Further'
BUCKET_MONITOR = '📅 Monitor for Opening'
BUCKET_BARRIER = '⚠️ Work Authorization Barrier'
BUCKET_ORDER = [BUCKET_APPLY, BUCKET_INVESTIGATE, BUCKET_MONITOR, BUCKET_BARRIER]

# Summer 2027 in the northern hemisphere. Used only as the default expectation
# when a posting does not state its dates.
DEFAULT_START = '2027-05'
DEFAULT_END = '2027-08'

_PAID_HINTS = re.compile(
    r'\b(paid internship|competitive (?:salary|compensation|pay)|'
    r'salary|stipend|hourly rate|per hour|per month|per annum|remunerat)', re.I)
_UNPAID_HINTS = re.compile(r'\b(unpaid|voluntary|volunteer basis|no compensation)\b', re.I)
_DURATION_RE = re.compile(r'\b(\d{1,2})\s*(?:-|to|–)\s*(\d{1,2})\s*(week|month)s?\b', re.I)
_SINGLE_DURATION_RE = re.compile(r'\b(\d{1,2})\s*(week|month)s?\b', re.I)


def city_from(location, country):
    """First segment of a location string, minus the country name."""
    if not location:
        return ''
    first = re.split(r'[,;/|]', str(location))[0].strip()
    if country and first.lower() == country.lower():
        return ''
    return first


def detect_paid(description, salary):
    """True / False / None. None means not disclosed, which is not 'unpaid'."""
    if salary:
        return True
    text = description or ''
    if _UNPAID_HINTS.search(text):
        return False
    if _PAID_HINTS.search(text):
        return True
    return None


def detect_duration(description):
    match = _DURATION_RE.search(description or '')
    if match:
        return f'{match.group(1)}-{match.group(2)} {match.group(3)}s'
    match = _SINGLE_DURATION_RE.search(description or '')
    if match:
        return f'{match.group(1)} {match.group(2)}s'
    return ''


def detect_benefit(description, *keywords):
    text = (description or '').lower()
    return 'Yes' if any(word in text for word in keywords) else 'Unclear'


def application_status(posting):
    """Open / Not Yet Open / Unknown for a live board posting.

    A posting returned by a board API is by definition currently listed, so
    'Open' is a statement about the board, not a guess.
    """
    if posting.get('season') == 'summer-2027':
        return 'Open'
    return 'Open (cycle unconfirmed)'


def bucket_for(row):
    """Sort a scored row into one of the brief's four presentation buckets."""
    category = row['Visa Category']
    score = int(row['Match Score'] or 0)

    if category == visa_mod.CATEGORY_C:
        return BUCKET_BARRIER
    if row['Application Status'].startswith('Open') and category == visa_mod.CATEGORY_A and score >= 65:
        return BUCKET_APPLY
    if category == visa_mod.CATEGORY_B and score >= 55:
        return BUCKET_INVESTIGATE
    if score >= 65:
        return BUCKET_APPLY
    return BUCKET_MONITOR


def build_row(posting, today=None):
    """Turn one filtered posting into a full tracker row."""
    today = today or date.today()
    description = posting.get('description', '')
    country = posting.get('country', '')
    company = posting.get('company', '')
    title = posting.get('title', '')

    verdict = visa_mod.classify(description, company, country, title)
    english = visa_mod.english_working_language(description, country)
    salary = posting.get('salary', '')
    paid = detect_paid(description, salary)
    season = posting.get('season', 'undated')

    score, breakdown, barriers = intl_scoring.score(
        role=title, country=country, visa_category=verdict['category'],
        paid=paid, company=company, employment_type=posting.get('employment_type', ''),
        english=english, is_2027=(season == 'summer-2027'),
    )

    currency = ''
    match = re.search(r'\b([A-Z]{3})\b', salary)
    if match:
        currency = match.group(1)

    row = {field: '' for field in INTL_FIELDNAMES}
    row.update({
        'Company': company,
        'Title': title,
        'Country': country,
        'City': city_from(posting.get('location', ''), country),
        'Region Tier': str(country_tier(country) or ''),
        'Category': posting.get('category', ''),
        'Employment Type': posting.get('employment_type', '') or 'Internship',
        'Duration': detect_duration(description),
        'Expected Start': DEFAULT_START,
        'Expected End': DEFAULT_END,

        'Application Status': application_status(posting),
        'Application Deadline': '',
        'Link': posting.get('link', ''),
        'Source': posting.get('source', ''),
        'External ID': posting.get('external_id', ''),
        'Date Posted': posting.get('posted_at', ''),
        'Last Verified': today.isoformat(),

        # The candidate is an undergraduate at a US university, so these are
        # about whether the posting rules that out, not whether it says yes.
        'Undergrad Eligible': 'No' if 'phd' in title.lower() else 'Yes'
                              if 'undergrad' in description.lower() else 'Unclear',
        'Foreign University Eligible':
            'No' if re.search(r'enrolled at (?:a|an) \w+ universit', description, re.I)
            else 'Unclear',
        'International Eligible': {'A': 'Yes', 'B': 'Unclear', 'C': 'No'}[verdict['category']],
        'Work Auth Required': {'A': 'No', 'B': 'Unclear', 'C': 'Yes'}[verdict['category']],
        'Visa Sponsorship': {'A': 'Yes', 'B': 'Unclear', 'C': 'No'}[verdict['category']],
        'Local Language Required': 'Yes' if english == 'No' else 'No' if english == 'Yes' else 'Unclear',
        'English Environment': english,

        'Visa Category': verdict['category'],
        'Visa Explanation': verdict['reason'],
        'Visa Route': verdict['visa_route'],
        'Visa Evidence': verdict['evidence'][:200],

        'Paid': {True: 'Yes', False: 'No', None: 'Not publicly disclosed'}[paid],
        'Compensation': salary,
        'Currency': currency,
        'Housing': detect_benefit(description, 'housing', 'accommodation'),
        'Relocation': detect_benefit(description, 'relocation', 'relocate'),

        'Match Score': str(score),
        'Score Breakdown': '; '.join(f'{k} {v}' for k, v in breakdown.items()),
        'Why It Fits': why_it_fits(posting, verdict, paid, score),
        'Barriers': '; '.join(barriers),

        'Status': 'Not Applied',
    })
    row['Bucket'] = bucket_for(row)
    return row


def why_it_fits(posting, verdict, paid, score):
    """One line explaining the score, in the terms the brief asks for."""
    bits = [f"{posting.get('category', 'technical')} role in {posting.get('country', 'unknown')}"]
    if verdict['category'] == visa_mod.CATEGORY_A:
        bits.append('employer states international support')
    elif verdict['visa_route']:
        bits.append(f"visa route exists ({verdict['visa_route'].split(';')[0]})")
    if paid is True:
        bits.append('paid')
    if posting.get('season') == 'summer-2027':
        bits.append('explicitly Summer 2027')
    if is_remote(posting.get('location', '')):
        bits.append('remote-friendly')
    return '; '.join(bits)


def merge_rows(existing_rows, new_rows, today=None):
    """Merge scraped rows into the tracker, preserving user-entered columns.

    Same contract as the domestic merge: a listing the user has acted on is
    never overwritten or deleted, and one that has disappeared upstream is
    marked closed rather than removed.
    """
    today = today or date.today()
    by_link = {}
    unlinked = []
    for row in existing_rows:
        key = listing_key(row)
        if key:
            by_link.setdefault(key, row)
        else:
            unlinked.append(row)

    merged, seen, added = [], set(), []
    for candidate in new_rows:
        key = listing_key(candidate)
        if key and key in seen:
            continue
        if key:
            seen.add(key)

        existing = by_link.get(key)
        if existing:
            row = dict(existing)
            for field in INTL_FIELDNAMES:
                if field in INTL_USER_FIELDS:
                    continue
                if candidate.get(field):
                    row[field] = candidate[field]
            if row.get('Status') == 'Closed':
                row['Status'] = 'Not Applied'
            merged.append(row)
        else:
            merged.append(candidate)
            added.append(candidate)

    closed = 0
    for key, row in by_link.items():
        if key in seen:
            continue
        row = dict(row)
        if row.get('Status') in ('Not Applied', '', None):
            row['Status'] = 'Closed'
            row['Application Status'] = 'Closed'
            row['Notes'] = row.get('Notes') or 'No longer listed on the company board'
            closed += 1
        merged.append(row)
    merged.extend(unlinked)

    merged.sort(key=lambda r: (BUCKET_ORDER.index(r['Bucket']) if r.get('Bucket') in BUCKET_ORDER else 9,
                               -int(r.get('Match Score') or 0),
                               r.get('Company') or ''))
    return merged, added, closed


def render_report(rows, added=(), path=INTL_REPORT_FILE, today=None):
    """Write the prioritized markdown report."""
    today = today or date.today()
    live = [r for r in rows if r.get('Status') != 'Closed']
    added_keys = {listing_key(r) for r in added}

    lines = [
        '# International Summer 2027 Internships',
        '',
        f'_Generated {today.isoformat()} · {len(live)} live opportunities '
        f'from {len({r["Source"].split(":")[1] for r in live if ":" in r.get("Source", "")})} '
        'company boards_',
        '',
        'Candidate: UIUC CS sophomore, graduating May 2028, Indian citizen on F-1 in the US.',
        'Scope: paid Summer 2027 internships outside the United States.',
        '',
        '**How to read this.** Visa category A means the employer states it supports '
        'international applicants; B means it says nothing either way, which is the '
        'usual case and worth a direct question; C means local work rights are '
        'required. Scores are out of 100 and weight role fit, international '
        'eligibility, pay, company, candidate fit and location.',
        '',
    ]

    for bucket in BUCKET_ORDER:
        in_bucket = [r for r in live if r.get('Bucket') == bucket]
        if not in_bucket:
            continue
        lines += [f'## {bucket}  ({len(in_bucket)})', '']
        for row in in_bucket:
            is_new = listing_key(row) in added_keys
            flag = ' 🆕' if is_new else ''
            lines.append(
                f"### {row['Company']} — {row['Title']}{flag}"
            )
            location = ', '.join(filter(None, [row.get('City'), row.get('Country')]))
            lines += [
                '',
                f"- **Location** {location}  ·  **Category** {row['Category']}"
                f"  ·  **Score** {row['Match Score']}/100",
                f"- **Visa** {visa_mod.CATEGORY_LABELS[row['Visa Category']]} — {row['Visa Explanation']}",
            ]
            if row.get('Visa Route'):
                lines.append(f"- **Route** {row['Visa Route']}")
            pay = row['Paid'] + (f" ({row['Compensation']})" if row.get('Compensation') else '')
            lines += [
                f"- **Paid** {pay}  ·  **English** {row['English Environment']}"
                f"  ·  **Status** {row['Application Status']}",
                f"- **Why it fits** {row['Why It Fits']}",
            ]
            if row.get('Barriers'):
                lines.append(f"- **Barriers** {row['Barriers']}")
            lines += [f"- **Apply** {row['Link']}", '']

    lines += [
        '---',
        '',
        '## Coverage and honest limits',
        '',
        '- Sources are company job-board APIs (Greenhouse, Lever, Ashby) for '
        f'the {len(rows) and ""}configured employer list in `intl_boards.py`. '
        'This finds real, currently-listed postings; it does not see companies '
        'whose boards are not in that list.',
        '- Visa categories are read from the posting text. An employer that '
        'says nothing is category B, not category C — silence is not refusal, '
        'and the only way to resolve it is to ask.',
        '- "Not publicly disclosed" pay means exactly that. Most employers do '
        'not publish intern rates, so it is not evidence the role is unpaid.',
        '- Summer 2027 postings for many large employers are not open yet. '
        'Roles listed without a year are kept and marked so, because boards '
        'routinely omit it.',
        '',
        'Add employers by putting their board token in `intl_boards.py`, then '
        'run `python3 intl_sources.py --check` to confirm it responds.',
    ]

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return path


def run(report_only=False):
    existing = read_csv(INTL_TRACKER_FILE)

    if report_only:
        render_report(existing)
        print(f'Rewrote {INTL_REPORT_FILE} from {len(existing)} tracked rows.')
        return 0

    print('Searching company boards for international Summer 2027 internships...')
    postings = scrape_all(
        progress=lambda done, total, org, n:
        print(f'  [{done}/{total}] {org}', end='\r', flush=True))
    print(' ' * 60, end='\r')

    if not postings:
        # Same guard as the domestic pipeline: an empty scrape must not be
        # allowed to close every tracked opportunity.
        print('No postings returned from any board; tracker left unchanged.')
        return 1

    new_rows = [build_row(p) for p in postings]
    merged, added, closed = merge_rows(existing, new_rows)
    write_csv(INTL_TRACKER_FILE, merged, INTL_FIELDNAMES)
    render_report(merged, added)

    live = [r for r in merged if r.get('Status') != 'Closed']
    print(f'\n{len(live)} live international opportunities '
          f'({len(added)} new, {closed} newly closed)')
    for bucket in BUCKET_ORDER:
        count = sum(1 for r in live if r.get('Bucket') == bucket)
        if count:
            print(f'  {bucket}: {count}')

    if added:
        print('\nNew since last run:')
        for row in sorted(added, key=lambda r: -int(r['Match Score']))[:10]:
            print(f"  {row['Match Score']:>3}  {row['Company']} — {row['Title'][:52]} "
                  f"({row['Country']})")

    print(f'\nWrote {INTL_TRACKER_FILE} and {INTL_REPORT_FILE}')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true',
                        help='re-render the report from the existing tracker')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    return run(report_only=args.report)


if __name__ == '__main__':
    sys.exit(main())
