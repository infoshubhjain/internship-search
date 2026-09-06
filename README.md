# Summer 2027 Internship Tracker

Two trackers, one rule: **the tracker is yours, and no automated run overwrites what you put in it.**

**🇺🇸 US tracker** — 851 opportunities from 4 community repos, scored and ranked, with sponsorship backed by real USCIS H-1B filing data.
**🌍 International tracker** — 138 CS internships across 19 countries, found by querying ~250 company job-board APIs directly, each classified for visa reachability and scored out of 100.

## Quick start

```bash
git clone https://github.com/infoshubhjain/internship-search.git
cd internship-search
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python3 update_all.py        # refresh the US tracker
python3 intl_tracker.py      # refresh the international tracker + report
streamlit run dashboard.py   # browse and apply

python3 urgency.py           # what is running out of time
python3 calibrate.py         # are the scores actually predicting responses?
```

Run everything from the repo root.

## Your data

`Summer2027_SWE_Tracker.csv` and `Summer2027_Intl_Tracker.csv` are the files that matter. Open them in Excel, Sheets, or the dashboard.

These columns are **yours**. Nothing automated writes over them:

`Status` · `Notes` · `Date Applied` · `Interview Date` · `Offer Status` · `Follow-up Date`

`Closed` is set automatically when a listing disappears upstream **and you never touched it**. If you had already applied, the row is left exactly as it was.

| Situation | What happens |
| --- | --- |
| A run is interrupted mid-write | Nothing lost — writes are atomic (temp file + rename) |
| Every source is down | The run aborts before merging; your tracker is untouched, not emptied |
| A job URL's tracking params change | Matched to your existing row; no duplicate |
| A board points many jobs at one URL | Still tracked separately, keyed on the board's job id |
| You add a row by hand | Carried through every future run |

---

## 🌍 International search

Built for the specific case: **UIUC CS sophomore, graduating May 2028, Indian citizen, currently in the US on F-1, wanting a paid Summer 2027 internship abroad.**

### How it finds roles

It queries company job-board APIs directly (Greenhouse, Lever, Ashby, Workday) rather than scraping aggregators, so results are *currently listed jobs at real companies*. Each board is fetched whole, then filtered: title looks like an internship → role is computer science → location is outside the US → season is plausibly Summer 2027.

**The board list grows by itself.** Every Greenhouse/Lever/Ashby/Workday job URL contains that company's board token, so `board_discovery.py` mines the trackers for tokens, validates each against the live API, and records it. The curated list of 88 became **164 boards plus 86 Workday tenants** without any manual curation — and every new listing scraped tomorrow is a candidate board for the day after.

```
python3 board_discovery.py     # mine tracker URLs for new boards
python3 workday.py --discover  # same for Workday tenants
```

### Visa classification

Every posting is read for work-authorization language and sorted into one of three categories, **with the sentence that decided it** recorded in the row:

| | Meaning |
| --- | --- |
| **A** | The employer states it sponsors visas, relocates, or welcomes international applicants |
| **B** | The posting says nothing either way — the usual case, and worth asking about |
| **C** | Existing local work rights, citizenship, or a clearance is required |

**Silence is not refusal.** A posting that says nothing is category B, never C. Restriction language is checked *before* support language, so diversity boilerplate cannot override an explicit "we do not sponsor".

