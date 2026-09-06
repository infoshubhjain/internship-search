# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Two internship trackers sharing one set of machinery:

- **US tracker** (`Summer2027_SWE_Tracker.csv`) — aggregated from community GitHub repos.
- **International tracker** (`Summer2027_Intl_Tracker.csv`) — built by querying company job-board APIs directly, filtered to CS internships outside the US, with visa classification and a 0–100 match score.

Flat modules at the repo root, no packages. Scripts use hardcoded relative filenames, so **run everything from the repo root**.

## Commands

```bash
pip install -r requirements.txt

python3 update_all.py          # US pipeline, 6 steps (see below)
python3 intl_tracker.py        # international agent: boards + Workday -> classify -> score -> report
streamlit run dashboard.py     # UI for both trackers

python3 test_tracker.py        # 53 tests, offline
python3 test_international.py  # 31 tests, offline

python3 enrich.py --limit 200         # ATS enrichment alone
python3 store.py                      # sync CSV -> SQLite, funnel + weekly applications
python3 urgency.py [--stats]          # what is running out of time
python3 calibrate.py                  # do the scores predict outcomes yet?
python3 board_discovery.py [--dry-run]  # find new company boards in tracker URLs
python3 workday.py --discover|--check   # find/verify Workday tenants
python3 h1b_data.py --refresh|--refresh-if-stale|--check Google
python3 intl_sources.py --check       # verify every board still responds
python3 intl_tracker.py --report      # re-render the report without re-scraping
python3 master_integration.py <update|international|deadlines|alerts|weekly|backup|security|all>
```

`update_all.py` runs: scrape → merge → discover boards/tenants → refresh H-1B if stale →
ATS enrich → sync history + urgency. Each later step is wrapped so a failure there cannot
undo a successful scrape and merge.

Single test: `python3 -c "import test_tracker as t; t.test_merge_preserves_user_columns()"`.

Lint: `python3 -m pyflakes *.py` — clean as of the last change; keep it that way.

## The invariant that matters

Both tracker CSVs hold the user's real application history. **No automated run may destroy it.**

`tracker_io.USER_FIELDS` / `INTL_USER_FIELDS` list the user-owned columns. Both merges (`merge_internship_data.merge_row`, `intl_tracker.merge_rows`) refresh every *other* column and leave those alone. A listing that disappears upstream is marked `Closed`, never deleted, and never if the user already applied.

This is not theoretical — the merge used to regenerate the tracker from scratch daily. Tests `test_merge_preserves_user_columns`, `test_merge_closes_but_never_deletes_delisted_rows`, `test_intl_merge_preserves_user_columns` and `test_intl_merge_closes_but_keeps_delisted_rows` pin it. Do not weaken them.

Corollaries:
- All writes go through `tracker_io.write_csv()` — temp file plus `os.replace`. A partial write must never truncate.
- An empty scrape aborts before the merge in both pipelines. Otherwise a bad upstream day closes every listing.
- Identity is `tracker_io.listing_key()`: `Source#External ID` when the board gives a job id, else the normalized link. **Link alone is not enough** — some boards (Jump Trading) point every posting at one careers page, which collapsed 25 jobs into 1.

## Module map

| Module | Role |
| --- | --- |
| `tracker_io.py` | paths, schemas, atomic writes, link normalization, row editing |
| `roles.py` | `classify_role(title)` → technical category or `None`. Gate for both pipelines |
| `scoring.py` | US priority scoring (0–100 → priority 1–5) |
| `sponsorship_database.py` | company → CPT/OPT/H-1B tier, plus `requires_citizenship()` |
| `enhanced_scraper.py` | 4 GitHub aggregator repos, one parser each |
| `merge_internship_data.py` | US merge, priority, new-listing record |
| `ats.py` | Greenhouse/Lever/Ashby/SmartRecruiters/Workday job APIs |
| `workday.py` | Workday CXS API; tenants auto-discovered from tracker URLs |
| `h1b_data.py` | USCIS H-1B filing counts → sponsorship evidence |
| `board_discovery.py` | mines tracker URLs for new company board tokens |
| `urgency.py` | expected-lifetime model; what is running out of time |
| `calibrate.py` | do the scores predict responses? |
| `enrich.py` | deadlines, salary, dead-link detection into the US tracker |
| `store.py` | SQLite mirror + `status_history` (the analytics CSV cannot do) |
| `geo.py` | free-text location → country, region tiers |
| `visa.py` | posting text → visa category A/B/C with evidence |
| `intl_scoring.py` | 100-point match score for the international candidate profile |
| `intl_boards.py` | the verified company board list |
| `intl_sources.py` | fetch whole boards, filter to international CS internships |
| `intl_tracker.py` | the international agent: build rows, merge, render report |

Standalone tools not in either pipeline: `company_research.py`, `skill_gap_analysis.py`, `template_library.py`, `resume_version_control.py`, `ab_testing.py`, `calendar_integration.py`.

## Data files that are generated, not hand-written

`discovered_boards.json`, `workday_tenants.json` and `h1b_sponsors.json.gz` are all
machine-generated and committed. Do not edit them by hand — regenerate with the
commands above. `intl_boards.py` is the one hand-curated list, and every token in it
was probed live.

