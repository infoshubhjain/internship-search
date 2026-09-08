#!/usr/bin/env python3
"""
Tests for the tracker pipeline. Run with: python3 test_tracker.py

No framework and no network: every test feeds fixed text through the parsers or
fixed rows through the merge. The merge tests are the important ones - they
guard the property that automated runs must never destroy the user's
application history.
"""
import os
import sys
import tempfile
from datetime import date

import enhanced_scraper as scraper
import merge_internship_data as merge
import tracker_io


# --------------------------------------------------------------------------
# tracker_io
# --------------------------------------------------------------------------

def test_normalize_link():
    same = [
        'https://WWW.Foo.com/job/1',
        'http://foo.com/job/1',
        'https://foo.com/job/1/',
        'https://www.foo.com/job/1?utm_source=github',
        'https://foo.com/job/1#apply',
    ]
    keys = {tracker_io.normalize_link(u) for u in same}
    assert keys == {'foo.com/job/1'}, keys
    assert tracker_io.normalize_link('') == ''
    assert tracker_io.normalize_link(None) == ''
    # Distinct postings must not collapse together.
    assert tracker_io.normalize_link('https://foo.com/job/1') != \
        tracker_io.normalize_link('https://foo.com/job/2')


def test_write_csv_is_atomic():
    """A failed write must leave the previous file intact, not a truncated one."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'x.csv')
        tracker_io.write_csv(path, [{'a': '1'}], ['a'])

        class Boom(dict):
            def get(self, *args, **kwargs):
                raise RuntimeError('disk full')

        try:
            tracker_io.write_csv(path, [Boom()], ['a'])
        except RuntimeError:
            pass
        else:
            raise AssertionError('expected the failing write to raise')

        assert tracker_io.read_csv(path) == [{'a': '1'}], 'original file was damaged'
        # No temp files left behind.
        assert os.listdir(tmp) == ['x.csv'], os.listdir(tmp)


# --------------------------------------------------------------------------
# parsers
# --------------------------------------------------------------------------

VANSH_TABLE = """
| Company | Role | Location | Application/Link | Date Posted |
| --- | --- | --- | --- | --- |
| **Acme** | Software Engineer Intern | NYC | <a href="https://acme.com/j/1?utm_source=x"><img src="i.png"></a> | Aug 21 |
| ↳ | Backend Intern | Remote | <a href="https://acme.com/j/2"><img src="i.png"></a> | Aug 21 |
| \U0001f525 Globex | SWE Intern \U0001f6c2 | SF | <a href="https://globex.com/j/3"><img src="i.png"></a> | 2026-08-01 |
| Closed Co | SWE Intern | NYC | \U0001f512 | Aug 04 |
| Citizens Only | SWE Intern \U0001f1fa\U0001f1f8 | DC | <a href="https://x.com/j/4"><img src="i.png"></a> | Aug 04 |
"""


def test_vansh_parser():
    rows = scraper.parse_vansh_format(VANSH_TABLE)
    companies = [r['company'] for r in rows]

    # The continuation row inherits the company above it instead of becoming a
    # company literally named with the arrow character.
    assert companies == ['Acme', 'Acme', 'Globex'], companies
    assert rows[0]['role'] == 'Software Engineer Intern'
    assert rows[1]['role'] == 'Backend Intern'
    # Tracking params are stripped from the stored link.
    assert rows[0]['link'] == 'https://acme.com/j/1', rows[0]['link']
    # Emoji decoration is not part of the company name.
    assert rows[2]['company'] == 'Globex'
    # The no-sponsorship flag is recorded, not used to drop the row.
    assert rows[2]['no_sponsorship'] is True
    assert rows[0]['no_sponsorship'] is False
    # Closed and citizenship-only listings are excluded.
    assert 'Closed Co' not in companies
    assert 'Citizens Only' not in companies


SIMPLIFY_TABLE = """## \U0001f4bb Software Engineering Internship Roles
<table>
<tbody>
<tr>
<td><strong><a href="https://simplify.jobs/c/Acme">Acme</a></strong></td>
<td>Software Engineering Intern</td>
<td>NYC</td>
<td><div align="center"><a href="https://boards.acme.com/jobs/1?utm_source=Simplify"><img src="https://i.imgur.com/a.png"></a> <a href="https://simplify.jobs/p/abc"><img src="https://i.imgur.com/b.png"></a></div></td>
<td>1d</td>
</tr>
<tr>
<td>↳</td>
<td>Technology Intern</td>
<td>NYC<br>SF</td>
<td><div align="center"><a href="https://boards.acme.com/jobs/2"><img src="https://i.imgur.com/a.png"></a></div></td>
<td>3d</td>
</tr>
</tbody>
</table>

