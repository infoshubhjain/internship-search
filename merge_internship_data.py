#!/usr/bin/env python3
"""
Merge scraped internship data with master tracker and create comprehensive tracker
"""
import csv
import requests
from datetime import datetime, timedelta

def load_master_tracker():
    """Load the master tracker CSV"""
    try:
        with open('SWE_Internship_Master_Tracker.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        print("Master tracker not found")
        return []

def load_scraped_data():
    """Load the scraped internship data"""
    try:
        with open('scraped_internships.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        print("Scraped data not found")
        return []

def assign_priority(company, role):
    """Assign priority based on company and role"""
    company_lower = company.lower()
    role_lower = role.lower()
    
    # Priority 1: Underclassman programs
    underclassman_keywords = ['step', 'explore', 'university swe', 'technology internship', 'engaging', 'university']
    underclassman_companies = ['google', 'microsoft', 'meta', 'amazon', 'capital one', 'uber', 'pinterest', 'lyft']
    
    if any(kw in role_lower for kw in underclassman_keywords) or any(comp in company_lower for comp in underclassman_companies):
        return '1'
    
    # Priority 2: Banks/fintech
    bank_keywords = ['jpmorgan', 'goldman', 'morgan stanley', 'bank of america', 'citi', 'wells fargo', 
                   'visa', 'mastercard', 'american express', 'blackrock', 'fidelity', 'paypal', 
                   'intuit', 'charles schwab', 'bloomberg', 'barclays', 'credit suisse', 'deutsche bank']
    
    if any(bank in company_lower for bank in bank_keywords):
        return '2'
    
    # Priority 3: F500 non-tech
    f500_companies = ['walmart', 'target', 'general motors', 'ford', 'john deere', 'caterpillar', 
                     'state farm', 'unitedhealth', 'optum', 'cvs', 'verizon', 't-mobile', 'comcast', 
                     'honeywell', 'siemens', 'ibm', 'intel', 'micron', 'dell', 'hp', 'cisco']
    
    if any(comp in company_lower for comp in f500_companies):
        return '3'
    
    # Priority 4: Big Tech/unicorns
    bigtech_companies = ['apple', 'netflix', 'airbnb', 'stripe', 'linkedin', 'salesforce', 'adobe', 
                        'workday', 'servicenow', 'sap', 'roblox', 'snap', 'datadog', 'atlassian', 
                        'dropbox', 'reddit', 'twitch', 'block', 'plaid', 'chime', 'brex', 'duolingo', 
                        'figma', 'notion', 'ramp', 'replit', 'notion', 'scale ai']
    
    if any(comp in company_lower for comp in bigtech_companies):
        return '4'
    
    # Priority 5: Startups/other
    return '5'

def determine_sponsorship_notes(company, no_sponsorship_flag):
    """Determine sponsorship notes based on company and flags"""
    if no_sponsorship_flag:
        return "No sponsorship"
    
    company_lower = company.lower()
    
    # Companies known to sponsor
    sponsors = ['google', 'microsoft', 'amazon', 'meta', 'apple', 'netflix', 'airbnb', 'stripe', 
               'linkedin', 'salesforce', 'adobe', 'jpmorgan', 'goldman', 'morgan stanley', 
               'bank of america', 'citi', 'visa', 'mastercard', 'american express', 'paypal',
               'intuit', 'fidelity', 'blackrock', 'bloomberg', 'cisco', 'intel', 'ibm']
    
    if any(sponsor in company_lower for sponsor in sponsors):
        return "Likely sponsors CPT/OPT"
    
    return "Unknown - check listing"

def create_comprehensive_tracker():
    """Create comprehensive tracker with all data sources"""
    master_data = load_master_tracker()
    scraped_data = load_scraped_data()
    
    # Create a set of existing links from master tracker
    existing_links = set()
    for row in master_data:
        if row.get('Link'):
            existing_links.add(row['Link'])
    
    # Process scraped data
    comprehensive_data = []
    
    # First, add master tracker entries with new columns
    for row in master_data:
        comprehensive_data.append({
            'Company': row.get('Company', ''),
            'Role': row.get('Program', row.get('Role', '')),
            'Location': 'Multiple',  # Master tracker doesn't have specific locations
            'Link': row.get('Link', ''),
            'Date Posted': '',
            'Application Deadline': '',
            'Work Authorization/Sponsorship Notes': row.get('Notes', ''),
            'Eligibility': row.get('Likelihood', ''),
            'Source': 'master_tracker',
            'Priority': assign_priority(row.get('Company', ''), row.get('Program', '')),
            'Status': 'Not Applied',
            'Notes': row.get('Notes', ''),
            'Date Applied': '',
            'Interview Date': '',
            'Offer Status': '',
            'Follow-up Date': ''
        })
    
    # Then add scraped data (new entries only)
    new_entries = 0
    for row in scraped_data:
        link = row.get('link', '')
        if link and link not in existing_links:
            existing_links.add(link)
            new_entries += 1
            
            comprehensive_data.append({
                'Company': row.get('company', ''),
                'Role': row.get('role', ''),
                'Location': row.get('location', ''),
                'Link': link,
                'Date Posted': datetime.now().strftime('%Y-%m-%d'),
                'Application Deadline': '',
                'Work Authorization/Sponsorship Notes': determine_sponsorship_notes(
                    row.get('company', ''), row.get('no_sponsorship', 'False') == 'True'
                ),
                'Eligibility': 'Unknown',
                'Source': row.get('source', ''),
                'Priority': assign_priority(row.get('company', ''), row.get('role', '')),
                'Status': 'Not Applied',
                'Notes': '',
                'Date Applied': '',
                'Interview Date': '',
                'Offer Status': '',
                'Follow-up Date': ''
            })
    
    # Sort by priority
    priority_order = {'1': 0, '2': 1, '3': 2, '4': 3, '5': 4}
    comprehensive_data.sort(key=lambda x: priority_order.get(x['Priority'], 5))
    
    # Save comprehensive tracker
    with open('Summer2027_SWE_Tracker.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Company', 'Role', 'Location', 'Link', 'Date Posted', 'Application Deadline', 
                     'Work Authorization/Sponsorship Notes', 'Eligibility', 'Source', 'Priority', 
                     'Status', 'Notes', 'Date Applied', 'Interview Date', 'Offer Status', 'Follow-up Date']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comprehensive_data)
    
    print(f"Created comprehensive tracker with {len(comprehensive_data)} total entries")
    print(f"Added {new_entries} new entries from scraped data")
    
    # Print priority breakdown
    priority_counts = {}
    for row in comprehensive_data:
        priority = row['Priority']
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    print("\nPriority breakdown:")
    for priority in sorted(priority_counts.keys()):
        print(f"  Priority {priority}: {priority_counts[priority]} entries")

if __name__ == "__main__":
    create_comprehensive_tracker()