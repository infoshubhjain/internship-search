#!/usr/bin/env python3
"""
Tests for the international internship agent.

Offline: every test feeds fixed text through the classifiers or fixed rows
through the merge. Nothing here touches the network, so the suite is a valid
gate in CI even when a company board is down.
"""
import os
import sys
import tempfile
from datetime import date

import geo
import intl_scoring
import intl_sources
import intl_tracker
import visa
from tracker_io import INTL_FIELDNAMES, INTL_USER_FIELDS, listing_key


# --------------------------------------------------------------------------
# geography
# --------------------------------------------------------------------------

def test_detect_country_basics():
    cases = {
        'London, UK': 'United Kingdom',
        'Sydney, Australia': 'Australia',
        'Dublin, Ireland': 'Ireland',
        'Singapore': 'Singapore',
        'Toronto, ON, Canada': 'Canada',
        'Amsterdam': 'Netherlands',
        'Zurich': 'Switzerland',
        'Bengaluru, India': 'India',
        'Auckland, New Zealand': 'New Zealand',
    }
    for location, expected in cases.items():
        assert geo.detect_country(location) == expected, (location, geo.detect_country(location))


def test_detect_country_disambiguates_shared_city_names():
    """The expensive mistakes: these cities exist in more than one country."""
    assert geo.detect_country('London, Ontario') == 'Canada'
    assert geo.detect_country('London, KY') == geo.US
    assert geo.detect_country('Cambridge, MA') == geo.US
    assert geo.detect_country('Cambridge, UK') == 'United Kingdom'
    assert geo.detect_country('Birmingham, AL') == geo.US
    assert geo.detect_country('Perth, WA, Australia') == 'Australia'


def test_detect_country_us_variants():
    for text in ['Multiple U.S. locations', 'U.S.A.', 'US', 'Various US locations',
                 'Mountain View, CA', 'New York, NY', 'US, MA, North Reading']:
        assert geo.detect_country(text) == geo.US, text


def test_detect_country_unknown_is_none_not_a_guess():
    """A wrong country is worse than an honest 'unknown'."""
    for text in ['Remote', '', None, 'Somewhere nice']:
        assert geo.detect_country(text) is None, text


def test_is_international():
    assert geo.is_international('London, UK')
    assert not geo.is_international('Austin, TX')
    assert not geo.is_international('Remote')


def test_country_tier():
    assert geo.country_tier('Australia') == 1
    assert geo.country_tier('Germany') == 2
    assert geo.country_tier('Brazil') == 3
    assert geo.country_tier(geo.US) is None


# --------------------------------------------------------------------------
# visa classification
# --------------------------------------------------------------------------

def test_visa_category_c_on_explicit_restriction():
    restrictions = [
        'We are unable to offer visa sponsorship for this position.',
        'Sponsorship is not available for this role.',
        'You must already have the right to work in Australia.',
        'Applicants must be Australian citizens only.',
        'This role requires security clearance.',
    ]
    for text in restrictions:
        result = visa.classify(text, 'Acme', 'Australia')
        assert result['category'] == visa.CATEGORY_C, (text, result)
        assert result['evidence'], text


def test_visa_category_a_on_explicit_support():
    supports = [
        'Visa sponsorship is available for this role.',
        'We provide relocation assistance for international hires.',
        'International students are welcome to apply.',
        'We will support your work permit application.',
    ]
    for text in supports:
        result = visa.classify(text, 'Acme', 'Ireland')
        assert result['category'] == visa.CATEGORY_A, (text, result)


def test_visa_defaults_to_b_when_silent():
    """Silence is not refusal. Most postings say nothing and must stay open."""
    result = visa.classify('Join our team building great products.', 'Acme', 'Singapore')
    assert result['category'] == visa.CATEGORY_B
    assert result['visa_route'], 'a known route should still be surfaced'


def test_visa_restriction_beats_support_language():
    """Diversity boilerplate must not override an explicit no-sponsorship line."""
    text = ('International applicants are welcome. '
            'However, we are unable to offer visa sponsorship for this role.')
    assert visa.classify(text, 'Acme', 'United Kingdom')['category'] == visa.CATEGORY_C


def test_visa_restricted_employers():
    for company in ['Helsing', 'Anduril', 'BAE Systems']:
        result = visa.classify('We welcome international applicants!', company, 'Germany')
        assert result['category'] == visa.CATEGORY_C, company


def test_english_working_language():
    assert visa.english_working_language('', 'United Kingdom') == 'Yes'
    assert visa.english_working_language('', 'Germany') == 'Unclear'
    assert visa.english_working_language('Our working language is English', 'Germany') == 'Yes'
    assert visa.english_working_language('Fluent in German required', 'Germany') == 'No'


# --------------------------------------------------------------------------
# internship / season filters
# --------------------------------------------------------------------------

