#!/usr/bin/env python3
"""
Run the full data pipeline: scrape every source, then merge into the tracker.

This is the single entry point used both locally and by GitHub Actions, so the
two cannot drift apart. Each stage is called in-process rather than shelled out,
so a failure in either aborts the run with a non-zero exit code instead of
letting a later stage operate on stale data.
"""
import sys

import board_discovery
import enhanced_scraper
import enrich
import h1b_data
import merge_internship_data
import store
import urgency
import workday


def main(ats_limit=150):
    print('=' * 60)
    print('Step 1/6: scraping internship sources')
    print('=' * 60)
    if enhanced_scraper.main() != 0:
        print('Scrape failed - tracker left unchanged.', file=sys.stderr)
        return 1

    print('=' * 60)
    print('Step 2/6: merging into tracker')
    print('=' * 60)
    if merge_internship_data.build_tracker() is None:
        print('Merge failed - tracker left unchanged.', file=sys.stderr)
        return 1

    print('=' * 60)
    print('Step 3/6: discovering new company boards and Workday tenants')
    print('=' * 60)
    # Every job URL just scraped may name a company board the international
    # search has never seen, so discovery runs on the fresh data.
    try:
        board_discovery.discover()
        _, new_tenants = workday.discover_tenants()
        print(f'  {len(new_tenants)} new Workday tenants')
    except Exception as e:
        print(f'Discovery skipped: {e}', file=sys.stderr)

    print('=' * 60)
    print('Step 4/6: refreshing H-1B sponsorship data if USCIS published a new year')
    print('=' * 60)
    try:
        h1b_data.refresh_if_stale()
        data = h1b_data.load_lookup()
        print(f"  H-1B lookup: FY{data['fiscal_year']}, "
              f"{len(data['employers'])} employers" if data else '  not built')
    except Exception as e:
        print(f'H-1B refresh skipped: {e}', file=sys.stderr)

    print('=' * 60)
    print('Step 5/6: enriching from ATS APIs (deadlines, salary, dead links)')
    print('=' * 60)
    # Enrichment is a bonus pass: a rate limit or an outage here should not
    # fail a run whose scrape and merge already succeeded.
    try:
        enrich.enrich_tracker(limit=ats_limit)
    except Exception as e:
        print(f'Enrichment skipped: {e}', file=sys.stderr)

    print('=' * 60)
    print('Step 6/6: syncing history and computing urgency')
    print('=' * 60)
    try:
        inserted, updated, transitions = store.sync_from_csv()
        print(f'  {inserted} new, {updated} updated, {transitions} status changes recorded')

        ranked, model = urgency.rank_open_listings()
        print(f"  lifetime model: {round(model['overall'])}d "
              f"({model['overall_source']})")
        critical = [r for r in ranked if r['level'] in (urgency.URGENT, urgency.SOON)]
        if critical:
            print(f'  {len(critical)} listing(s) are running out of time:')
            for item in critical[:5]:
                print(f"    [{item['level']}] {item['company']} - {item['role'][:40]} "
                      f"(seen {item['age_days']}d ago)")
    except Exception as e:
        print(f'History sync skipped: {e}', file=sys.stderr)

    print('\nDone. Updated:')
    print(f'  {enhanced_scraper.SCRAPED_FILE} (raw scrape)')
    print(f'  {merge_internship_data.TRACKER_FILE} (your tracker)')
    print(f'  {store.DB_PATH} (history)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
