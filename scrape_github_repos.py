#!/usr/bin/env python3
"""
Script to scrape internship data from GitHub repositories
"""
import requests
import re
import csv
from urllib.parse import urlparse
import time

def scrape_vansh_repo():
    """Scrape data from vanshb03/Summer2027-Internships"""
    url = "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/README.md"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Failed to fetch vansh repo: {response.status_code}")
        return []
    
    content = response.text
    internships = []
    
    # Extract table rows after the table marker
    table_start = content.find("| Company | Role | Location | Application/Link | Date Posted |")
    if table_start == -1:
        print("Could not find table in vansh repo")
        return []
    
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
                
                # Extract URL from markdown link
                url_match = re.search(r'href="([^"]+)"', link_cell)
                if url_match:
                    link = url_match.group(1)
                    # Remove query parameters
                    link = link.split('?')[0]
                    
                    # Check for sponsorship indicators
                    no_sponsorship = '🛂' in row
                    us_citizenship = '🇺🇸' in row
                    closed = '🔒' in row
                    
                    if not closed and not us_citizenship:
                        internships.append({
                            'company': company,
                            'role': role,
                            'location': location,
                            'link': link,
                            'no_sponsorship': no_sponsorship,
                            'source': 'vansh_repo'
                        })
    
    print(f"Found {len(internships)} internships from vansh repo")
    return internships

def scrape_simplify_repo():
    """Scrape data from SimplifyJobs/Summer2027-Internships"""
    url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Failed to fetch simplify repo: {response.status_code}")
        return []
    
    content = response.text
    internships = []
    
    # Find the Software Engineering section
    swe_section = content.find("## 💻 Software Engineering Internship Roles")
    if swe_section == -1:
        print("Could not find SWE section in simplify repo")
        return []
    
    # Get content from SWE section to next section
    next_section = content.find("## 📱", swe_section + 10)
    if next_section == -1:
        swe_content = content[swe_section:]
    else:
        swe_content = content[swe_section:next_section]
    
    # Extract table rows
    rows = swe_content.split('\n')
    current_company = None
    
    for row in rows:
        if row.startswith('<tr>'):
            # Check if this is a main company row or a sub-row
            company_match = re.search(r'<strong><a[^>]*>([^<]+)</a></strong>', row)
            
            if company_match:
                current_company = company_match.group(1).strip()
                
                # Extract role
                role_match = re.search(r'<td>([^<]+)</td>', row)
                if role_match:
                    role = role_match.group(1).strip()
                    
                    # Extract location (second td after role)
                    tds = re.findall(r'<td[^>]*>(.*?)</td>', row)
                    if len(tds) >= 2:
                        location = tds[1].replace('<br>', ', ').replace('<strong>', '').replace('</strong>', '').strip()
                        
                        # Extract application links
                        links = re.findall(r'href="([^"]+)"', row)
                        if links:
                            # Get the first actual application link (not simplify links)
                            for link in links:
                                if 'simplify.jobs' not in link and 'imgur' not in link and 'github.com' not in link:
                                    link = link.split('?')[0]
                                    
                                    # Check for indicators
                                    no_sponsorship = '🛂' in row
                                    us_citizenship = '🇺🇸' in row
                                    closed = '🔒' in row
                                    
                                    if not closed and not us_citizenship:
                                        internships.append({
                                            'company': current_company,
                                            'role': role,
                                            'location': location,
                                            'link': link,
                                            'no_sponsorship': no_sponsorship,
                                            'source': 'simplify_repo'
                                        })
                                    break
            elif current_company:
                # This is a sub-row (same company)
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
                                        internships.append({
                                            'company': current_company,
                                            'role': role,
                                            'location': location,
                                            'link': link,
                                            'no_sponsorship': no_sponsorship,
                                            'source': 'simplify_repo'
                                        })
                                    break
    
    print(f"Found {len(internships)} internships from simplify repo")
    return internships

def scrape_applyguy_repo():
    """Scrape data from ApplyGuy/2027-Internships JSON API"""
    url = "https://raw.githubusercontent.com/ApplyGuy/2027-Internships/main/data/internships.json"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Failed to fetch applyguy repo: {response.status_code}")
        return []
    
    data = response.json()
    internships = []
    
    for job in data.get('jobs', []):
        # Only include software engineering roles and summer 2027
        if job.get('category') == 'Software Engineering':
            # Check if it's for 2027
            season = job.get('season', '').lower()
            title = job.get('title', '').lower()
            
            if '2027' in season or '2027' in title or 'summer' in season:
                # Use listingUrl if available, otherwise use url
                link = job.get('listingUrl', job.get('url', ''))
                
                # Filter out applyguy.ai links
                if 'applyguy.ai' not in link and link:
                    internships.append({
                        'company': job.get('company', ''),
                        'role': job.get('title', ''),
                        'location': job.get('location', ''),
                        'link': link,
                        'no_sponsorship': False,  # ApplyGuy doesn't provide this info
                        'source': 'applyguy_repo'
                    })
    
    print(f"Found {len(internships)} internships from applyguy repo")
    return internships

def verify_url(url):
    """Check if URL is accessible and valid"""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

def main():
    print("Starting GitHub repo scraping...")
    
    # Scrape all repos
    vansh_internships = scrape_vansh_repo()
    simplify_internships = scrape_simplify_repo()
    applyguy_internships = scrape_applyguy_repo()
    
    # Combine and deduplicate
    all_internships = vansh_internships + simplify_internships + applyguy_internships
    seen_links = set()
    unique_internships = []
    
    for internship in all_internships:
        if internship['link'] not in seen_links:
            seen_links.add(internship['link'])
            unique_internships.append(internship)
    
    print(f"Total unique internships: {len(unique_internships)}")
    
    # Save to CSV
    with open('scraped_internships.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['company', 'role', 'location', 'link', 'no_sponsorship', 'source'])
        writer.writeheader()
        writer.writerows(unique_internships)
    
    print("Saved to scraped_internships.csv")
    
    # Verify first 20 URLs
    print("\nVerifying first 20 URLs...")
    verified_count = 0
    for i, internship in enumerate(unique_internships[:20]):
        if verify_url(internship['link']):
            verified_count += 1
            print(f"✓ {internship['company']}: {internship['link']}")
        else:
            print(f"✗ {internship['company']}: {internship['link']}")
        time.sleep(0.5)  # Rate limiting
    
    print(f"\nVerified {verified_count}/20 URLs")

if __name__ == "__main__":
    main()