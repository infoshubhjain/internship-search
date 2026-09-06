#!/usr/bin/env python3
"""
Simple scraper for job boards (Indeed, BuiltIn, etc.)
Note: LinkedIn requires authentication and is not easily scrapable
"""
import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from datetime import datetime

def scrape_indeed():
    """Scrape Indeed for software engineer internships"""
    # Indeed search URL for Summer 2027 SWE internships
    url = "https://www.indeed.com/jobs?q=software+engineer+intern+summer+2027&l=United+States"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Indeed scraping failed: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        internships = []
        
        # Find job cards
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        
        for card in job_cards:
            try:
                title_elem = card.find('h2', class_='jobTitle')
                company_elem = card.find('span', {'data-testid': 'company-name'})
                location_elem = card.find('div', {'data-testid': 'text-location'})
                link_elem = card.find('a', href=True)
                
                if title_elem and company_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True)
                    location = location_elem.get_text(strip=True) if location_elem else 'Unknown'
                    link = 'https://www.indeed.com' + link_elem['href']
                    
                    # Filter for internships and 2027
                    if 'intern' in title.lower() and '2027' in title.lower():
                        internships.append({
                            'company': company,
                            'role': title,
                            'location': location,
                            'link': link,
                            'no_sponsorship': False,
                            'source': 'indeed'
                        })
            except Exception as e:
                continue
        
        print(f"Found {len(internships)} internships from Indeed")
        return internships
        
    except Exception as e:
        print(f"Indeed scraping error: {e}")
        return []

def scrape_built_in():
    """Scrape BuiltIn for tech internships"""
    url = "https://builtin.com/jobs/internships/software-engineer"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"BuiltIn scraping failed: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        internships = []
        
        # BuiltIn uses different structure - this is a basic implementation
        job_cards = soup.find_all('div', class_='search-item')
        
        for card in job_cards:
            try:
                title_elem = card.find('h3')
                company_elem = card.find('div', class_='company-info')
                link_elem = card.find('a', href=True)
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True) if company_elem else 'Unknown'
                    link = link_elem['href']
                    
                    if 'intern' in title.lower():
                        internships.append({
                            'company': company,
                            'role': title,
                            'location': 'Various',
                            'link': link,
                            'no_sponsorship': False,
                            'source': 'builtin'
                        })
            except Exception as e:
                continue
        
        print(f"Found {len(internships)} internships from BuiltIn")
        return internships
        
    except Exception as e:
        print(f"BuiltIn scraping error: {e}")
        return []

def main():
    print("Starting job board scraping...")
    
    # Scrape job boards
    indeed_internships = scrape_indeed()
    builtin_internships = scrape_built_in()
    
    # Combine results
    all_internships = indeed_internships + builtin_internships
    
    # Deduplicate by link
    seen_links = set()
    unique_internships = []
    
    for internship in all_internships:
        if internship['link'] not in seen_links:
            seen_links.add(internship['link'])
            unique_internships.append(internship)
    
    print(f"Total unique internships from job boards: {len(unique_internships)}")
    
    # Save to CSV
    if unique_internships:
        with open('job_board_internships.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['company', 'role', 'location', 'link', 'no_sponsorship', 'source'])
            writer.writeheader()
            writer.writerows(unique_internships)
        
        print("Saved to job_board_internships.csv")
    else:
        print("No internships found from job boards")

if __name__ == "__main__":
    main()