## Gotchas that caused real bugs

**Sponsorship lookup.** `get_sponsorship_info` resolves in a fixed precedence: citizenship/clearance requirement → hand-recorded *non*-sponsor → USCIS H-1B filing counts → hand-curated table → unknown. Real filing data beats guesses, but negative knowledge from a listing ("we do not sponsor") beats volume, and a clearance requirement beats everything — Booz Allen files plenty of H-1Bs and still needs citizenship.

Matching is word-boundary based, longest key first. Substring matching let the `'x'` key (Twitter/X) claim RTX, SpaceX, Cox and Apex as "full sponsorship", and `'ge'` claim General Dynamics. Keys under 4 chars only match as whole words. Never reintroduce substring matching here.

**H-1B name matching** needs a two-word prefix. A one-word prefix let "apex" match "apex systems staffing" and inherit 900 approvals. `h1b_data.sponsorship_tier` returns `(None, None)` for an absent employer rather than tier 5, so callers can tell "no record" from "checked, unknown".

**Word boundaries and underscores.** Job titles contain underscores (`Intern_OnSite`, `Co-op_Fall`), and `_` is a word character, so `\bintern\b` does **not** match. `intl_sources` uses explicit separator classes instead. Conversely `FT` is matched case-sensitively — lowercase `ft` appears inside ordinary words.

**Citizenship is rechecked by company, not trusted from a row.** `scoring.score_listing` calls `requires_citizenship(company)` even when a cached `sponsorship_tier` is passed, because a stale scrape can carry a wrong tier. ITAR/cleared employers are tier 6 and capped at priority 5.

**Scraper parsers.** Continuation rows (`↳`) mean "same company as above" — `clean_cell` reduces the arrow to `''`, and an empty company inherits `last_company`. SimplifyJobs `<tr>` blocks span multiple lines, so split on `</tr>`. Emoji prefixes (🔥) must be stripped or the sponsorship lookup misses. A parser returning zero rows logs a **warning**.

**Dates.** Sources send ISO, `Aug 21` (no year), and relative ages (`3d`). `parse_date_posted` normalizes all to ISO because downstream parses with `date.fromisoformat`.

**Country detection.** Order is: explicit country name → US state marker → unambiguous city. London is also in Ontario; Cambridge and Birmingham are also in the US. Two-letter codes are checked last because they collide with US state codes (`IN`, `CA`, `DE`). `detect_country` returns `None` rather than guessing — an honest unknown beats a wrong country.

**Visa classification.** Restrictions are checked before support language, so diversity boilerplate cannot override an explicit "we do not sponsor". Silence is category **B**, not C. Every verdict carries the `evidence` phrase that produced it — keep that, it is how a wrong call gets caught. Note that some employers reuse one description across offices, so US-flavoured sponsorship text can appear on a London posting; the evidence field is what makes that visible.

**Streamlit cache keys.** `load_data(mtime)` must not name that argument `_mtime` — Streamlit excludes underscore-prefixed params from the cache key, which pins the app to the first version of the file it read.

**Adding a company board.** Usually unnecessary — `board_discovery.py` mines every Greenhouse/Lever/Ashby URL in the trackers for its board token, validates it, and records it in `discovered_boards.json`. `intl_sources.scrape_all` iterates `board_discovery.all_boards()` (curated + discovered), *not* `intl_boards.BOARDS`. To add one by hand anyway, put it in `intl_boards.py` and run `python3 intl_sources.py --check`.

**Workday search cost.** Measured on four tenants: one search term over two pages returned 42 postings in 20s; five terms over five pages returned 45 in 76s. Nearly four times the requests for 7% more results — hence `SEARCH_TERMS = ['intern']` and `MAX_PAGES = 2`. Don't raise these without re-measuring.

**Deadlines and urgency.** Scraping deadlines found 0 of 851, because employers mostly don't publish them; Workday's `endDate` later supplied 71. `urgency.py` fills the rest from observed listing lifetimes (`first_seen` → status became `Closed`), falling back to a stated 45-day prior below `MIN_OBSERVATIONS`. It labels which basis it used — never present a prior as if it were a published deadline.

**Calibration honesty.** `calibrate.py` refuses to reach a verdict below `MIN_TOTAL` applications and `MIN_PER_BAND` per band, and computes rates over *decided* applications only — counting pending ones as rejections understates early results.

## Conventions

- Import paths from `tracker_io`; don't re-hardcode CSV filenames.
- Secrets come from the environment or a gitignored `.env` via `SecurityManager.get_secret()`. Email uses `TRACKER_EMAIL` / `TRACKER_EMAIL_PASSWORD` and skips silently when unset.
- Logging goes to `internship_tracker.log` (gitignored) and stderr.
- Dashboard writes go through `tracker_io.update_row()` / `append_row()`, which reject non-user-editable columns. Keep write logic there so it stays testable without a browser.
- `.github/workflows/update-internships.yml` runs both test suites before either pipeline, then commits both trackers. Renaming a script or output file means updating its `git add` list.