def test_looks_like_internship():
    for title in ['Software Engineer Intern', 'Summer Analyst 2027',
                  'Placement Student', 'Working Student Backend', 'SWE Co-op']:
        assert intl_sources.looks_like_internship(title), title
    for title in ['Senior Engineer', 'Internal Audit Analyst',
                  'Internship Program Manager', 'New Graduate Software Engineer', '']:
        assert not intl_sources.looks_like_internship(title), title


def test_internship_detection_handles_underscore_separators():
    """Job titles use underscores; \\b does not fire inside "Intern_OnSite"."""
    assert intl_sources.looks_like_internship('Summer 2027 Software Intern_OnSite')
    assert intl_sources.looks_like_internship('Software Engineering Co-op_Fall 2027')
    assert intl_sources.looks_like_internship('Coop Engineer')
    # But a word that merely contains the letters must not match.
    assert not intl_sources.looks_like_internship('Cooperative Marketing Lead')


def test_intern_conversion_reqs_are_not_internships():
    """"2026 Intern Conversion: 2027 FT Software Engineer" is a full-time hire."""
    assert not intl_sources.looks_like_internship(
        '2026 Intern Conversion: 2027 FT Software Engineer')
    assert not intl_sources.looks_like_internship('2027 FT Software Engineer')
    # Lowercase "ft" inside ordinary words must not trigger the full-time rule.
    assert intl_sources.looks_like_internship('Software Craft Intern')


def test_full_time_campus_roles_are_not_internships():
    """Campus recruiting posts matched pairs; only the intern half qualifies."""
    assert not intl_sources.looks_like_internship('Campus ML Research Engineer (Full-Time)')
    assert intl_sources.looks_like_internship('Campus ML Research Engineer (Intern)')


def test_season_status():
    today = date(2026, 9, 6)
    assert intl_sources.season_status('SWE Intern Summer 2027', '', today) == 'summer-2027'
    assert intl_sources.season_status('SWE Intern', '', today) == 'undated'
    assert intl_sources.season_status('SWE Intern Summer 2026', '', today) == 'stale'


def test_filter_keeps_only_international_cs_internships():
    postings = [
        {'title': 'Software Engineer Intern', 'location': 'London, UK', 'description': ''},
        {'title': 'Software Engineer Intern', 'location': 'Austin, TX', 'description': ''},
        {'title': 'Marketing Intern', 'location': 'London, UK', 'description': ''},
        {'title': 'Senior Software Engineer', 'location': 'London, UK', 'description': ''},
        {'title': 'SWE Intern Summer 2026', 'location': 'London, UK', 'description': ''},
    ]
    kept = intl_sources.filter_international_internships(postings)
    assert len(kept) == 1, [k['title'] for k in kept]
    assert kept[0]['country'] == 'United Kingdom'
    assert kept[0]['category'] == 'Software Engineering'


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def test_score_components_sum_to_100_max():
    total, breakdown, _ = intl_scoring.score(
        role='Software Engineer Intern', country='Australia',
        visa_category=visa.CATEGORY_A, paid=True, company='Atlassian',
        employment_type='Intern', english='Yes', is_2027=True)
    assert total == 100, (total, breakdown)


def test_score_zeroes_non_cs_roles():
    """A prestigious marketing internship is still not in scope."""
    total, _, _ = intl_scoring.score(
        role='Marketing Intern', country='Ireland', visa_category=visa.CATEGORY_A,
        paid=True, company='Stripe', english='Yes', is_2027=True)
    assert total == 0, total


def test_score_caps_work_authorization_barrier():
    """Category C must never be presented as a top recommendation."""
    total, _, barriers = intl_scoring.score(
        role='Backend Engineer Intern', country='Singapore',
        visa_category=visa.CATEGORY_C, paid=True, company='Grab',
        english='Yes', is_2027=True)
    assert total <= 40, total
    assert any('authorization' in b for b in barriers)


def test_score_treats_undisclosed_pay_as_unknown_not_unpaid():
    unknown, _, _ = intl_scoring.score(role='Software Engineer Intern', country='Ireland',
                                       visa_category=visa.CATEGORY_B, paid=None)
    unpaid, _, _ = intl_scoring.score(role='Software Engineer Intern', country='Ireland',
                                      visa_category=visa.CATEGORY_B, paid=False)
    paid, _, _ = intl_scoring.score(role='Software Engineer Intern', country='Ireland',
                                    visa_category=visa.CATEGORY_B, paid=True)
    assert paid > unknown > unpaid


def test_score_penalises_phd_only_roles():
    phd, _, barriers = intl_scoring.score(role='PhD Research Intern', country='United Kingdom',
                                          visa_category=visa.CATEGORY_A, paid=True)
    undergrad, _, _ = intl_scoring.score(role='Software Engineer Intern', country='United Kingdom',
                                         visa_category=visa.CATEGORY_A, paid=True)
    assert undergrad > phd
    assert any('PhD' in b for b in barriers)


