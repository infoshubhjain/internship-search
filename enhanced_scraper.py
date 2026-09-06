#!/usr/bin/env python3
"""
Enhanced scraper with additional GitHub data sources and improved data processing
"""
import requests
import re
import sys
import time
import logging
from datetime import date, datetime, timedelta
from sponsorship_database import get_sponsorship_info
from tracker_io import SCRAPED_FILE, normalize_link, write_csv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('internship_tracker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

SCRAPED_FIELDNAMES = ['company', 'role', 'location', 'link', 'no_sponsorship', 'source',
                      'sponsorship_tier', 'sponsorship_notes', 'date_posted']

def scrape_github_repo(url, repo_name, parser):
    """Fetch one source and parse it with the parser it needs."""
    try:
        logger.info(f"Scraping {repo_name}...")
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch {repo_name}: {response.status_code}")
            return []
        
        content = response.text
        internships = []
        
        # Try different parsing strategies based on repo format
        internships = parser(content)

        if not internships:
            # A parser silently returning nothing means the upstream README was
            # restructured. Warn loudly rather than quietly shipping a smaller
            # tracker.
            logger.warning(f"{repo_name}: parsed 0 internships - check upstream format")
        else:
            logger.info(f"Found {len(internships)} internships from {repo_name}")
        return internships
        
    except Exception as e:
        logger.error(f"Error scraping {repo_name}: {e}")
        return []

def make_entry(company, role, location, link, no_sponsorship, source, date_posted=''):
    """Build one scraped record, enriched with sponsorship info."""
    info = get_sponsorship_info(company)
    return {
        'company': company.strip(),
        'role': role.strip(),
        'location': location.strip(),
        'link': link.split('?')[0].strip(),
        'no_sponsorship': no_sponsorship,
        'source': source,
        'sponsorship_tier': info['tier'],
        'sponsorship_notes': info['notes'],
        'date_posted': parse_date_posted(date_posted),
    }


def parse_date_posted(text, today=None):
    """Normalize an upstream "date posted" cell to ISO YYYY-MM-DD.

    Sources disagree on format: ApplyGuy sends ISO dates, vanshb03 sends
    "Aug 21" with no year, and SimplifyJobs sends a relative age like "3d".
    Downstream code (deadline alerts, dashboard sorting) parses these with
    date.fromisoformat, so anything not normalized here is silently dropped.
    Returns '' when the text cannot be interpreted.
    """
    text = (text or '').strip()
    if not text:
        return ''
    today = today or date.today()

    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        pass

    # Relative age, e.g. "3d" / "2mo".
    rel = re.fullmatch(r'(\d+)\s*(d|w|mo|y)', text, re.I)
    if rel:
        amount = int(rel.group(1))
        days = {'d': 1, 'w': 7, 'mo': 30, 'y': 365}[rel.group(2).lower()]
        return (today - timedelta(days=amount * days)).isoformat()

    # "Aug 21" / "Aug 21, 2026" - a bare month/day has no year, so assume the
    # most recent occurrence rather than defaulting to a future date.
    match = re.match(r'([A-Za-z]{3,9})\s+(\d{1,2})(?:,\s*(\d{4}))?$', text)
    if match:
        month_name, day_str, year_str = match.groups()
        try:
            month = datetime.strptime(month_name[:3], '%b').month
        except ValueError:
            return ''
        try:
            if year_str:
                return date(int(year_str), month, int(day_str)).isoformat()
            parsed = date(today.year, month, int(day_str))
            if parsed > today:
                parsed = date(today.year - 1, month, int(day_str))
            return parsed.isoformat()
        except ValueError:
            return ''

    return ''


def clean_cell(cell):
    """Strip markdown/HTML decoration from a table cell, keeping the text."""
    cell = re.sub(r'<br\s*/?>', ', ', cell)
    cell = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', cell)   # [text](url) -> text
    cell = re.sub(r'<[^>]+>', '', cell)                     # strip tags
    cell = cell.replace('**', '')                           # markdown bold
    cell = re.sub(r'\s+', ' ', cell).strip(' ,')
    # Some repos prefix hot listings with an emoji ("\U0001f525 Google"), which
    # would otherwise become part of the company name and break the
    # sponsorship and priority lookups that match on it.
    return re.sub(r'^[^\w(]+\s*', '', cell).strip()


def is_excluded(row_text):
    """True if the listing is closed or not open to visa holders.

    Upstream repos flag these with emoji: closed, US-citizenship-only, and
    (separately) no-sponsorship. Only the first two disqualify the listing;
    no-sponsorship is recorded on the row instead so the user can still see it.
    """
    return '\U0001f512' in row_text or '\U0001f1fa\U0001f1f8' in row_text


def parse_vansh_format(content, source='vansh_repo'):
    """Parse the vanshb03 markdown table.

    Rows whose company cell is the continuation arrow belong to the company
    named in the last full row; without carrying that forward, roughly a
    quarter of all listings end up filed under a company literally named
    with the arrow character.
    """
    internships = []

    table_start = content.find('| Company | Role | Location | Application/Link | Date Posted |')
    if table_start == -1:
        logger.warning('vansh table header not found - upstream format may have changed')
        return internships

    last_company = None
    for row in content[table_start:].split('\n'):
        if not row.startswith('|') or row.startswith('| Company') or row.startswith('| ---'):
            continue
        parts = [part.strip() for part in row.split('|')]
        if len(parts) < 6:
            continue

        company_cell, role_cell, location_cell, link_cell = parts[1], parts[2], parts[3], parts[4]
        date_posted = clean_cell(parts[5]) if len(parts) > 5 else ''

        company = clean_cell(company_cell)
        # clean_cell reduces a bare continuation arrow to an empty string, so an
        # empty company here means "same company as the row above".
        if not company:
            company = last_company
        else:
            last_company = company
        if not company:
            continue

        url_match = re.search(r'href="([^"]+)"', link_cell)
        if not url_match:
            # No apply link: the listing is closed or link-less, not trackable.
            continue
        if is_excluded(row):
            continue

        internships.append(make_entry(
            company, clean_cell(role_cell), clean_cell(location_cell),
            url_match.group(1), '\U0001f6c2' in row, source, date_posted,
        ))

    return internships


def parse_applyguy_format(content):
    """Parse the ApplyGuy JSON feed."""
    import json
    internships = []

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.error('Failed to parse ApplyGuy JSON')
        return internships

    for job in data.get('jobs', []):
        if job.get('category') != 'Software Engineering':
            continue
        season = (job.get('season') or '').lower()
        title = (job.get('title') or '').lower()
        if not ('2027' in season or '2027' in title or 'summer' in season):
            continue

        link = job.get('listingUrl') or job.get('url') or ''
        # applyguy.ai links are interstitials, not the employer's application.
        if not link or 'applyguy.ai' in link:
            continue

        internships.append(make_entry(
            job.get('company', ''), job.get('title', ''), job.get('location', ''),
            link, False, 'applyguy_repo', job.get('posted', '') or '',
        ))

    return internships


def parse_simplify_format(content):
    """Parse the SimplifyJobs/pittcsc README HTML table.

    Each <tr> spans several lines, so the block must be reassembled before the
    cells can be read; scanning line by line finds no company at all.
    """
    internships = []

    swe_section = content.find('## \U0001f4bb Software Engineering Internship Roles')
    if swe_section == -1:
        logger.warning('SimplifyJobs SWE section not found - upstream format may have changed')
        return internships

    next_section = content.find('\n## ', swe_section + 10)
    swe_content = content[swe_section:next_section] if next_section != -1 else content[swe_section:]

    last_company = None
    for block in swe_content.split('</tr>'):
        if '<td' not in block:
            continue
        cells = re.findall(r'<td[^>]*>(.*?)</td>', block, re.S)
        if len(cells) < 4:
            continue

        # A continuation row ("same company as above") has an arrow for its
        # company cell, which clean_cell reduces to an empty string.
        company = clean_cell(cells[0])
        if not company:
            company = last_company
        else:
            last_company = company
        if not company:
            continue

        if is_excluded(block):
            continue

        # The application cell holds the employer link plus Simplify's own
        # referral link and image assets; only the employer link is wanted.
        link = next((
            url for url in re.findall(r'href="([^"]+)"', cells[3])
            if not any(skip in url for skip in ('simplify.jobs', 'imgur', 'github.com'))
        ), None)
        if not link:
            continue

        internships.append(make_entry(
            company, clean_cell(cells[1]), clean_cell(cells[2]),
            link, '\U0001f6c2' in block, 'simplify_repo', clean_cell(cells[4]) if len(cells) > 4 else '',
        ))

    return internships


def parse_generic_markdown(content, source='generic'):
    """Parse a plain markdown table with Company/Role/Location/Apply columns.

    Column order varies between repos, so the header row is read to locate
    them rather than assuming fixed positions.
    """
    internships = []
    rows = [line for line in content.split('\n') if line.strip().startswith('|')]
    if not rows:
        return internships

    header = [clean_cell(c).lower() for c in rows[0].split('|')]

    def find_column(*names):
        for index, name in enumerate(header):
            if any(n in name for n in names):
                return index
        return None

    col_company = find_column('company')
    col_role = find_column('role', 'position', 'title')
    col_location = find_column('location')
    col_link = find_column('apply', 'link', 'application')
    col_date = find_column('added', 'date', 'posted', 'age')
    if col_company is None or col_role is None or col_link is None:
        logger.warning('%s: could not identify table columns', source)
        return internships

    last_company = None
    for row in rows[1:]:
        cells = row.split('|')
        needed = max(c for c in (col_company, col_role, col_location, col_link) if c is not None)
        if len(cells) <= needed:
            continue
        company = clean_cell(cells[col_company])
        # A markdown separator row ("| --- | --- |"). An *empty* company cell is
        # not a separator - it is a continuation row - so require actual dashes.
        if company and set(company) <= {'-', ':'}:
            continue
        if not company:          # continuation row: same company as above
            company = last_company
        else:
            last_company = company
        if not company or is_excluded(row):
            continue

        link_match = re.search(r'\]\((https?://[^)]+)\)', cells[col_link]) or \
            re.search(r'href="([^"]+)"', cells[col_link])
        if not link_match:
            continue

        location = clean_cell(cells[col_location]) if col_location is not None else ''
        date_posted = clean_cell(cells[col_date]) if col_date is not None and col_date < len(cells) else ''
        internships.append(make_entry(
            company, clean_cell(cells[col_role]), location,
            link_match.group(1), '\U0001f6c2' in row, source, date_posted,
        ))

    return internships


def scrape_all_sources():
    """Scrape all configured GitHub sources"""
    # pittcsc/Summer2027-Internships redirects to the SimplifyJobs repo and
    # serves byte-identical content, so it is deliberately not listed here.
    sources = [
        ('https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/README.md',
         'vanshb03', parse_vansh_format),
        ('https://raw.githubusercontent.com/ApplyGuy/2027-Internships/main/data/internships.json',
         'ApplyGuy', parse_applyguy_format),
        ('https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md',
         'SimplifyJobs', parse_simplify_format),
        ('https://raw.githubusercontent.com/sndsh404/summer-2027-internships/main/README.md',
         'sndsh404', lambda c: parse_generic_markdown(c, 'sndsh404_repo')),
    ]

    all_internships = []

    for url, repo_name, parser in sources:
        try:
            all_internships.extend(scrape_github_repo(url, repo_name, parser))
            time.sleep(1)  # be polite to raw.githubusercontent.com
        except Exception as e:
            logger.error(f"Failed to scrape {repo_name}: {e}")

    # Deduplicate across sources. The same posting appears in several repos with
    # different tracking parameters, so compare normalized links.
    seen_links = set()
    unique_internships = []

    for internship in all_internships:
        key = normalize_link(internship['link'])
        if key and key not in seen_links:
            seen_links.add(key)
            unique_internships.append(internship)

    logger.info(f"Total unique internships: {len(unique_internships)}")

    return unique_internships

def main():
    logger.info("Starting enhanced GitHub repo scraping...")
    
    internships = scrape_all_sources()
    
    if not internships:
        # Every source failed. Overwriting the scrape file with nothing would
        # make the next merge close every open listing.
        logger.error("No internships scraped from any source - leaving %s unchanged", SCRAPED_FILE)
        return 1

    write_csv(SCRAPED_FILE, internships, SCRAPED_FIELDNAMES)
    logger.info(f"Saved {len(internships)} internships to {SCRAPED_FILE}")
    
    # Print sponsorship tier breakdown
    tier_counts = {}
    for internship in internships:
        tier = internship['sponsorship_tier']
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    
    logger.info("Sponsorship tier breakdown:")
    for tier in sorted(tier_counts.keys()):
        logger.info(f"  Tier {tier}: {tier_counts[tier]} internships")

    return 0


if __name__ == "__main__":
    sys.exit(main())