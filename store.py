#!/usr/bin/env python3
"""
SQLite mirror of the tracker, with the application history the CSV cannot hold.

The CSV stays the working file people open and edit. This adds the things a
flat file cannot answer:

  - "what did I apply to in week 3?" (status_history)
  - "how long between applying and hearing back?" (timestamps per transition)
  - "when did this listing first appear?" (first_seen, never overwritten)

sync_from_csv() is the only writer of the listings table; it is idempotent and
records a history row only when a status actually changes, so running it on a
schedule does not inflate the history.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from tracker_io import TRACKER_FILE, normalize_link, read_csv

DB_PATH = 'internship_tracker.db'

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    link_key      TEXT PRIMARY KEY,
    company       TEXT NOT NULL,
    role          TEXT,
    location      TEXT,
    link          TEXT,
    date_posted   TEXT,
    deadline      TEXT,
    sponsorship   TEXT,
    source        TEXT,
    priority      TEXT,
    score         INTEGER,
    category      TEXT,
    status        TEXT,
    notes         TEXT,
    date_applied  TEXT,
    interview_date TEXT,
    offer_status  TEXT,
    followup_date TEXT,
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS status_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    link_key   TEXT NOT NULL REFERENCES listings(link_key),
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_priority ON listings(priority, score DESC);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_history_link ON status_history(link_key, changed_at);
"""

# CSV column -> database column.
COLUMN_MAP = {
    'Company': 'company', 'Role': 'role', 'Location': 'location', 'Link': 'link',
    'Date Posted': 'date_posted', 'Application Deadline': 'deadline',
    'Work Authorization/Sponsorship Notes': 'sponsorship', 'Source': 'source',
    'Priority': 'priority', 'Score': 'score', 'Category': 'category',
    'Status': 'status', 'Notes': 'notes', 'Date Applied': 'date_applied',
    'Interview Date': 'interview_date', 'Offer Status': 'offer_status',
    'Follow-up Date': 'followup_date',
}


@contextmanager
def connect(db_path=DB_PATH):
    """Open the database, creating the schema on first use."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_values(row):
    values = {}
    for csv_col, db_col in COLUMN_MAP.items():
        value = row.get(csv_col, '')
        if db_col == 'score':
            try:
                value = int(value or 0)
            except (TypeError, ValueError):
                value = 0
        values[db_col] = value
    return values


def sync_from_csv(csv_path=TRACKER_FILE, db_path=DB_PATH, now=None):
    """Mirror the tracker CSV into SQLite and record status transitions.

    Returns (inserted, updated, transitions). Safe to run repeatedly: only a
    real status change appends to status_history.
    """
    now = now or datetime.now().isoformat(timespec='seconds')
    rows = read_csv(csv_path)
    if not rows:
        return 0, 0, 0

    inserted = updated = transitions = 0

    with connect(db_path) as conn:
        existing = {
            r['link_key']: r['status']
            for r in conn.execute('SELECT link_key, status FROM listings')
        }

        for row in rows:
            key = normalize_link(row.get('Link', '')) or f"norow:{row.get('Company','')}|{row.get('Role','')}"
            values = _row_values(row)
            values['link_key'] = key
            values['last_seen'] = now

            if key in existing:
                old_status = existing[key]
                conn.execute(
                    'UPDATE listings SET ' +
                    ', '.join(f'{c} = :{c}' for c in list(COLUMN_MAP.values()) + ['last_seen']) +
                    ' WHERE link_key = :link_key', values)
                updated += 1
                if old_status != values['status']:
                    conn.execute(
                        'INSERT INTO status_history (link_key, old_status, new_status, changed_at)'
                        ' VALUES (?, ?, ?, ?)', (key, old_status, values['status'], now))
                    transitions += 1
            else:
                values['first_seen'] = now
                columns = list(COLUMN_MAP.values()) + ['link_key', 'first_seen', 'last_seen']
                conn.execute(
                    f"INSERT INTO listings ({', '.join(columns)}) "
                    f"VALUES ({', '.join(':' + c for c in columns)})", values)
                inserted += 1
                # Seed history so every listing has an origin row to diff from.
                conn.execute(
                    'INSERT INTO status_history (link_key, old_status, new_status, changed_at)'
                    ' VALUES (?, NULL, ?, ?)', (key, values['status'], now))

    return inserted, updated, transitions


def applications_by_week(db_path=DB_PATH, weeks=12):
    """Applications submitted per ISO week - the question CSV cannot answer."""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT changed_at FROM status_history WHERE new_status = 'Applied'"
            " ORDER BY changed_at").fetchall()

    counts = {}
    for row in rows:
        try:
            when = datetime.fromisoformat(row['changed_at']).date()
        except ValueError:
            continue
        year, week, _ = when.isocalendar()
        counts[f'{year}-W{week:02d}'] = counts.get(f'{year}-W{week:02d}', 0) + 1
    return dict(sorted(counts.items())[-weeks:])


def response_times(db_path=DB_PATH):
    """Days from Applied to the next status change, per listing."""
    with connect(db_path) as conn:
        rows = conn.execute(
            'SELECT link_key, old_status, new_status, changed_at FROM status_history'
            ' ORDER BY link_key, changed_at').fetchall()

    applied_at = {}
    results = []
    for row in rows:
        key = row['link_key']
        if row['new_status'] == 'Applied':
            applied_at[key] = row['changed_at']
        elif key in applied_at and row['new_status'] in ('Interviewing', 'Offer', 'Rejected'):
            try:
                start = datetime.fromisoformat(applied_at.pop(key))
                end = datetime.fromisoformat(row['changed_at'])
            except ValueError:
                continue
            results.append({'link_key': key, 'outcome': row['new_status'],
                            'days': (end - start).days})
    return results


def funnel(db_path=DB_PATH):
    """Current counts by status, plus how many listings are being tracked."""
    with connect(db_path) as conn:
        rows = conn.execute(
            'SELECT status, COUNT(*) AS n FROM listings GROUP BY status').fetchall()
        total = conn.execute('SELECT COUNT(*) AS n FROM listings').fetchone()['n']
    return {'total': total, **{r['status']: r['n'] for r in rows}}


def main():
    inserted, updated, transitions = sync_from_csv()
    print(f'Synced {TRACKER_FILE} -> {DB_PATH}')
    print(f'  {inserted} new, {updated} updated, {transitions} status changes recorded')
    print(f'  funnel: {funnel()}')
    weekly = applications_by_week()
    if weekly:
        print('  applications per week:')
        for week, count in weekly.items():
            print(f'    {week}: {count}')


if __name__ == '__main__':
    main()