## \U0001f4f1 Product Management Internship Roles
<tr>
<td><strong><a href="https://simplify.jobs/c/Nope">Nope</a></strong></td>
<td>PM Intern</td>
<td>NYC</td>
<td><a href="https://boards.nope.com/jobs/9"><img src="x.png"></a></td>
<td>1d</td>
</tr>
"""


def test_simplify_parser():
    """Each <tr> spans multiple lines; a line-by-line scan finds nothing."""
    rows = scraper.parse_simplify_format(SIMPLIFY_TABLE)
    assert len(rows) == 2, rows
    assert [r['company'] for r in rows] == ['Acme', 'Acme']
    assert rows[1]['role'] == 'Technology Intern'
    # Simplify's own referral link and image assets are not the apply link.
    assert rows[0]['link'] == 'https://boards.acme.com/jobs/1', rows[0]['link']
    # <br> in the location cell becomes a readable separator.
    assert rows[1]['location'] == 'NYC, SF', rows[1]['location']
    # Only the Software Engineering section is read.
    assert all(r['company'] != 'Nope' for r in rows)


GENERIC_TABLE = """
| Company | Role | Location | Apply | Added |
| --- | --- | --- | --- | --- |
| Susquehanna | Quant Intern | New York, NY | [apply](https://careers.sig.com/jobs/10822) | 2026-07-21 |
| ↳ | Systems Intern | New York, NY | [apply](https://careers.sig.com/jobs/10823) | 2026-07-21 |
"""


def test_generic_markdown_parser():
    rows = scraper.parse_generic_markdown(GENERIC_TABLE, 'test_repo')
    assert len(rows) == 2, rows
    assert [r['company'] for r in rows] == ['Susquehanna', 'Susquehanna']
    assert rows[0]['link'] == 'https://careers.sig.com/jobs/10822'
    assert rows[0]['source'] == 'test_repo'
    assert rows[0]['date_posted'] == '2026-07-21'


def test_generic_parser_rejects_unknown_columns():
    """An unrecognized table yields nothing rather than garbage rows."""
    assert scraper.parse_generic_markdown('| Foo | Bar |\n| a | b |\n') == []


def test_parse_date_posted():
    today = date(2026, 9, 6)
    cases = {
        '2026-07-21': '2026-07-21',
        'Aug 21': '2026-08-21',
        'Dec 15': '2025-12-15',      # bare month/day in the future means last year
        'Aug 21, 2025': '2025-08-21',
        '3d': '2026-09-03',
        '2mo': '2026-07-08',
        '': '',
        'sometime soon': '',
    }
    for raw, expected in cases.items():
        got = scraper.parse_date_posted(raw, today)
        assert got == expected, f'{raw!r}: expected {expected!r}, got {got!r}'


def test_applyguy_parser_ignores_non_swe_and_interstitials():
    payload = """{"jobs": [
      {"company": "Acme", "title": "SWE Intern Summer 2027", "category": "Software Engineering",
       "location": "NYC", "listingUrl": "https://acme.com/j/1", "posted": "2026-09-05", "season": "Summer 2027"},
      {"company": "Nope", "title": "Design Intern 2027", "category": "Design",
       "location": "NYC", "listingUrl": "https://nope.com/j/2", "season": "Summer 2027"},
      {"company": "Blocked", "title": "SWE Intern 2027", "category": "Software Engineering",
       "location": "NYC", "listingUrl": "https://applyguy.ai/x", "season": "Summer 2027"}
    ]}"""
    rows = scraper.parse_applyguy_format(payload)
    assert [r['company'] for r in rows] == ['Acme'], rows
    assert rows[0]['date_posted'] == '2026-09-05'


def test_applyguy_parser_survives_bad_json():
    assert scraper.parse_applyguy_format('not json at all') == []


# --------------------------------------------------------------------------
# role classification
# --------------------------------------------------------------------------

def test_classify_role():
    from roles import classify_role
    technical = {
        'Software Engineer Intern': 'Software Engineering',
        'SDE Intern': 'Software Engineering',
        'Backend Engineer Intern': 'Backend Engineering',
        'Full-Stack Developer Intern': 'Full-Stack Engineering',
        'Machine Learning Intern': 'Machine Learning / AI',
        'Data Engineer Intern': 'Data Engineering',
        'Site Reliability Engineering Intern': 'Cloud / DevOps / Infrastructure',
        'Cyber Security Intern': 'Cybersecurity',
        'Research Intern': 'Research',
        'Technology Intern': 'General Technology',
    }
    for title, expected in technical.items():
        assert classify_role(title) == expected, (title, classify_role(title))

    # Non-technical roles must be rejected, including ones that name a
    # technical field.
    for title in ['Product Manager Intern', 'Product Manager, Machine Learning',
                  'UX Designer Intern', 'Marketing Intern', 'Technical Recruiter',
                  'Mechanical Engineer Intern', 'Sales and Trading Intern',
                  'Investment Analyst Intern', '', None]:
        assert classify_role(title) is None, (title, classify_role(title))


def test_strong_technical_signal_overrides_exclusion():
    """An explicit engineering title is not thrown out for one stray word."""
    from roles import classify_role
    assert classify_role('Software Engineer Intern, Brand Innovation') == 'Software Engineering'
    assert classify_role('Backend Software Engineer Intern, Digital Content') == 'Backend Engineering'


# --------------------------------------------------------------------------
# sponsorship lookup
# --------------------------------------------------------------------------

def test_sponsorship_short_keys_do_not_match_substrings():
    """The 'x' entry (Twitter/X) used to claim RTX, SpaceX, Cox and Apex.

    These companies may now legitimately resolve from USCIS filing data, so
    the invariant is not "unknown" - it is that they never inherit another
    company's curated entry by substring.
    """
    from sponsorship_database import get_sponsorship_info
    for company in ['Cox', 'Apex', 'Apex Technology, Inc.', 'Plexus']:
        info = get_sponsorship_info(company)
        assert info.get('source') != 'curated', (company, info)
        assert 'Twitter' not in info['notes'], (company, info)
    # The real entry still resolves to a sponsoring tier. The exact tier now
    # comes from filing volume rather than the hand-written guess, so this
    # asserts the classification, not a hardcoded number.
    assert get_sponsorship_info('Twitter')['tier'] <= 3


def test_h1b_data_backs_known_sponsors():
    """Filing counts, not policy guesses, drive the common case."""
    from sponsorship_database import get_sponsorship_info
    info = get_sponsorship_info('Google')
    assert info['tier'] == 1 and info['source'] == 'uscis_h1b', info
    assert 'H-1B approvals' in info['notes']


def test_curated_non_sponsor_beats_h1b_volume():
    """A listing that said 'no sponsorship' outranks the employer's filings."""
    from sponsorship_database import get_sponsorship_info
    info = get_sponsorship_info('Epic Games')
    assert info['cpt'] is False, info


def test_citizenship_requirement_beats_h1b_volume():
    """Cleared employers file plenty of H-1Bs and still need citizenship."""
    from sponsorship_database import get_sponsorship_info
    for company in ['Booz Allen Hamilton', 'RTX', 'Leidos']:
        assert get_sponsorship_info(company)['tier'] == 6, company


def test_sponsorship_prefers_longest_key():
    from sponsorship_database import get_sponsorship_info
    # 'ge' must not win over the more specific defense-contractor match.
    assert get_sponsorship_info('General Dynamics UK')['tier'] == 6


def test_citizenship_required_employers():
    """ITAR / cleared employers are a hard barrier for an F-1 student."""
    from sponsorship_database import get_sponsorship_info, requires_citizenship
    for company in ['RTX', 'SpaceX', 'Lockheed Martin', 'Northrop Grumman',
                    'Booz Allen Hamilton', 'Anduril']:
        assert requires_citizenship(company), company
        assert get_sponsorship_info(company)['tier'] == 6, company
    for company in ['Google', 'Stripe', 'Goldman Sachs']:
        assert not requires_citizenship(company), company


def test_sponsorship_handles_corporate_suffixes():
    from sponsorship_database import get_sponsorship_info
    assert get_sponsorship_info('Google LLC')['tier'] == 1
    assert get_sponsorship_info('Google, Inc.')['tier'] == 1
    assert get_sponsorship_info('')['tier'] == 5


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def test_score_ranks_sponsoring_software_roles_highest():
    from scoring import score_listing
    good = score_listing('Amazon', 'SDE Intern')[0]
    unknown = score_listing('Nobody Inc', 'Software Engineer Intern')[0]
    non_tech = score_listing('Google', 'Product Manager Intern')[0]
    assert good > unknown > non_tech


def test_score_recognises_named_underclassman_programs():
    """STEP and Explore do not say 'software' anywhere in the title."""
    from scoring import score_listing
    for company, role in [('Google', 'STEP Intern'), ('Microsoft', 'Explore Intern')]:
        score, priority, _ = score_listing(company, role)
        assert priority == '1', (company, role, score, priority)


def test_score_caps_citizenship_restricted_roles():
    """A prestigious name must not outweigh a clearance requirement."""
    from scoring import score_listing
    score, priority, reasons = score_listing('SpaceX', 'Software Engineer Intern')
    assert priority == '5' and score <= 25, (score, priority)
    assert any('citizenship' in r for r in reasons), reasons


def test_score_ignores_stale_cached_tier_for_restricted_employer():
    """A wrong tier cached in an old scrape must not resurrect the listing."""
    from scoring import score_listing
    _, priority, _ = score_listing('RTX', 'Software Engineer Intern', sponsorship_tier='1')
    assert priority == '5', priority


def test_score_penalises_explicit_no_sponsorship():
    from scoring import score_listing
    _, priority, _ = score_listing('Google', 'Software Engineer Intern', no_sponsorship=True)
    assert priority == '5', priority


# --------------------------------------------------------------------------
# priority
# --------------------------------------------------------------------------

def test_assign_priority():
    assert merge.assign_priority('Google', 'STEP Intern') == '1'
    assert merge.assign_priority('Amazon', 'SDE Intern') == '1'
    # Unknown sponsorship ranks below a known sponsor for the same role.
    assert merge.assign_priority('Nobody Inc', 'SWE Intern') > \
        merge.assign_priority('Goldman Sachs', 'Software Engineer Intern')
    assert merge.assign_priority('', '') == '5'
    assert merge.assign_priority(None, None) == '5'


def test_merge_writes_score_columns():
    rows = run_merge([], [scraped_row(company='Amazon', role='SDE Intern')])
    row = rows[0]
    assert row['Score'].isdigit() and int(row['Score']) > 0, row
    assert row['Category'] == 'Software Engineering', row
    assert 'Software Engineering' in row['Score Reasons'], row


# --------------------------------------------------------------------------
# merge - the behaviour that protects the user's data
# --------------------------------------------------------------------------

def run_merge(existing, scraped, master=()):
    """Run build_tracker against temp files and return the resulting rows."""
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            if existing:
                tracker_io.write_csv(tracker_io.TRACKER_FILE, existing,
                                     tracker_io.TRACKER_FIELDNAMES)
            tracker_io.write_csv(tracker_io.SCRAPED_FILE, scraped, list(scraped[0])) \
                if scraped else None
            if master:
                tracker_io.write_csv(merge.MASTER_FILE, master, list(master[0]))
            merge.build_tracker()
            return tracker_io.read_csv(tracker_io.TRACKER_FILE)
        finally:
            os.chdir(cwd)


def scraped_row(company='Acme', link='https://acme.com/j/1', **kw):
    row = {'company': company, 'role': 'SWE Intern', 'location': 'NYC', 'link': link,
           'no_sponsorship': 'False', 'source': 'test', 'sponsorship_tier': '1',
           'sponsorship_notes': 'Sponsors', 'date_posted': '2026-09-01'}
    row.update(kw)
    return row


def tracker_row(**kw):
    row = {f: '' for f in tracker_io.TRACKER_FIELDNAMES}
    row.update({'Company': 'Acme', 'Role': 'SWE Intern', 'Link': 'https://acme.com/j/1',
                'Priority': '5', 'Status': 'Not Applied'})
    row.update(kw)
    return row


def test_merge_preserves_user_columns():
    """The core guarantee: a re-scrape must not erase an application."""
    existing = [tracker_row(Status='Applied', **{
        'Date Applied': '2026-09-01', 'Notes': 'referred by Dana',
        'Interview Date': '2026-09-20', 'Offer Status': 'Pending',
        'Follow-up Date': '2026-09-25', 'Application Deadline': '2026-10-01',
    })]
    rows = run_merge(existing, [scraped_row()])

    assert len(rows) == 1, rows
    row = rows[0]
    assert row['Status'] == 'Applied'
    assert row['Date Applied'] == '2026-09-01'
    assert row['Notes'] == 'referred by Dana'
    assert row['Interview Date'] == '2026-09-20'
    assert row['Offer Status'] == 'Pending'
    assert row['Follow-up Date'] == '2026-09-25'
    assert row['Application Deadline'] == '2026-10-01'


def test_merge_matches_despite_changed_tracking_params():
    """The same posting with new utm params must not become a second row."""
    existing = [tracker_row(Link='https://acme.com/j/1?utm_source=old', Status='Applied')]
    rows = run_merge(existing, [scraped_row(link='https://www.acme.com/j/1?utm_source=new')])
    assert len(rows) == 1, rows
    assert rows[0]['Status'] == 'Applied'


def test_merge_refreshes_scraped_metadata():
    """Non-user columns do follow upstream."""
    existing = [tracker_row(Role='Old Title', Status='Applied')]
    rows = run_merge(existing, [scraped_row(role='New Title')])
    assert rows[0]['Role'] == 'New Title'
    assert rows[0]['Status'] == 'Applied'


def test_merge_adds_new_listings():
    existing = [tracker_row()]
    rows = run_merge(existing, [scraped_row(), scraped_row(company='Globex',
                                                           link='https://globex.com/j/9')])
    assert len(rows) == 2, rows
    assert {r['Company'] for r in rows} == {'Acme', 'Globex'}


def test_merge_closes_but_never_deletes_delisted_rows():
    existing = [
        tracker_row(Link='https://gone.com/j/1', Company='Gone'),
        tracker_row(Link='https://applied.com/j/2', Company='Applied Co', Status='Applied'),
    ]
    rows = run_merge(existing, [scraped_row()])
    by_company = {r['Company']: r for r in rows}

    # Untouched and delisted -> drops out of the queue.
    assert by_company['Gone']['Status'] == 'Closed'
    # Already applied to -> the record is left exactly as it was.
    assert by_company['Applied Co']['Status'] == 'Applied'
    assert len(rows) == 3, rows


def test_merge_reopens_relisted_row():
    existing = [tracker_row(Status='Closed', Notes='No longer listed upstream')]
    rows = run_merge(existing, [scraped_row()])
    assert rows[0]['Status'] == 'Not Applied'
    assert rows[0]['Notes'] == ''


def test_merge_keeps_hand_added_rows_without_links():
    existing = [tracker_row(Link='', Company='Career Fair Lead', Status='Applied')]
    rows = run_merge(existing, [scraped_row()])
    assert any(r['Company'] == 'Career Fair Lead' and r['Status'] == 'Applied'
               for r in rows), rows


def test_merge_refuses_to_run_on_empty_scrape():
    """If every source failed, leave the tracker alone rather than closing it all."""
    existing = [tracker_row(Status='Applied')]
    rows = run_merge(existing, [])
    assert len(rows) == 1
    assert rows[0]['Status'] == 'Applied'


def test_merge_deduplicates_within_one_scrape():
    rows = run_merge([], [scraped_row(), scraped_row(link='https://acme.com/j/1/')])
    assert len(rows) == 1, rows


# --------------------------------------------------------------------------
# row editing (what the dashboard buttons call)
# --------------------------------------------------------------------------

def with_temp_tracker(rows):
    """Context helper: write rows to a temp tracker and return its path."""
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, 'tracker.csv')
    tracker_io.write_csv(path, rows, tracker_io.TRACKER_FIELDNAMES)
    return path


def test_update_row_writes_status():
    path = with_temp_tracker([tracker_row(), tracker_row(Link='https://b.com/2', Company='B')])
    assert tracker_io.update_row('https://acme.com/j/1?utm=x',
                                 {'Status': 'Applied', 'Date Applied': '2026-09-06'}, path)
    rows = {r['Company']: r for r in tracker_io.read_csv(path)}
    assert rows['Acme']['Status'] == 'Applied'
    assert rows['Acme']['Date Applied'] == '2026-09-06'
    # The other row is untouched.
    assert rows['B']['Status'] == 'Not Applied'


def test_update_row_reports_missing():
    path = with_temp_tracker([tracker_row()])
    assert tracker_io.update_row('https://nowhere.com/x', {'Status': 'Applied'}, path) is False


def test_update_row_rejects_scraped_columns():
    """Writing a scraped column here would be silently undone by the next merge."""
    path = with_temp_tracker([tracker_row()])
    try:
        tracker_io.update_row('https://acme.com/j/1', {'Company': 'Hacked'}, path)
    except ValueError:
        return
    raise AssertionError('expected ValueError for a non-user-editable column')


def test_append_row_adds_and_deduplicates():
    path = with_temp_tracker([tracker_row()])
    assert tracker_io.append_row(
        {'Company': 'New Co', 'Role': 'SWE', 'Link': 'https://new.co/1'}, path)
    rows = tracker_io.read_csv(path)
    assert len(rows) == 2
    added = [r for r in rows if r['Company'] == 'New Co'][0]
    assert added['Source'] == 'manual'
    assert added['Status'] == 'Applied'
    assert set(added) == set(tracker_io.TRACKER_FIELDNAMES)

    # Same link again is refused rather than duplicated.
    assert tracker_io.append_row({'Company': 'Dupe', 'Link': 'https://new.co/1/'}, path) is False
    assert len(tracker_io.read_csv(path)) == 2


def test_appended_row_survives_a_merge():
    """A hand-added row must not be wiped by the next automated run."""
    existing = [tracker_row()]
    manual = {f: '' for f in tracker_io.TRACKER_FIELDNAMES}
    manual.update({'Company': 'Career Fair', 'Link': 'https://fair.com/1',
                   'Status': 'Applied', 'Source': 'manual', 'Priority': '5'})
    rows = run_merge(existing + [manual], [scraped_row()])
    fair = [r for r in rows if r['Company'] == 'Career Fair']
    assert len(fair) == 1 and fair[0]['Status'] == 'Applied', rows


# --------------------------------------------------------------------------
# deadline tracker
# --------------------------------------------------------------------------

def _tracker_with(rows):
    """Write rows to a throwaway tracker CSV and return its path."""
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, 'tracker.csv')
    tracker_io.write_csv(path, rows, tracker_io.TRACKER_FIELDNAMES)
    return path


