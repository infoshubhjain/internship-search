#!/usr/bin/env python3
"""
Database manager for SQLite-based internship tracking system
"""
import sqlite3
import logging
import csv
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = 'internship_tracker.db'):
        self.db_path = db_path
        self._initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Companies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    website TEXT,
                    sponsorship_cpt BOOLEAN,
                    sponsorship_opt BOOLEAN,
                    sponsorship_h1b BOOLEAN,
                    sponsorship_notes TEXT,
                    sponsorship_tier INTEGER DEFAULT 5,
                    industry TEXT,
                    headquarters TEXT,
                    founded_year INTEGER,
                    employee_count INTEGER,
                    glassdoor_rating REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Opportunities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    role TEXT NOT NULL,
                    location TEXT,
                    link TEXT NOT NULL UNIQUE,
                    date_posted DATE,
                    application_deadline DATE,
                    source TEXT,
                    priority INTEGER DEFAULT 5,
                    eligibility TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            """)
            
            # Applications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'Not Applied',
                    date_applied DATE,
                    interview_date DATE,
                    interview_type TEXT,
                    offer_status TEXT,
                    offer_details TEXT,
                    rejection_reason TEXT,
                    follow_up_date DATE,
                    follow_up_status TEXT,
                    resume_version TEXT,
                    cover_letter_version TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
                )
            """)
            
            # Company research table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_research (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    research_type TEXT,
                    content TEXT,
                    source TEXT,
                    date_researched DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
            """)
            
            # Templates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    template_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    variables TEXT,
                    is_custom BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, template_name)
                )
            """)
            
            # Skills table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT,
                    proficiency_level INTEGER DEFAULT 1,
                    last_practiced DATE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Opportunity skills junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS opportunity_skills (
                    opportunity_id INTEGER,
                    skill_id INTEGER,
                    importance_level INTEGER DEFAULT 1,
                    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id),
                    FOREIGN KEY (skill_id) REFERENCES skills(id),
                    PRIMARY KEY (opportunity_id, skill_id)
                )
            """)
            
            # Analytics events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_priority ON opportunities(priority)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_status ON applications(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_sponsorship ON companies(sponsorship_tier)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_date ON applications(date_applied)")
            
            logger.info("Database initialized successfully")
    
    def migrate_from_csv(self, csv_file: str):
        """Migrate data from CSV to database"""
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    for row in reader:
                        # Check if company exists
                        cursor.execute(
                            "SELECT id FROM companies WHERE name = ?",
                            (row['Company'],)
                        )
                        company_result = cursor.fetchone()
                        
                        if company_result:
                            company_id = company_result['id']
                        else:
                            # Create company
                            sponsorship_info = self._get_sponsorship_from_notes(row['Work Authorization/Sponsorship Notes'])
                            
                            cursor.execute("""
                                INSERT INTO companies (name, sponsorship_notes, sponsorship_tier)
                                VALUES (?, ?, ?)
                            """, (row['Company'], row['Work Authorization/Sponsorship Notes'], sponsorship_info['tier']))
                            
                            company_id = cursor.lastrowid
                        
                        # Check if opportunity exists
                        cursor.execute(
                            "SELECT id FROM opportunities WHERE link = ?",
                            (row['Link'],)
                        )
                        opp_result = cursor.fetchone()
                        
                        if opp_result:
                            opportunity_id = opp_result['id']
                        else:
                            # Create opportunity
                            cursor.execute("""
                                INSERT INTO opportunities (
                                    company_id, role, location, link, date_posted,
                                    application_deadline, source, priority, eligibility, notes
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                company_id,
                                row['Role'],
                                row['Location'],
                                row['Link'],
                                row.get('Date Posted', '') or None,
                                row.get('Application Deadline', '') or None,
                                row['Source'],
                                int(row['Priority']) if row['Priority'].isdigit() else 5,
                                row['Eligibility'],
                                row['Notes']
                            ))
                            
                            opportunity_id = cursor.lastrowid
                        
                        # Create application record if status is not empty
                        if row['Status'] and row['Status'] != 'Not Applied':
                            cursor.execute("""
                                INSERT INTO applications (
                                    opportunity_id, status, date_applied, interview_date,
                                    offer_status, follow_up_date, notes
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                opportunity_id,
                                row['Status'],
                                row.get('Date Applied', '') or None,
                                row.get('Interview Date', '') or None,
                                row.get('Offer Status', '') or None,
                                row.get('Follow-up Date', '') or None,
                                row.get('Notes', '')
                            ))
            
            logger.info(f"Successfully migrated data from {csv_file}")
            
        except Exception as e:
            logger.error(f"Error migrating from CSV: {e}")
            raise
    
    def _get_sponsorship_from_notes(self, notes: str) -> Dict:
        """Extract sponsorship tier from notes"""
        notes_lower = notes.lower() if notes else ""
        
        if 'no sponsorship' in notes_lower or 'does not sponsor' in notes_lower:
            return {'tier': 4}
        elif 'full sponsorship' in notes_lower or 'likely sponsors' in notes_lower:
            return {'tier': 1}
        elif 'sponsors cpt' in notes_lower:
            return {'tier': 2}
        else:
            return {'tier': 5}
    
    def add_company(self, name: str, **kwargs) -> int:
        """Add a new company"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO companies (name, website, sponsorship_cpt, sponsorship_opt,
                sponsorship_h1b, sponsorship_notes, sponsorship_tier, industry,
                headquarters, founded_year, employee_count, glassdoor_rating, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                kwargs.get('website'),
                kwargs.get('sponsorship_cpt'),
                kwargs.get('sponsorship_opt'),
                kwargs.get('sponsorship_h1b'),
                kwargs.get('sponsorship_notes'),
                kwargs.get('sponsorship_tier', 5),
                kwargs.get('industry'),
                kwargs.get('headquarters'),
                kwargs.get('founded_year'),
                kwargs.get('employee_count'),
                kwargs.get('glassdoor_rating'),
                kwargs.get('notes')
            ))
            
            return cursor.lastrowid
    
    def add_opportunity(self, company_name: str, role: str, link: str, **kwargs) -> int:
        """Add a new opportunity"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get or create company
            cursor.execute("SELECT id FROM companies WHERE name = ?", (company_name,))
            company_result = cursor.fetchone()
            
            if company_result:
                company_id = company_result['id']
            else:
                company_id = self.add_company(company_name)
            
            # Add opportunity
            cursor.execute("""
                INSERT INTO opportunities (company_id, role, location, link, date_posted,
                application_deadline, source, priority, eligibility, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                role,
                kwargs.get('location', ''),
                link,
                kwargs.get('date_posted'),
                kwargs.get('application_deadline'),
                kwargs.get('source', ''),
                kwargs.get('priority', 5),
                kwargs.get('eligibility', ''),
                kwargs.get('notes', '')
            ))
            
            return cursor.lastrowid
    
    def update_application_status(self, opportunity_id: int, status: str, **kwargs) -> bool:
        """Update application status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if application exists
            cursor.execute(
                "SELECT id FROM applications WHERE opportunity_id = ?",
                (opportunity_id,)
            )
            app_result = cursor.fetchone()
            
            if app_result:
                # Update existing application
                cursor.execute("""
                    UPDATE applications SET status = ?, date_applied = ?, interview_date = ?,
                    interview_type = ?, offer_status = ?, follow_up_date = ?, notes = ?
                    WHERE opportunity_id = ?
                """, (
                    status,
                    kwargs.get('date_applied'),
                    kwargs.get('interview_date'),
                    kwargs.get('interview_type'),
                    kwargs.get('offer_status'),
                    kwargs.get('follow_up_date'),
                    kwargs.get('notes'),
                    opportunity_id
                ))
            else:
                # Create new application
                cursor.execute("""
                    INSERT INTO applications (opportunity_id, status, date_applied, interview_date,
                    interview_type, offer_status, follow_up_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    opportunity_id,
                    status,
                    kwargs.get('date_applied'),
                    kwargs.get('interview_date'),
                    kwargs.get('interview_type'),
                    kwargs.get('offer_status'),
                    kwargs.get('follow_up_date'),
                    kwargs.get('notes')
                ))
            
            return True
    
    def get_opportunities(self, filters: Dict = None) -> List[Dict]:
        """Get opportunities with optional filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT o.*, c.name as company_name, c.sponsorship_tier, c.sponsorship_notes,
                       a.status as application_status, a.date_applied, a.interview_date
                FROM opportunities o
                JOIN companies c ON o.company_id = c.id
                LEFT JOIN applications a ON o.id = a.opportunity_id
                WHERE o.is_active = 1
            """
            
            params = []
            
            if filters:
                if 'priority' in filters:
                    query += " AND o.priority IN ({})".format(','.join(['?'] * len(filters['priority'])))
                    params.extend(filters['priority'])
                
                if 'status' in filters:
                    query += " AND a.status IN ({})".format(','.join(['?'] * len(filters['status'])))
                    params.extend(filters['status'])
                
                if 'sponsorship_tier' in filters:
                    query += " AND c.sponsorship_tier <= ?"
                    params.append(filters['sponsorship_tier'])
            
            query += " ORDER BY o.priority, o.date_posted DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_analytics(self) -> Dict:
        """Get application analytics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            analytics = {}
            
            # Total opportunities
            cursor.execute("SELECT COUNT(*) as count FROM opportunities WHERE is_active = 1")
            analytics['total_opportunities'] = cursor.fetchone()['count']
            
            # Application funnel
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM applications 
                GROUP BY status
            """)
            analytics['status_breakdown'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Priority breakdown
            cursor.execute("""
                SELECT priority, COUNT(*) as count 
                FROM opportunities 
                WHERE is_active = 1
                GROUP BY priority
            """)
            analytics['priority_breakdown'] = {row['priority']: row['count'] for row in cursor.fetchall()}
            
            # Sponsorship tier breakdown
            cursor.execute("""
                SELECT sponsorship_tier, COUNT(*) as count 
                FROM companies
                GROUP BY sponsorship_tier
            """)
            analytics['sponsorship_breakdown'] = {row['sponsorship_tier']: row['count'] for row in cursor.fetchall()}
            
            # Application rate
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM applications WHERE status = 'Applied') * 100.0 / 
                    (SELECT COUNT(*) FROM opportunities WHERE is_active = 1) as rate
            """)
            result = cursor.fetchone()
            analytics['application_rate'] = result['rate'] if result['rate'] else 0
            
            return analytics
    
    def backup_database(self, backup_path: str):
        """Backup database to file"""
        import shutil
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
    
    def restore_database(self, backup_path: str):
        """Restore database from backup"""
        import shutil
        try:
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False

def main():
    """Example usage"""
    db = DatabaseManager()
    
    # Migrate from CSV
    # db.migrate_from_csv('Summer2027_SWE_Tracker.csv')
    
    # Add a new opportunity
    # opportunity_id = db.add_opportunity(
    #     company_name="Test Company",
    #     role="Software Engineer Intern",
    #     link="https://example.com/apply",
    #     location="Remote",
    #     priority=1,
    #     source="manual"
    # )
    
    # Get opportunities
    # opportunities = db.get_opportunities({'priority': ['1', '2']})
    # print(f"Found {len(opportunities)} opportunities")
    
    # Get analytics
    # analytics = db.get_analytics()
    # print(f"Analytics: {analytics}")
    
    print("Database manager example")

if __name__ == "__main__":
    main()