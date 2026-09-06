#!/usr/bin/env python3
"""
Google Calendar integration for interview scheduling and deadline reminders
"""
import logging
from datetime import datetime, timedelta
from typing import List
import csv

logger = logging.getLogger(__name__)

class CalendarIntegration:
    def __init__(self, credentials_path=None):
        """
        Initialize Google Calendar integration
        
        Args:
            credentials_path: Path to Google OAuth credentials JSON file
        """
        self.credentials_path = credentials_path
        self.service = None
        
        if credentials_path:
            try:
                self._authenticate()
            except Exception as e:
                logger.error(f"Failed to authenticate with Google Calendar: {e}")
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            import os
            
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            
            creds = None
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            
            from googleapiclient.discovery import build
            self.service = build('calendar', 'v3', credentials=creds)
            
            logger.info("Successfully authenticated with Google Calendar")
            
        except ImportError:
            logger.warning("Google Calendar API libraries not installed")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
    
    def add_event(self, title: str, start_time: datetime, end_time: datetime, 
                  description: str = "", location: str = "") -> bool:
        """Add event to Google Calendar"""
        if not self.service:
            logger.warning("Calendar service not available")
            return False
        
        try:
            event = {
                'summary': title,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/Chicago',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Chicago',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 60},
                    ],
                },
            }
            
            event = self.service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f"Created event: {event.get('htmlLink')}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return False
    
    def add_application_deadline(self, company: str, role: str, deadline: datetime, 
                                 link: str = "") -> bool:
        """Add application deadline to calendar"""
        title = f"📅 Apply: {company} - {role}"
        description = f"Application deadline for {company} - {role}\n\nLink: {link}"
        
        # Set reminder for 1 day before deadline
        reminder_time = deadline - timedelta(days=1)
        
        return self.add_event(
            title=title,
            start_time=reminder_time,
            end_time=reminder_time + timedelta(hours=1),
            description=description
        )
    
    def add_interview(self, company: str, role: str, interview_time: datetime,
                      interview_type: str = "Technical", notes: str = "") -> bool:
        """Add interview to calendar"""
        title = f"🎯 Interview: {company} - {role} ({interview_type})"
        description = f"Interview with {company}\nRole: {role}\nType: {interview_type}\n\nNotes: {notes}"
        
        # Assume 1 hour interview
        end_time = interview_time + timedelta(hours=1)
        
        return self.add_event(
            title=title,
            start_time=interview_time,
            end_time=end_time,
            description=description
        )
    
    def add_follow_up_reminder(self, company: str, role: str, follow_up_date: datetime,
                              notes: str = "") -> bool:
        """Add follow-up reminder to calendar"""
        title = f"📧 Follow-up: {company} - {role}"
        description = f"Send follow-up email to {company}\nRole: {role}\n\nNotes: {notes}"
        
        return self.add_event(
            title=title,
            start_time=follow_up_date,
            end_time=follow_up_date + timedelta(hours=1),
            description=description
        )
    
    def add_weekly_goals(self, start_date: datetime, goals: List[str]) -> bool:
        """Add weekly goals to calendar"""
        title = "🎯 Weekly Internship Goals"
        description = "This week's goals:\n\n" + "\n".join(f"• {goal}" for goal in goals)
        
        return self.add_event(
            title=title,
            start_time=start_date,
            end_time=start_date + timedelta(hours=1),
            description=description
        )
    
    def sync_tracker_to_calendar(self, tracker_file: str):
        """Sync all tracker items to calendar"""
        try:
            with open(tracker_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Add deadlines
                    deadline_str = row.get('Application Deadline', '')
                    if deadline_str and row['Status'] == 'Not Applied':
                        try:
                            deadline = datetime.fromisoformat(deadline_str)
                            self.add_application_deadline(
                                row['Company'],
                                row['Role'],
                                deadline,
                                row['Link']
                            )
                        except ValueError:
                            continue
                    
                    # Add interviews
                    interview_str = row.get('Interview Date', '')
                    if interview_str:
                        try:
                            interview = datetime.fromisoformat(interview_str)
                            self.add_interview(
                                row['Company'],
                                row['Role'],
                                interview
                            )
                        except ValueError:
                            continue
                    
                    # Add follow-ups
                    followup_str = row.get('Follow-up Date', '')
                    if followup_str:
                        try:
                            followup = datetime.fromisoformat(followup_str)
                            self.add_follow_up_reminder(
                                row['Company'],
                                row['Role'],
                                followup,
                                row.get('Notes', '')
                            )
                        except ValueError:
                            continue
            
            logger.info("Successfully synced tracker to calendar")
            
        except Exception as e:
            logger.error(f"Error syncing tracker to calendar: {e}")

def main():
    """Example usage"""
    # Initialize with your credentials file
    # calendar = CalendarIntegration('credentials.json')
    
    # Add individual events
    # calendar.add_application_deadline(
    #     company="Google",
    #     role="STEP Intern",
    #     deadline=datetime(2026, 10, 15),
    #     link="https://example.com"
    # )
    
    # calendar.add_interview(
    #     company="Microsoft",
    #     role="Explore Intern",
    #     interview_time=datetime(2026, 10, 20, 14, 0),
    #     interview_type="Technical",
    #     notes="Prepare for data structures and algorithms"
    # )
    
    # Sync entire tracker
    # calendar.sync_tracker_to_calendar('Summer2027_SWE_Tracker.csv')
    
    print("Calendar integration example (requires Google credentials)")

if __name__ == "__main__":
    main()