def test_expiring_a_listing_keeps_the_users_note():
    """Notes is a USER_FIELD, so closing an expired listing must not erase it."""
    from deadline_tracker import DeadlineTracker

    path = _tracker_with([tracker_row(**{
        'Application Deadline': '2020-01-01',
        'Notes': 'referred by Dana',
    })])
    DeadlineTracker(path).mark_expired_as_closed()

    row = tracker_io.read_csv(path)[0]
    assert row['Status'] == 'Closed', row
    assert 'referred by Dana' in row['Notes'], row['Notes']
    assert 'Deadline passed' in row['Notes'], row['Notes']


def test_expiring_twice_does_not_duplicate_the_stamp():
    """The daily run is idempotent: no note should grow on every pass."""
    from deadline_tracker import DeadlineTracker

    path = _tracker_with([tracker_row(**{'Application Deadline': '2020-01-01'})])
    DeadlineTracker(path).mark_expired_as_closed()
    first = tracker_io.read_csv(path)[0]['Notes']
    # Re-open the listing so the expiry branch runs a second time.
    rows = tracker_io.read_csv(path)
    rows[0]['Status'] = 'Not Applied'
    tracker_io.write_csv(path, rows, tracker_io.TRACKER_FIELDNAMES)
    DeadlineTracker(path).mark_expired_as_closed()

    assert tracker_io.read_csv(path)[0]['Notes'].count('Deadline passed') == 1, first


