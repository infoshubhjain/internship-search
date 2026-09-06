#!/usr/bin/env python3
"""
Email and notification system for high-priority internship opportunities
"""
import smtplib
import csv
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict

from tracker_io import TRACKER_FILE

logger = logging.getLogger(__name__)


def config_from_env():
    """Build SMTP settings from the environment.

    Returns {} when unconfigured, which makes send_email skip silently rather
    than crash - alerts are optional, the tracker itself is not.
    """
    from security_manager import SecurityManager

    secrets = SecurityManager()
    email = secrets.get_secret('TRACKER_EMAIL')
    password = secrets.get_secret('TRACKER_EMAIL_PASSWORD')
    if not (email and password):
        return {}

    return {
        'email': email,
        'password': password,
        'smtp_server': secrets.get_secret('TRACKER_SMTP_SERVER') or 'smtp.gmail.com',
        'smtp_port': int(secrets.get_secret('TRACKER_SMTP_PORT') or 587),
    }

class NotificationSystem:
    def __init__(self, email_config=None):
        """
        Initialize notification system
        
        Args:
            email_config: Dict with 'email', 'password', 'smtp_server', 'smtp_port'
                         For Gmail: smtp_server='smtp.gmail.com', smtp_port=587
        """
        self.email_config = email_config or config_from_env()

    
    def send_email(self, to_email: str, subject: str, body: str, html: bool = False):
        """Send email notification"""
        if not self.email_config:
            logger.warning("Email configuration not set, skipping email send")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_config['email']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Context manager so the connection is closed even if login or
            # send raises; the previous explicit quit() was skipped on error.
            with smtplib.SMTP(self.email_config['smtp_server'],
                              self.email_config['smtp_port'], timeout=30) as server:
                server.starttls()
                server.login(self.email_config['email'], self.email_config['password'])
                server.send_message(msg)

            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def check_new_priority_opportunities(self, tracker_file=None, last_check_file=None):
        """High-priority listings added by the most recent merge.

        Delegates to the merge's own record of what it added; the old
        timestamp-versus-Date-Posted comparison fired on every row of a fresh
        tracker because the merge stamps Date Posted itself.
        """
        from merge_internship_data import read_new_listings

        return read_new_listings()

    def send_priority_alert(self, opportunities: List[Dict], to_email: str):
        """Send alert for new high-priority opportunities"""
        if not opportunities:
            logger.info("No new priority opportunities to report")
            return
        
        subject = f"🚀 {len(opportunities)} New High-Priority Internship Opportunities"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .opportunity {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .priority-1 {{ border-left: 5px solid #ff6b6b; }}
                .priority-2 {{ border-left: 5px solid #ffd93d; }}
                .company {{ font-weight: bold; font-size: 18px; }}
                .role {{ color: #666; }}
                .link {{ color: #4CAF50; text-decoration: none; }}
                .sponsorship {{ font-size: 12px; color: #888; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 New High-Priority Internship Opportunities</h1>
                <p>{len(opportunities)} new opportunities found since last check</p>
            </div>
            
            <div class="content">
        """
        
        for opp in opportunities:
            priority_class = f"priority-{opp['Priority']}"
            html_body += f"""
                <div class="opportunity {priority_class}">
                    <div class="company">{opp['Company']}</div>
                    <div class="role">{opp['Role']}</div>
                    <div class="location">📍 {opp['Location']}</div>
                    <div class="sponsorship">💼 {opp['Work Authorization/Sponsorship Notes']}</div>
                    <a href="{opp['Link']}" class="link">Apply Now →</a>
                </div>
            """
        
        html_body += """
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background-color: #f5f5f5; border-radius: 5px;">
                <h3>📋 Next Steps:</h3>
                <ol>
                    <li>Review the opportunities above</li>
                    <li>Prioritize Priority 1 roles (underclassman programs)</li>
                    <li>Apply to 2-3 roles today</li>
                    <li>Update your tracker with application status</li>
                </ol>
                <p><strong>Target:</strong> Apply to 5-10 high-priority roles per week</p>
            </div>
        </body>
        </html>
        """
        
        self.send_email(to_email, subject, html_body, html=True)
    
    def check_deadline_alerts(self, tracker_file: str, days_ahead: int = 7):
        """Check for opportunities with deadlines approaching"""
        upcoming_deadlines = []
        today = datetime.now()
        alert_date = today + timedelta(days=days_ahead)
        
        try:
            with open(tracker_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    deadline = row.get('Application Deadline', '')
                    if deadline and row['Status'] == 'Not Applied':
                        try:
                            deadline_date = datetime.fromisoformat(deadline)
                            if today <= deadline_date <= alert_date:
                                upcoming_deadlines.append({
                                    'company': row['Company'],
                                    'role': row['Role'],
                                    'deadline': deadline,
                                    'days_remaining': (deadline_date - today).days,
                                    'link': row['Link']
                                })
                        except ValueError:
                            continue
            
            return upcoming_deadlines
            
        except Exception as e:
            logger.error(f"Error checking deadlines: {e}")
            return []
    
    def send_deadline_alert(self, deadlines: List[Dict], to_email: str):
        """Send alert for upcoming deadlines"""
        if not deadlines:
            return
        
        subject = f"⏰ {len(deadlines)} Application Deadlines This Week"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .urgent {{ background-color: #ffebee; border-left: 5px solid #f44336; }}
                .warning {{ background-color: #fff3e0; border-left: 5px solid #ff9800; }}
                .deadline {{ font-weight: bold; color: #f44336; }}
            </style>
        </head>
        <body>
            <h1>⏰ Upcoming Application Deadlines</h1>
            <p>You have {len(deadlines)} application deadlines approaching in the next 7 days.</p>
        """
        
        for deadline in deadlines:
            urgency_class = 'urgent' if deadline['days_remaining'] <= 3 else 'warning'
            html_body += f"""
                <div class="{urgency_class}" style="padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <div><strong>{deadline['company']}</strong> - {deadline['role']}</div>
                    <div class="deadline">Deadline: {deadline['deadline']} ({deadline['days_remaining']} days remaining)</div>
                    <a href="{deadline['link']}">Apply Now →</a>
                </div>
            """
        
        html_body += """
            <div style="margin-top: 20px; padding: 15px; background-color: #e3f2fd; border-radius: 5px;">
                <strong>🎯 Action Required:</strong> Prioritize these applications immediately to avoid missing deadlines.
            </div>
        </body>
        </html>
        """
        
        self.send_email(to_email, subject, html_body, html=True)
    
    def send_weekly_summary(self, tracker_file: str, to_email: str):
        """Send weekly summary of application progress"""
        try:
            with open(tracker_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Calculate statistics
            total = len(rows)
            applied = len([r for r in rows if r['Status'] == 'Applied'])
            interviewing = len([r for r in rows if r['Status'] == 'Interviewing'])
            offers = len([r for r in rows if r['Offer Status'] == 'Offer'])
            rejected = len([r for r in rows if r['Status'] == 'Rejected'])
            
            # Priority breakdown
            priority_stats = {}
            for row in rows:
                priority = row['Priority']
                if priority not in priority_stats:
                    priority_stats[priority] = {'total': 0, 'applied': 0}
                priority_stats[priority]['total'] += 1
                if row['Status'] == 'Applied':
                    priority_stats[priority]['applied'] += 1
            
            subject = "📊 Weekly Internship Application Summary"
            
            html_body = f"""
            <html>
            <body>
                <h1>📊 Weekly Application Summary</h1>
                
                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h2>Overall Progress</h2>
                    <p><strong>Total Opportunities:</strong> {total}</p>
                    <p><strong>Applied:</strong> {applied} ({applied/total*100:.1f}%)</p>
                    <p><strong>Interviewing:</strong> {interviewing}</p>
                    <p><strong>Offers:</strong> {offers}</p>
                    <p><strong>Rejected:</strong> {rejected}</p>
                </div>
                
                <div style="background-color: #e3f2fd; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h2>Priority Breakdown</h2>
            """
            
            for priority in sorted(priority_stats.keys()):
                stats = priority_stats[priority]
                percentage = (stats['applied'] / stats['total'] * 100) if stats['total'] > 0 else 0
                html_body += f"""
                    <p><strong>Priority {priority}:</strong> {stats['applied']}/{stats['total']} applied ({percentage:.1f}%)</p>
                """
            
            html_body += """
                </div>
                
                <div style="background-color: #fff3e0; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h2>🎯 Next Week's Goals</h2>
                    <ul>
                        <li>Apply to 5-10 new opportunities</li>
                        <li>Focus on Priority 1-2 roles</li>
                        <li>Follow up on pending applications</li>
                        <li>Prepare for upcoming interviews</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            
            self.send_email(to_email, subject, html_body, html=True)
            
        except Exception as e:
            logger.error(f"Error sending weekly summary: {e}")

def main():
    """Send any pending priority and deadline alerts."""
    notifier = NotificationSystem()

    if not notifier.email_config:
        print("Email is not configured. Set these and re-run:")
        print("  export TRACKER_EMAIL=you@gmail.com")
        print("  export TRACKER_EMAIL_PASSWORD=<gmail app password>")
        print("(a .env file in this directory works too)")
        return

    to_email = notifier.email_config['email']

    new_opps = notifier.check_new_priority_opportunities(TRACKER_FILE)
    if new_opps:
        notifier.send_priority_alert(new_opps, to_email)

    deadlines = notifier.check_deadline_alerts(TRACKER_FILE)
    if deadlines:
        notifier.send_deadline_alert(deadlines, to_email)

if __name__ == "__main__":
    main()