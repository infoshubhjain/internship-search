#!/usr/bin/env python3
"""
Deadline tracking and alerting system
"""
import csv
import logging
from datetime import datetime, timedelta
from notification_system import NotificationSystem
from tracker_io import TRACKER_FILE, write_csv

logger = logging.getLogger(__name__)

class DeadlineTracker:
    def __init__(self, tracker_file: str):
        self.tracker_file = tracker_file
        self.notifier = NotificationSystem()
    
    def extract_deadlines_from_link(self, link: str) -> str:
        """Try to extract deadline from job posting URL or page"""
        # This is a placeholder - in a real implementation, you'd scrape the page
        # For now, return empty string
        return ""
    
    def update_deadlines(self):
        """Update deadlines in tracker by scraping job postings"""
        try:
            updated_rows = []
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    # If deadline is empty and status is 'Not Applied', try to find it
                    if not row.get('Application Deadline') and row['Status'] == 'Not Applied':
                        deadline = self.extract_deadlines_from_link(row['Link'])
                        row['Application Deadline'] = deadline
                    
                    updated_rows.append(row)
            
            write_csv(self.tracker_file, updated_rows, fieldnames)
            
            logger.info("Updated deadlines in tracker")
            
        except Exception as e:
            logger.error(f"Error updating deadlines: {e}")
    
    def get_upcoming_deadlines(self, days_ahead: int = 7) -> list:
        """Get opportunities with deadlines in the next N days"""
        upcoming = []
        today = datetime.now()
        alert_date = today + timedelta(days=days_ahead)
        
        try:
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    deadline_str = row.get('Application Deadline', '')
                    if deadline_str and row['Status'] == 'Not Applied':
                        try:
                            deadline = datetime.fromisoformat(deadline_str.strip()[:19])
                            if today <= deadline <= alert_date:
                                upcoming.append({
                                    'company': row['Company'],
                                    'role': row['Role'],
                                    'deadline': deadline,
                                    'days_remaining': (deadline - today).days,
                                    'link': row['Link'],
                                    'priority': row['Priority']
                                })
                        except ValueError:
                            continue
            
            # Sort by days remaining
            upcoming.sort(key=lambda x: x['days_remaining'])
            
            return upcoming
            
        except Exception as e:
            logger.error(f"Error getting upcoming deadlines: {e}")
            return []
    
    def get_expired_opportunities(self) -> list:
        """Get opportunities with passed deadlines"""
        expired = []
        today = datetime.now()
        
        try:
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    deadline_str = row.get('Application Deadline', '')
                    if deadline_str and row['Status'] == 'Not Applied':
                        try:
                            deadline = datetime.fromisoformat(deadline_str.strip()[:19])
                            if deadline < today:
                                expired.append({
                                    'company': row['Company'],
                                    'role': row['Role'],
                                    'deadline': deadline,
                                    'days_past': (today - deadline).days,
                                    'link': row['Link']
                                })
                        except ValueError:
                            continue
            
            return expired
            
        except Exception as e:
            logger.error(f"Error getting expired opportunities: {e}")
            return []
    
    def mark_expired_as_closed(self):
        """Mark expired opportunities as closed"""
        expired = self.get_expired_opportunities()
        
        if not expired:
            logger.info("No expired opportunities to mark")
            return
        
        try:
            updated_rows = []
            expired_links = {item['link'] for item in expired}
            
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    if row['Link'] in expired_links and row['Status'] == 'Not Applied':
                        row['Status'] = 'Closed'
                        # Notes is a USER_FIELD: the merge protects it, so this
                        # must append rather than overwrite whatever the user
                        # wrote on a listing they had not applied to yet.
                        stamp = f"Deadline passed on {row['Application Deadline']}"
                        note = (row.get('Notes') or '').strip()
                        if stamp not in note:
                            row['Notes'] = f"{note} | {stamp}".strip(' |')
                    
                    updated_rows.append(row)
            
            write_csv(self.tracker_file, updated_rows, fieldnames)
            
            logger.info(f"Marked {len(expired)} expired opportunities as closed")
            
        except Exception as e:
            logger.error(f"Error marking expired opportunities: {e}")
    
    def add_manual_deadline(self, company: str, role: str, deadline: str):
        """Add or update deadline for a specific opportunity"""
        try:
            updated_rows = []
            found = False
            
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    if row['Company'] == company and row['Role'] == role:
                        row['Application Deadline'] = deadline
                        found = True
                    
                    updated_rows.append(row)
            
            if found:
                write_csv(self.tracker_file, updated_rows, fieldnames)
                
                logger.info(f"Updated deadline for {company} - {role}")
            else:
                logger.warning(f"Could not find {company} - {role} in tracker")
            
        except Exception as e:
            logger.error(f"Error adding manual deadline: {e}")
    
    def send_deadline_alerts(self, email_config: dict = None):
        """Send email alerts for upcoming deadlines"""
        if email_config:
            self.notifier = NotificationSystem(email_config)
        
        upcoming = self.get_upcoming_deadlines(days_ahead=7)
        
        if upcoming:
            logger.info(f"Sending deadline alerts for {len(upcoming)} opportunities")
            # This would call the notification system
            # For now, just log them
            for item in upcoming:
                logger.info(f"UPCOMING: {item['company']} - {item['role']} - {item['days_remaining']} days")
        else:
            logger.info("No upcoming deadlines in the next 7 days")

def main():
    """Example usage"""
    tracker = DeadlineTracker(TRACKER_FILE)
    
    # Update deadlines (would scrape job postings in real implementation)
    # tracker.update_deadlines()
    
    # Get upcoming deadlines
    upcoming = tracker.get_upcoming_deadlines(days_ahead=7)
    print(f"Upcoming deadlines (next 7 days): {len(upcoming)}")
    
    # Get expired opportunities
    expired = tracker.get_expired_opportunities()
    print(f"Expired opportunities: {len(expired)}")
    
    # Mark expired as closed
    # tracker.mark_expired_as_closed()
    
    # Send alerts (would require email config)
    # tracker.send_deadline_alerts(email_config)

if __name__ == "__main__":
    main()