def test_expiry_leaves_applied_listings_alone():
    """An application already in flight is not closed by a passing deadline."""
    from deadline_tracker import DeadlineTracker

    path = _tracker_with([tracker_row(Status='Applied', **{
        'Application Deadline': '2020-01-01',
        'Notes': 'phone screen booked',
    })])
    DeadlineTracker(path).mark_expired_as_closed()

    row = tracker_io.read_csv(path)[0]
    assert row['Status'] == 'Applied', row
    assert row['Notes'] == 'phone screen booked', row['Notes']


# --------------------------------------------------------------------------
# sponsorship data table
# --------------------------------------------------------------------------

def test_sponsorship_db_has_no_duplicate_keys():
    """A repeated key silently discards one of the two tier ratings."""
    import ast
    tree = ast.parse(open('sponsorship_database.py', encoding='utf-8').read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [k.value for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        dupes = {k for k in keys if keys.count(k) > 1}
        assert not dupes, f'duplicate keys in sponsorship_database.py: {sorted(dupes)}'


def test_sponsorship_lookup_shape():
    from sponsorship_database import get_sponsorship_info
    for name in ('Google', 'google', '  Google  ', 'Totally Unknown Startup'):
        info = get_sponsorship_info(name)
        assert 'tier' in info and 'notes' in info, (name, info)


# --------------------------------------------------------------------------
# H-1B sponsorship data
# --------------------------------------------------------------------------

def test_h1b_normalize_employer():
    from h1b_data import normalize_employer as n
    assert n('GOOGLE LLC') == n('Google, Inc.') == 'google'
    assert n('AMAZON.COM SERVICES LLC') == 'amazon com'
    assert n('') == ''
    assert n(None) == ''


def test_h1b_lookup_requires_two_word_prefix():
    """A one-word prefix match let 'apex' claim 'apex systems staffing'."""
    import h1b_data
    # Keys are stored already normalized, so the fixture uses that form.
    employers = {'apex systems staffing': [900, 5], 'acme industries global': [10, 0]}
    fake = {'fiscal_year': 2023, 'employers': employers}
    original, h1b_data._cache = h1b_data._cache, fake
    try:
        # A single short word must not prefix-match a bigger unrelated employer.
        assert h1b_data.lookup('Apex') is None
        # Two words may, which is how "Amazon" reaches "AMAZON COM SERVICES".
        hit = h1b_data.lookup('Acme Industries')
        assert hit and hit['approvals'] == 10, hit
    finally:
        h1b_data._cache = original


def test_h1b_tier_scale():
    import h1b_data
    fake = {'fiscal_year': 2023, 'employers': {
        'bigfirm': [500, 2], 'midfirm': [40, 1], 'smallfirm': [8, 0],
        'tinyfirm': [2, 0], 'deniedfirm': [0, 6]}}
    original, h1b_data._cache = h1b_data._cache, fake
    try:
        assert h1b_data.sponsorship_tier('Bigfirm')[0] == 1
        assert h1b_data.sponsorship_tier('Midfirm')[0] == 2
        assert h1b_data.sponsorship_tier('Smallfirm')[0] == 3
        assert h1b_data.sponsorship_tier('Tinyfirm')[0] == 4
        # Filed but never approved is weaker than never having filed.
        assert h1b_data.sponsorship_tier('Deniedfirm')[0] == 5
        # Absent means absent, not tier 5 - the caller must be able to tell.
        assert h1b_data.sponsorship_tier('Unheardof') == (None, None)
    finally:
        h1b_data._cache = original


# --------------------------------------------------------------------------
# Workday
# --------------------------------------------------------------------------

def test_workday_parse_url():
    from workday import parse_url
    assert parse_url('https://barclays.wd3.myworkdayjobs.com/External_Career_Site/job/x') \
        == ('barclays', 'wd3', 'External_Career_Site')
    # Locale segments vary in case and must not be read as the site.
    assert parse_url('https://intel.wd1.myworkdayjobs.com/en-us/external/job/x') \
        == ('intel', 'wd1', 'external')
    assert parse_url('https://medline.wd5.myworkdayjobs.com/en-US/Medline/job/x') \
        == ('medline', 'wd5', 'Medline')
    assert parse_url('https://example.com/job/1') is None
    assert parse_url('') is None


def test_workday_detected_by_ats():
    import ats
    detected = ats.detect_ats(
        'https://barclays.wd3.myworkdayjobs.com/External_Career_Site/job/Pune/Data-Engineer_JR-1')
    assert detected is not None
    platform, org, job_path = detected
    assert platform == 'workday'
    assert org == 'barclays|wd3|External_Career_Site'
    assert job_path.startswith('/job/')


# --------------------------------------------------------------------------
# board discovery
# --------------------------------------------------------------------------

def test_board_discovery_extracts_tokens_from_links():
    import board_discovery
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'jobs.csv')
        tracker_io.write_csv(path, [
            {'Company': 'Acme', 'Link': 'https://job-boards.greenhouse.io/acme/jobs/1'},
            {'Company': 'Acme', 'Link': 'https://job-boards.greenhouse.io/acme/jobs/2'},
            {'Company': 'Globex', 'Link': 'https://jobs.lever.co/globex/abc'},
            {'Company': 'Nope', 'Link': 'https://nope.com/careers'},
        ], ['Company', 'Link'])
        found = board_discovery.candidates_from_trackers([(path, 'Link')])

    assert found == {('greenhouse', 'acme'): 'Acme', ('lever', 'globex'): 'Globex'}, found


def test_all_boards_includes_curated_and_discovered():
    import board_discovery
    from intl_boards import BOARDS
    combined = board_discovery.all_boards()
    assert len(combined) >= len(BOARDS)
    assert len(combined) == len(set(combined)), 'all_boards must not duplicate'


# --------------------------------------------------------------------------
# urgency
# --------------------------------------------------------------------------

def test_score_urgency_buckets():
    import urgency
    assert urgency.score_urgency(45, 45)[0] == urgency.URGENT
    assert urgency.score_urgency(30, 45)[0] == urgency.SOON
    assert urgency.score_urgency(18, 45)[0] == urgency.COMFORTABLE
    assert urgency.score_urgency(3, 45)[0] == urgency.FRESH
    # A zero or unknown expectation must not divide by zero.
    assert urgency.score_urgency(10, 0)[0] == urgency.FRESH


def test_lifetime_model_falls_back_to_prior_and_says_so():
    """A median over three closures is noise and must be labelled as unused."""
    import urgency
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, 't.db')
        _seed_lifetimes(db, [('a', 10), ('b', 20), ('c', 30)])
        model = urgency.lifetime_model(db)
    assert model['overall'] == urgency.DEFAULT_LIFETIME_DAYS
    assert 'prior' in model['overall_source']


