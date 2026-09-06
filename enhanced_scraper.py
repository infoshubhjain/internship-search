#!/usr/bin/env python3
"""
Enhanced scraper with additional GitHub data sources and improved data processing
"""
import requests
import re
import csv
import time
import logging
from urllib.parse import urlparse
from datetime import datetime
from sponsorship_database import get_sponsorship_info

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

def scrape_github_repo(url, repo_name):
    """Generic GitHub repo scraper"""
    try:
        logger.info(f"Scraping {repo_name}...")
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch {repo_name}: {response.status_code}")
            return []
        
        content = response.text
        internships = []
        
        # Try different parsing strategies based on repo format
        if 'vanshb03' in repo_name or 'Summer2027-Internships' in repo_name:
            internships = parse_vansh_format(content)
        elif 'ApplyGuy' in repo_name:
            internships = parse_applyguy_format(content)
        elif 'SimplifyJobs' in repo_name:
            internships = parse_simplify_format(content)
        else:
            internships = parse_generic_markdown(content)
        
        logger.info(f"Found {len(internships)} internships from {repo_name}")
        return internships
        
    except Exception as e:
        logger.error(f"Error scraping {repo_name}: {e}")
        return []

def parse_vansh_format(content):
    """Parse vanshb03 repo format"""
    internships = []
    
    table_start = content.find("| Company | Role | Location | Application/Link | Date Posted |")
    if table_start == -1:
        return internships
    
    table_content = content[table_start:]
    rows = table_content.split('\n')
    
    for row in rows:
        if row.startswith('|') and not row.startswith('| Company'):
            parts = [part.strip() for part in row.split('|')]
            if len(parts) >= 5:
                company = parts[1]
                role = parts[2]
                location = parts[3]
                link_cell = parts[4]
                
                url_match = re.search(r'href="([^"]+)"', link_cell)
                if url_match:
                    link = url_match.group(1).split('?')[0]
                    
                    no_sponsorship = '🛂' in row
                    us_citizenship = '🇺🇸' in row
                    closed = '🔒' in row
                    
                    if not closed and not us_citizenship:
                        sponsorship_info = get_sponsorship_info(company)
                        
                        internships.append({
                            'company': company,
                            'role': role,
                            'location': location,
                            'link': link,
                            'no_sponsorship': no_sponsorship,
                            'source': 'vansh_repo',
                            'sponsorship_tier': sponsorship_info['tier'],
                            'sponsorship_notes': sponsorship_info['notes']
                        })
    
    return internships

def parse_applyguy_format(content):
    """Parse ApplyGuy JSON format"""
    import json
    internships = []
    
    try:
        data = json.loads(content)
        
        for job in data.get('jobs', []):
            if job.get('category') == 'Software Engineering':
                season = job.get('season', '').lower()
                title = job.get('title', '').lower()
                
                if '2027' in season or '2027' in title or 'summer' in season:
                    link = job.get('listingUrl', job.get('url', ''))
                    
                    if 'applyguy.ai' not in link and link:
                        sponsorship_info = get_sponsorship_info(job.get('company', ''))
                        
                        internships.append({
                            'company': job.get('company', ''),
                            'role': job.get('title', ''),
                            'location': job.get('location', ''),
                            'link': link,
                            'no_sponsorship': False,
                            'source': 'applyguy_repo',
                            'sponsorship_tier': sponsorship_info['tier'],
                            'sponsorship_notes': sponsorship_info['notes']
                        })
    except json.JSONDecodeError:
        logger.error("Failed to parse ApplyGuy JSON")
    
    return internships

