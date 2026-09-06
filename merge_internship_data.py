#!/usr/bin/env python3
"""
Merge scraped internship data into the master tracker.

The tracker CSV is the system of record for the user's application history, so
this script MERGES into it rather than regenerating it:

  - a listing already in the tracker keeps every user-owned column
    (Status, Notes, Date Applied, ...) and only refreshes scraped metadata
  - a listing that has disappeared upstream is kept, not deleted; if the user
    never acted on it, it is marked 'Closed'
  - a genuinely new listing is appended as 'Not Applied'

Listings are matched by normalized link, so tracking parameters changing
upstream does not create a duplicate row.
"""
import json
import os
from datetime import datetime

from roles import classify_role
from scoring import score_listing
from tracker_io import (
    NEW_LISTINGS_FILE, SCRAPED_FILE, TRACKER_FILE, TRACKER_FIELDNAMES,
    USER_FIELDS, normalize_link, read_csv, write_csv,
)

MASTER_FILE = 'SWE_Internship_Master_Tracker.csv'


def assign_priority(company, role):
    """Priority 1-5 for a listing. Thin wrapper kept for callers and tests."""
    return score_listing(company, role)[1]


def sponsorship_notes(row):
    """Sponsorship note for a scraped row.

    enhanced_scraper.py already resolved this against sponsorship_database.py,
    so prefer its answer and only fall back for rows that predate that field.
    """
    if str(row.get('no_sponsorship', '')).strip().lower() == 'true':
        return 'No sponsorship'
    notes = (row.get('sponsorship_notes') or '').strip()
    if notes:
        return notes
    return 'Unknown - check listing'


def scraped_to_tracker_row(row):
    """Build a fresh tracker row from a scraped row (user columns left blank)."""
    company, role = row.get('company', ''), row.get('role', '')
    score, priority, reasons = score_listing(
        company, role,
        sponsorship_tier=row.get('sponsorship_tier'),
        no_sponsorship=str(row.get('no_sponsorship', '')).strip().lower() == 'true',
    )
    return {
        'Company': company,
        'Role': role,
        'Location': row.get('location', ''),
        'Link': row.get('link', ''),
        'Date Posted': row.get('date_posted') or datetime.now().strftime('%Y-%m-%d'),
        'Application Deadline': '',
        'Work Authorization/Sponsorship Notes': sponsorship_notes(row),
        'Eligibility': row.get('sponsorship_tier', 'Unknown'),
        'Source': row.get('source', ''),
        'Priority': priority,
        'Score': str(score),
        'Category': classify_role(role) or '',
        'Score Reasons': '; '.join(reasons),
        'Status': 'Not Applied',
        'Notes': '',
        'Date Applied': '',
        'Interview Date': '',
        'Offer Status': '',
        'Follow-up Date': '',
    }


def master_to_tracker_row(row):
    """Build a tracker row from the hand-curated master company list."""
    role = row.get('Program') or row.get('Role') or ''
    company = row.get('Company', '')
    score, priority, reasons = score_listing(company, role)
    return {
        'Company': company,
        'Role': role,
        # The master list tracks companies, not individual postings, so it has
        # no per-posting location.
        'Location': 'Multiple',
        'Link': row.get('Link', ''),
        'Date Posted': '',
        'Application Deadline': '',
        'Work Authorization/Sponsorship Notes': row.get('Notes', ''),
        'Eligibility': row.get('Likelihood', ''),
        'Source': 'master_tracker',
        'Priority': priority,
        'Score': str(score),
        'Category': classify_role(role) or '',
        'Score Reasons': '; '.join(reasons),
        'Status': 'Not Applied',
        'Notes': row.get('Notes', ''),
        'Date Applied': '',
        'Interview Date': '',
        'Offer Status': '',
        'Follow-up Date': '',
    }


def merge_row(existing, incoming):
    """Refresh an existing tracker row with incoming scraped metadata.

    User-owned columns always win: this is what stops an automated run from
    erasing an application the user already submitted.
    """
    merged = dict(existing)
    for field in TRACKER_FIELDNAMES:
        if field in USER_FIELDS:
            continue
        value = incoming.get(field, '')
        # Never blank out a populated column with an empty scrape.
        if value:
            merged[field] = value
    # A listing that reappeared upstream is open again.
    if merged.get('Status') == 'Closed':
        merged['Status'] = 'Not Applied'
        merged['Notes'] = ''
    return merged


