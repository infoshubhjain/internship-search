#!/usr/bin/env python3
"""
Shared CSV I/O for the tracker.

Every script in this repo rewrites Summer2027_SWE_Tracker.csv in place. That file
holds the user's real application history, so a crash or a full disk halfway
through a write used to truncate it. All writes go through write_csv() here,
which writes to a temp file in the same directory and atomically renames it.
"""
import csv
import os
import tempfile

TRACKER_FILE = 'Summer2027_SWE_Tracker.csv'
SCRAPED_FILE = 'enhanced_scraped_internships.csv'
# Listings added by the most recent merge. The merge knows exactly which rows
# are new, so alerts read this instead of inferring novelty from Date Posted -
# which the merge itself stamps, making every row look new on a first run.
NEW_LISTINGS_FILE = 'new_listings.json'

# The international tracker. Separate file from the domestic one because the
# questions are different - visa route, compensation disclosure, match score -
# but it goes through the same atomic writes and the same merge guarantees.
INTL_TRACKER_FILE = 'Summer2027_Intl_Tracker.csv'
INTL_REPORT_FILE = 'INTERNATIONAL_REPORT.md'

# Column order of the tracker CSV. Columns after 'Priority' are user-owned:
# scrapers and merges must never overwrite them.
TRACKER_FIELDNAMES = [
    'Company', 'Role', 'Location', 'Link', 'Date Posted', 'Application Deadline',
    'Work Authorization/Sponsorship Notes', 'Eligibility', 'Source', 'Priority',
    'Score', 'Category', 'Score Reasons', 'Salary',
    'Status', 'Notes', 'Date Applied', 'Interview Date', 'Offer Status', 'Follow-up Date',
]

# Fields the user edits by hand. Preserved across every automated rebuild.
USER_FIELDS = [
    'Status', 'Notes', 'Date Applied', 'Interview Date', 'Offer Status',
    'Follow-up Date', 'Application Deadline',
]

STATUSES = ['Not Applied', 'Applied', 'Interviewing', 'Offer', 'Rejected', 'Closed']

# Column order for the international tracker, following the output format in
# the search brief: what it is, how to apply, whether the candidate can legally
# take it, what it pays, and how well it fits.
INTL_FIELDNAMES = [
    # basic
    'Company', 'Title', 'Country', 'City', 'Region Tier', 'Category',
    'Employment Type', 'Duration', 'Expected Start', 'Expected End',
    # application
    'Application Status', 'Application Deadline', 'Link', 'Source', 'External ID',
    'Date Posted', 'Last Verified',
    # eligibility
    'Undergrad Eligible', 'Foreign University Eligible', 'International Eligible',
    'Work Auth Required', 'Visa Sponsorship', 'Local Language Required',
    'English Environment',
    # visa
    'Visa Category', 'Visa Explanation', 'Visa Route', 'Visa Evidence',
    # compensation
    'Paid', 'Compensation', 'Currency', 'Housing', 'Relocation',
    # match
    'Match Score', 'Score Breakdown', 'Why It Fits', 'Barriers', 'Bucket',
    # user-owned
    'Status', 'Notes', 'Date Applied', 'Interview Date', 'Offer Status', 'Follow-up Date',
]

# Same guarantee as the domestic tracker: automated runs never touch these.
INTL_USER_FIELDS = [
    'Status', 'Notes', 'Date Applied', 'Interview Date', 'Offer Status',
    'Follow-up Date',
]


def read_csv(path):
    """Read a CSV into a list of dicts. Missing file returns []."""
    try:
        with open(path, 'r', encoding='utf-8', newline='') as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def write_csv(path, rows, fieldnames):
    """Write rows to path atomically, so an interrupted run cannot truncate it."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def normalize_link(link):
    """Canonical form of a job URL, used as the identity key for a listing.

    Upstream repos append tracking params and vary on trailing slashes and
    scheme, so the raw URL is not stable enough to dedupe or to match a
    listing against the user's existing row for it.
    """
    if not link:
        return ''
    link = link.strip().lower().split('?')[0].split('#')[0]
    for prefix in ('https://', 'http://'):
        if link.startswith(prefix):
            link = link[len(prefix):]
            break
    if link.startswith('www.'):
        link = link[4:]
    return link.rstrip('/')


def listing_key(row):
    """Stable identity for an international listing.

    The apply link alone is not enough: some boards point every posting at one
    generic careers page, which would collapse 25 distinct jobs into a single
    row. The board's own job id is authoritative when present.
    """
    source = (row.get('Source') or row.get('source') or '').strip()
    external = (row.get('External ID') or row.get('external_id') or '').strip()
    if source and external:
        return f'{source}#{external}'
    link = normalize_link(row.get('Link') or row.get('link') or '')
    if link:
        return link
    return f"{row.get('Company') or row.get('company', '')}|{row.get('Title') or row.get('title', '')}".lower()


def update_row(link, updates, path=TRACKER_FILE):
    """Apply updates to the tracker row matching link. Returns True if found.

    Only user-owned columns may be set this way; scraped columns are owned by
    the merge and would be overwritten on the next run anyway.
    """
    bad = set(updates) - set(USER_FIELDS)
    if bad:
        raise ValueError(f'not user-editable: {sorted(bad)}')

    key = normalize_link(link)
    if not key:
        raise ValueError('a link is required to identify the row')

    rows = read_csv(path)
    found = False
    for row in rows:
        if normalize_link(row.get('Link', '')) == key:
            row.update(updates)
            found = True
    if found:
        write_csv(path, rows, TRACKER_FIELDNAMES)
    return found


def append_row(row, path=TRACKER_FILE):
    """Append a hand-entered listing. Returns False if the link already exists."""
    rows = read_csv(path)
    key = normalize_link(row.get('Link', ''))
    if key and any(normalize_link(r.get('Link', '')) == key for r in rows):
        return False

    complete = {field: '' for field in TRACKER_FIELDNAMES}
    complete.update(row)
    complete.setdefault('Source', 'manual')
    if not complete['Source']:
        complete['Source'] = 'manual'
    if not complete['Status']:
        complete['Status'] = 'Applied'
    if not complete['Priority']:
        complete['Priority'] = '5'
    rows.append(complete)
    write_csv(path, rows, TRACKER_FIELDNAMES)
    return True