def parse_simplify_format(content):
    """Parse SimplifyJobs format (HTML table)"""
    internships = []
    
    swe_section = content.find("## 💻 Software Engineering Internship Roles")
    if swe_section == -1:
        return internships
    
    next_section = content.find("## 📱", swe_section + 10)
    swe_content = content[swe_section:next_section] if next_section != -1 else content[swe_section:]
    
    rows = swe_content.split('\n')
    current_company = None
    
    for row in rows:
        if row.startswith('<tr>'):
            company_match = re.search(r'<strong><a[^>]*>([^<]+)</a></strong>', row)
            
            if company_match:
                current_company = company_match.group(1).strip()
                
                role_match = re.search(r'<td>([^<]+)</td>', row)
                if role_match:
                    role = role_match.group(1).strip()
                    
                    tds = re.findall(r'<td[^>]*>(.*?)</td>', row)
                    if len(tds) >= 2:
                        location = tds[1].replace('<br>', ', ').replace('<strong>', '').replace('</strong>', '').strip()
                        
                        links = re.findall(r'href="([^"]+)"', row)
                        if links:
                            for link in links:
                                if 'simplify.jobs' not in link and 'imgur' not in link and 'github.com' not in link:
                                    link = link.split('?')[0]
                                    
                                    no_sponsorship = '🛂' in row
                                    us_citizenship = '🇺🇸' in row
                                    closed = '🔒' in row
                                    
                                    if not closed and not us_citizenship:
                                        sponsorship_info = get_sponsorship_info(current_company)
                                        
                                        internships.append({
                                            'company': current_company,
                                            'role': role,
                                            'location': location,
                                            'link': link,
                                            'no_sponsorship': no_sponsorship,
                                            'source': 'simplify_repo',
                                            'sponsorship_tier': sponsorship_info['tier'],
                                            'sponsorship_notes': sponsorship_info['notes']
                                        })
                                    break
            elif current_company:
                # Similar logic for sub-rows
                role_match = re.search(r'<td>([^<]+)</td>', row)
                if role_match:
                    role = role_match.group(1).strip()
                    
                    tds = re.findall(r'<td[^>]*>(.*?)</td>', row)
                    if len(tds) >= 2:
                        location = tds[1].replace('<br>', ', ').replace('<strong>', '').replace('</strong>', '').strip()
                        
                        links = re.findall(r'href="([^"]+)"', row)
                        if links:
                            for link in links:
                                if 'simplify.jobs' not in link and 'imgur' not in link and 'github.com' not in link:
                                    link = link.split('?')[0]
                                    
                                    no_sponsorship = '🛂' in row
                                    us_citizenship = '🇺🇸' in row
                                    closed = '🔒' in row
                                    
                                    if not closed and not us_citizenship:
                                        sponsorship_info = get_sponsorship_info(current_company)
                                        
                                        internships.append({
                                            'company': current_company,
                                            'role': role,
                                            'location': location,
                                            'link': link,
                                            'no_sponsorship': no_sponsorship,
                                            'source': 'simplify_repo',
                                            'sponsorship_tier': sponsorship_info['tier'],
                                            'sponsorship_notes': sponsorship_info['notes']
                                        })
                                    break
    
    return internships

def parse_generic_markdown(content):
    """Generic markdown table parser"""
    internships = []
    
    # Look for markdown tables
    table_pattern = r'\|[^|\n]+\|[^|\n]+\|[^|\n]+\|[^|\n]+\|'
    tables = re.findall(table_pattern, content)
    
    for table in tables:
        rows = table.split('\n')
        for row in rows:
            if '|' in row and not row.strip().startswith('|---'):
                parts = [part.strip() for part in row.split('|')]
                if len(parts) >= 4:
                    # Try to identify company, role, location, link
                    # This is a generic parser - may need adjustment per repo
                    pass
    
    return internships

def scrape_all_sources():
    """Scrape all configured GitHub sources"""
    sources = [
        ('https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/README.md', 'vanshb03'),
        ('https://raw.githubusercontent.com/ApplyGuy/2027-Internships/main/data/internships.json', 'ApplyGuy'),
        ('https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md', 'SimplifyJobs'),
        ('https://raw.githubusercontent.com/pittcsc/Summer2027-Internships/dev/README.md', 'pittcsc'),
        ('https://raw.githubusercontent.com/sndsh404/summer-2027-internships/main/README.md', 'sndsh404'),
    ]
    
    all_internships = []
    
    for url, repo_name in sources:
        try:
            internships = scrape_github_repo(url, repo_name)
            all_internships.extend(internships)
            time.sleep(1)  # Rate limiting
        except Exception as e:
            logger.error(f"Failed to scrape {repo_name}: {e}")
    
    # Deduplicate
    seen_links = set()
    unique_internships = []
    
    for internship in all_internships:
        if internship['link'] not in seen_links:
            seen_links.add(internship['link'])
            unique_internships.append(internship)
    
    logger.info(f"Total unique internships: {len(unique_internships)}")
    
    return unique_internships

def main():
    logger.info("Starting enhanced GitHub repo scraping...")
    
    internships = scrape_all_sources()
    
    # Save to CSV with enhanced fields
    with open('enhanced_scraped_internships.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['company', 'role', 'location', 'link', 'no_sponsorship', 'source', 
                     'sponsorship_tier', 'sponsorship_notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(internships)
    
    logger.info(f"Saved {len(internships)} internships to enhanced_scraped_internships.csv")
    
    # Print sponsorship tier breakdown
    tier_counts = {}
    for internship in internships:
        tier = internship['sponsorship_tier']
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    
    logger.info("Sponsorship tier breakdown:")
    for tier in sorted(tier_counts.keys()):
        logger.info(f"  Tier {tier}: {tier_counts[tier]} internships")

if __name__ == "__main__":
    main()