def write_new_listings(new_rows, path=NEW_LISTINGS_FILE):
    """Persist the listings this merge added, newest run replacing the last."""
    payload = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'listings': sorted(new_rows, key=lambda r: -int(r.get('Score') or 0)),
    }
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)


def read_new_listings(path=NEW_LISTINGS_FILE, min_priority='2'):
    """Listings added by the last merge, filtered to those worth alerting on."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return [r for r in payload.get('listings', [])
            if (r.get('Priority') or '9') <= min_priority]


def build_tracker():
    """Merge master list + scraped listings into the tracker, preserving state."""
    existing_rows = read_csv(TRACKER_FILE)
    scraped = read_csv(SCRAPED_FILE)
    master = read_csv(MASTER_FILE)

    if not scraped:
        print(f'Warning: {SCRAPED_FILE} is empty or missing.')
        print('Run "python3 enhanced_scraper.py" first. Tracker left unchanged.')
        return None

    # Index the user's existing rows by normalized link. Rows without a link
    # (hand-added entries) cannot be matched, so they are carried through as-is.
    by_link = {}
    unlinked = []
    for row in existing_rows:
        key = normalize_link(row.get('Link', ''))
        if key and key not in by_link:
            by_link[key] = row
        elif not key:
            unlinked.append(row)

    seen = set()
    merged_rows = []
    new_rows = []

    def absorb(candidate):
        key = normalize_link(candidate.get('Link', ''))
        if key and key in seen:
            return
        if key:
            seen.add(key)
        existing = by_link.get(key) if key else None
        if existing:
            merged_rows.append(merge_row(existing, candidate))
        else:
            merged_rows.append(candidate)
            new_rows.append(candidate)

    for row in master:
        absorb(master_to_tracker_row(row))
    for row in scraped:
        absorb(scraped_to_tracker_row(row))

    # Anything the user already had that is no longer listed upstream is kept.
    # Deleting it would destroy an application record; instead, an untouched
    # listing is marked Closed so it drops out of the daily apply queue.
    stale = 0
    for key, row in by_link.items():
        if key in seen:
            continue
        row = dict(row)
        if row.get('Status') == 'Not Applied':
            row['Status'] = 'Closed'
            row['Notes'] = row.get('Notes') or 'No longer listed upstream'
            stale += 1
        merged_rows.append(row)
    merged_rows.extend(unlinked)

    # Highest score first inside each priority band, so the top of the file is
    # always the best thing to apply to next.
    # Record exactly what this run added, so alerts do not have to guess.
    write_new_listings(new_rows)

    merged_rows.sort(key=lambda r: (r.get('Priority') or '9',
                                    -int(r.get('Score') or 0),
                                    r.get('Company') or ''))
    write_csv(TRACKER_FILE, merged_rows, TRACKER_FIELDNAMES)

    print(f'Tracker now has {len(merged_rows)} entries '
          f'({len(new_rows)} added, {stale} newly closed).')
    notable = [r for r in new_rows if r.get('Priority') in ('1', '2')]
    if notable:
        print(f'\n{len(notable)} new priority 1-2 listing(s):')
        for row in sorted(notable, key=lambda r: -int(r.get('Score') or 0))[:10]:
            print(f"  P{row['Priority']} {row['Score']:>3}  {row['Company']} - {row['Role']}")

    counts = {}
    for row in merged_rows:
        counts[row['Priority']] = counts.get(row['Priority'], 0) + 1
    print('\nPriority breakdown:')
    for priority in sorted(counts):
        print(f'  Priority {priority}: {counts[priority]} entries')

    active = sum(1 for r in merged_rows if r.get('Status') == 'Not Applied')
    applied = sum(1 for r in merged_rows if r.get('Status') not in ('Not Applied', 'Closed', ''))
    print(f'\nOpen and unapplied: {active}   In progress: {applied}')
    return merged_rows


if __name__ == '__main__':
    build_tracker()