Where a country has a known internship route (UK Government Authorised Exchange, Ireland's Atypical Working Scheme, Australia's Subclass 407, Germany's internship visa, and others), the route is named on the row — it exists as a legal pathway, which is not the same as an offer.

### Match score, out of 100

| Axis | Points |
| --- | --- |
| Role relevance | 25 |
| International eligibility | 25 |
| Compensation | 15 |
| Company and career value | 15 |
| Candidate eligibility | 10 |
| Location preference | 10 |

Two hard gates stop a good-looking score hiding a real problem: a non-CS role scores **0**, and a category C role is capped at **40**. A prestigious name in a great city cannot float a role you cannot legally take.

Pay that isn't published is scored as *unknown*, not unpaid — most employers simply don't publish intern rates.

### Output

`INTERNATIONAL_REPORT.md` organizes everything into four buckets:

- **🔥 Apply Immediately** — open, category A, scoring 65+
- **👀 Investigate Further** — strong, but visa eligibility unstated
- **📅 Monitor for Opening** — recurring programs not yet open
- **⚠️ Work Authorization Barrier** — kept visible, never recommended

Newly found roles are flagged 🆕 against the previous run, which is what makes a scheduled run act as continuous monitoring.

### Honest limits

- Coverage is whatever boards discovery has found so far. It grows on its own, but a company that has never appeared in any source is still invisible — add it to `intl_boards.py` directly.
- Visa categories are read from posting text. Some employers reuse one description across offices, so US-flavoured sponsorship language can appear on a London posting — the recorded evidence phrase is what lets you spot that.
- Many large employers have not opened Summer 2027 applications yet. Roles listed without a year are kept and marked as such, because boards routinely omit it.

---

## 🇺🇸 US tracker

### Sponsorship, from filings rather than guesses

The sponsorship table used to be hand-written, which is why two-thirds of listings resolved to "unknown" and why RTX and SpaceX were once labelled "full sponsorship".

It now reads **USCIS H-1B employer data** — the actual count of petitions each employer had approved. "Google: 2,460 H-1B approvals in FY2023" is evidence; "Google: full sponsorship" was a guess.

Sponsorship-known went from **24% to 54%** of listings. Precedence:

1. **Citizenship or clearance required** — a hard barrier. Booz Allen files plenty of H-1Bs and still needs a clearance.
2. **A listing that said "no sponsorship"** — negative knowledge the filing data cannot express.
3. **USCIS filing counts** — volume maps to a tier.
4. **The hand-curated table** — only for employers with no filing record.

The file refreshes only when USCIS publishes a new year (`--refresh-if-stale`), since it changes annually.

Caveat worth knowing: this is H-1B data, not CPT. A company that sponsors H-1B is very likely comfortable hosting an F-1 intern on CPT, but the inference runs one way — no filings lowers confidence rather than ruling a company out.

### Ranking

Listings are scored, not bucketed by first keyword match, then banded into priority 1–5. Every signal contributes: role category, sponsorship tier, whether it's a named underclassman program (STEP, Explore), and company engineering reputation. The `Score Reasons` column shows exactly why a listing ranked where it did.

Two things are hard-capped to priority 5:
- **Non-technical roles.** Product, design, marketing and finance internships come through the aggregator repos and used to rank as Priority 1 whenever the company name matched.
- **ITAR / cleared employers** (RTX, SpaceX, Lockheed, Booz Allen, and others). These generally require US citizenship, which is a hard barrier, not a sponsorship question.

### ATS enrichment

`enrich.py` queries Greenhouse, Lever, Ashby and SmartRecruiters for listings hosted there and writes back:

- **Real application deadlines** (Greenhouse publishes the field; others state it in the description)
- **Posted salary ranges**
- **Dead listings** — a 404 means the posting is gone, so it leaves the apply queue

A deadline you typed yourself is never overwritten; only empty ones are filled. Adding Workday took enrichment coverage from **20% to 48%** of listings and produced the first **71 real deadlines**.

### Urgency, when there is no deadline

Most employers never publish a deadline — the first enrichment pass found zero across 851 listings. That's a fact to design around, not a bug to fix.

`urgency.py` uses what the tracker actually observes: when it first saw each listing, and how long comparable listings survived before disappearing. A listing's age against that median is a real urgency signal.

```bash
python3 urgency.py --stats
```

It labels where each estimate came from — `published deadline 2026-09-12` versus `prior (45d); only 0 closures observed so far` — because a median over four observations is not a deadline and must not be displayed as one. Published deadlines always win where they exist.

### Are the scores any good?

The weights are judgment, not measurement. `status_history` records every application and outcome, so `calibrate.py` closes the loop: response rate by score band, priority, and role category.

It deliberately **refuses to conclude** below ~30 applications, and computes rates over *decided* applications only — counting pending ones as rejections would understate early results. If the spread between bands turns out flat, the ranking is decoration and should be reweighted.

### Application history

`store.py` mirrors the CSV into SQLite with a `status_history` table, which answers what a flat file cannot: what you applied to in a given week, how long employers took to respond, and when each listing first appeared. It records a history row only when a status actually changes, so running it on a schedule doesn't inflate anything.

```bash
python3 store.py   # funnel + applications per week
```

## Dashboard

`streamlit run dashboard.py`

- **Dashboard** — funnel metrics, priority breakdown, upcoming deadlines
- **Opportunities** — filter and paginate, one-click "Mark Applied"
- **Applications** — editable table of everything you've applied to
- **Urgency** — what is running out of time, and on what basis
- **International** — scored international roles with visa category, route, evidence and barriers
- **Analytics** — funnel, status distribution, priority heatmap, applications over time
- **Settings** — run an update, export CSV, check email config

Every button writes to disk. Changes survive the next automated update.

## Automation

GitHub Actions runs daily at 06:00 UTC: both test suites, then both pipelines, then commits. It refuses to commit if tests fail or a scrape comes back empty.

### Email alerts (optional)

```bash
export TRACKER_EMAIL=you@gmail.com
export TRACKER_EMAIL_PASSWORD=<gmail app password>
```

A gitignored `.env` works too. Alerts report exactly the listings the last merge added — the merge records them, so nothing is inferred. Unset means alerts are skipped; the trackers still work.

## Tests

```bash
python3 test_tracker.py        # 53 tests
python3 test_international.py  # 31 tests
```

Fully offline — no network, so they're a valid CI gate even when a company board is down. They cover each parser against fixed text, the country/visa/scoring classifiers against their known traps, and the merge guarantees that protect your data.

## Strategy notes

- Apply 5–10 per day, weekends included. Work down from the top of the file — it's sorted best-first.
- For international roles, category B is not a dead end. A short email asking whether they can host an intern on a training/exchange visa resolves it faster than guessing.
- Check work authorization before investing time; it's the binding constraint.
- See [`RECOMMENDATIONS.md`](RECOMMENDATIONS.md) for the longer strategy write-up.