def test_lifetime_model_uses_observations_once_there_are_enough():
    import urgency
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, 't.db')
        _seed_lifetimes(db, [(f'k{i}', days) for i, days in
                             enumerate([10, 20, 30, 40, 50, 60])])
        model = urgency.lifetime_model(db)
    assert model['overall'] == 35, model
    assert 'observed' in model['overall_source']


def _seed_lifetimes(db_path, pairs):
    """Insert listings that were first seen N days before they closed."""
    from datetime import datetime, timedelta
    import store
    now = datetime(2026, 9, 6)
    with store.connect(db_path) as conn:
        for key, days in pairs:
            first = (now - timedelta(days=days)).isoformat(timespec='seconds')
            conn.execute(
                'INSERT INTO listings (link_key, company, status, first_seen, last_seen)'
                ' VALUES (?, ?, ?, ?, ?)', (key, 'Acme', 'Closed', first, now.isoformat()))
            conn.execute(
                'INSERT INTO status_history (link_key, old_status, new_status, changed_at)'
                " VALUES (?, 'Not Applied', 'Closed', ?)", (key, now.isoformat(timespec='seconds')))


# --------------------------------------------------------------------------
# calibration
# --------------------------------------------------------------------------

def test_calibration_refuses_to_conclude_from_thin_data():
    """A rate over five applications is noise and must not be reported as signal."""
    import calibrate
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, 't.db')
        import store
        with store.connect(db) as conn:
            for i in range(5):
                conn.execute(
                    'INSERT INTO listings (link_key, company, role, score, priority,'
                    ' status, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?)',
                    (f'k{i}', 'Acme', 'SWE Intern', 80, '1', 'Applied', 'x', 'x'))
                conn.execute(
                    'INSERT INTO status_history (link_key, new_status, changed_at)'
                    " VALUES (?, 'Applied', '2026-09-01T00:00:00')", (f'k{i}',))
        records, verdict = calibrate.report(db)
    assert len(records) == 5
    assert verdict is None, 'must not reach a verdict on five applications'


def test_calibration_rate_ignores_pending_applications():
    """Counting undecided applications as rejections understates early results."""
    import calibrate
    records = [
        {'outcome': 'Offer'}, {'outcome': 'Rejected'}, {'outcome': 'Pending'},
    ]
    rates = calibrate.rates_by(records, lambda r: 'all')['all']
    assert rates['decided'] == 2
    assert rates['rate'] == 0.5


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failures = []
    for test in tests:
        try:
            test()
            print(f'  PASS  {test.__name__}')
        except Exception as e:
            failures.append((test.__name__, e))
            print(f'  FAIL  {test.__name__}: {e}')

    print(f'\n{len(tests) - len(failures)}/{len(tests)} passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