# --------------------------------------------------------------------------
# row building and merge
# --------------------------------------------------------------------------

def posting(**kw):
    base = {
        'company': 'Acme', 'title': 'Software Engineer Intern',
        'location': 'London, UK', 'link': 'https://acme.com/jobs/1',
        'description': 'Visa sponsorship is available. Paid internship.',
        'posted_at': '2026-09-01', 'employment_type': 'Intern',
        'country_hint': '', 'salary': '', 'source': 'greenhouse:acme',
        'external_id': '1', 'country': 'United Kingdom',
        'category': 'Software Engineering', 'season': 'summer-2027',
    }
    base.update(kw)
    return base


def test_build_row_populates_every_column():
    row = intl_tracker.build_row(posting())
    assert set(row) == set(INTL_FIELDNAMES), set(INTL_FIELDNAMES) ^ set(row)
    assert row['Country'] == 'United Kingdom'
    assert row['City'] == 'London'
    assert row['Visa Category'] == visa.CATEGORY_A
    assert row['Paid'] == 'Yes'
    assert int(row['Match Score']) > 0
    assert row['Bucket'] == intl_tracker.BUCKET_APPLY


def test_build_row_buckets_barrier_roles():
    row = intl_tracker.build_row(posting(
        description='You must already have the right to work in the UK.'))
    assert row['Visa Category'] == visa.CATEGORY_C
    assert row['Bucket'] == intl_tracker.BUCKET_BARRIER


def test_listing_key_separates_jobs_sharing_one_url():
    """Some boards point every posting at one careers page."""
    a = {'Source': 'greenhouse:jump', 'External ID': '1', 'Link': 'https://x.com/careers'}
    b = {'Source': 'greenhouse:jump', 'External ID': '2', 'Link': 'https://x.com/careers'}
    assert listing_key(a) != listing_key(b)
    # And a listing with no id still keys off its link.
    assert listing_key({'Link': 'https://x.com/jobs/9'}) == 'x.com/jobs/9'


def test_intl_merge_preserves_user_columns():
    existing = intl_tracker.build_row(posting())
    existing.update({'Status': 'Applied', 'Notes': 'emailed recruiter',
                     'Date Applied': '2026-09-05', 'Offer Status': 'Pending'})
    merged, added, closed = intl_tracker.merge_rows([existing], [intl_tracker.build_row(posting())])

    assert len(merged) == 1 and not added and not closed
    for field in INTL_USER_FIELDS:
        assert merged[0][field] == existing[field], field


def test_intl_merge_closes_but_keeps_delisted_rows():
    gone = intl_tracker.build_row(posting(external_id='99', link='https://acme.com/jobs/99'))
    applied = intl_tracker.build_row(posting(external_id='98', link='https://acme.com/jobs/98'))
    applied['Status'] = 'Applied'

    merged, _, closed = intl_tracker.merge_rows([gone, applied], [intl_tracker.build_row(posting())])
    by_id = {r['External ID']: r for r in merged}

    assert by_id['99']['Status'] == 'Closed'
    assert by_id['98']['Status'] == 'Applied', 'an applied row must never be closed'
    assert closed == 1
    assert len(merged) == 3


def test_intl_merge_reports_new_rows():
    merged, added, _ = intl_tracker.merge_rows([], [intl_tracker.build_row(posting())])
    assert len(added) == 1 and len(merged) == 1


def test_report_renders_all_buckets():
    rows = [
        intl_tracker.build_row(posting()),
        intl_tracker.build_row(posting(
            external_id='2', description='You must have the right to work in the UK.')),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'report.md')
        intl_tracker.render_report(rows, added=rows, path=path)
        text = open(path, encoding='utf-8').read()

    assert intl_tracker.BUCKET_APPLY in text
    assert intl_tracker.BUCKET_BARRIER in text
    assert 'Acme' in text and 'Summer 2027' in text
    # The honest-limits section must survive; it is what stops the report
    # being read as an exhaustive search.
    assert 'honest limits' in text.lower()


def test_detect_paid():
    assert intl_tracker.detect_paid('', '50,000 GBP') is True
    assert intl_tracker.detect_paid('This is a paid internship.', '') is True
    assert intl_tracker.detect_paid('This is an unpaid position.', '') is False
    assert intl_tracker.detect_paid('Join our team.', '') is None


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failures = []
    for test in tests:
        try:
            test()
            print(f'  PASS  {test.__name__}')
        except Exception as e:
            failures.append(test.__name__)
            print(f'  FAIL  {test.__name__}: {e}')
    print(f'\n{len(tests) - len(failures)}/{len(tests)} passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
