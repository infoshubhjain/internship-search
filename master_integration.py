#!/usr/bin/env python3
"""
Master integration script that ties all systems together
"""
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('internship_tracker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_data_update():
    """Update data from all sources"""
    logger.info("Starting data update...")
    
    try:
        from enhanced_scraper import scrape_all_sources
        
        # Scrape data
        internships = scrape_all_sources()
        
        # Save to CSV (keeping CSV as primary format for now)
        import csv
        with open('enhanced_scraped_internships.csv', 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['company', 'role', 'location', 'link', 'no_sponsorship', 'source', 
                         'sponsorship_tier', 'sponsorship_notes']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(internships)
        
        logger.info(f"Data update completed: {len(internships)} internships")
        return True
        
    except Exception as e:
        logger.error(f"Data update failed: {e}")
        return False

def run_deadline_checks():
    """Check for upcoming deadlines and send alerts"""
    logger.info("Running deadline checks...")
    
    try:
        from deadline_tracker import DeadlineTracker
        
        tracker = DeadlineTracker('Summer2027_SWE_Tracker.csv')
        
        # Get upcoming deadlines
        upcoming = tracker.get_upcoming_deadlines(days_ahead=7)
        
        if upcoming:
            logger.info(f"Found {len(upcoming)} upcoming deadlines")
            for item in upcoming:
                logger.info(f"UPCOMING: {item['company']} - {item['days_remaining']} days")
        
        # Mark expired opportunities
        tracker.mark_expired_as_closed()
        
        logger.info("Deadline checks completed")
        return True
        
    except Exception as e:
        logger.error(f"Deadline checks failed: {e}")
        return False

def run_priority_alerts():
    """Check for new high-priority opportunities"""
    logger.info("Running priority alerts...")
    
    try:
        import csv
        from datetime import datetime, timedelta
        
        # Simple check for new opportunities
        try:
            with open('last_check.txt', 'r') as f:
                last_check = datetime.fromisoformat(f.read().strip())
        except FileNotFoundError:
            last_check = datetime.now() - timedelta(days=1)
        
        new_opps = []
        with open('Summer2027_SWE_Tracker.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Priority'] in ['1', '2'] and row['Status'] == 'Not Applied':
                    date_posted = row.get('Date Posted', '')
                    if date_posted:
                        try:
                            post_date = datetime.fromisoformat(date_posted)
                            if post_date > last_check:
                                new_opps.append(row)
                        except ValueError:
                            pass
        
        # Update last check time
        with open('last_check.txt', 'w') as f:
            f.write(datetime.now().isoformat())
        
        if new_opps:
            logger.info(f"Found {len(new_opps)} new priority opportunities")
            for opp in new_opps:
                logger.info(f"NEW: {opp['Company']} - {opp['Role']}")
        
        logger.info("Priority alerts completed")
        return True
        
    except Exception as e:
        logger.error(f"Priority alerts failed: {e}")
        return False

def run_weekly_summary():
    """Generate weekly summary"""
    logger.info("Running weekly summary...")
    
    try:
        import csv
        
        # Calculate basic statistics
        with open('Summer2027_SWE_Tracker.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        total = len(rows)
        applied = len([r for r in rows if r['Status'] == 'Applied'])
        interviewing = len([r for r in rows if r['Status'] == 'Interviewing'])
        offers = len([r for r in rows if r['Offer Status'] == 'Offer'])
        
        logger.info(f"Weekly summary: Total={total}, Applied={applied}, Interviewing={interviewing}, Offers={offers}")
        logger.info("Weekly summary completed")
        return True
        
    except Exception as e:
        logger.error(f"Weekly summary failed: {e}")
        return False

def run_backup():
    """Run system backup"""
    logger.info("Running system backup...")
    
    try:
        from security_manager import SecurityManager
        import os
        
        security = SecurityManager()
        
        # Backup important files (only CSV files since we're not using DB yet)
        files_to_backup = []
        
        if os.path.exists('Summer2027_SWE_Tracker.csv'):
            files_to_backup.append('Summer2027_SWE_Tracker.csv')
        if os.path.exists('scraped_internships.csv'):
            files_to_backup.append('scraped_internships.csv')
        if os.path.exists('enhanced_scraped_internships.csv'):
            files_to_backup.append('enhanced_scraped_internships.csv')
        
        if files_to_backup:
            backup_path = security.backup_files(files_to_backup)
            # Clean up old backups
            security.cleanup_old_backups(days_to_keep=30)
            logger.info(f"Backup completed: {backup_path}")
        else:
            logger.info("No files to backup")
        
        return True
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False

def run_security_check():
    """Run security check"""
    logger.info("Running security check...")
    
    try:
        from security_manager import SecurityManager
        
        security = SecurityManager()
        
        # Generate security report
        report = security.generate_security_report()
        
        logger.info(f"Security check completed: {report['secrets_count']} secrets, {report['backups_count']} backups")
        return True
        
    except Exception as e:
        logger.error(f"Security check failed: {e}")
        return False

def main():
    """Main integration function"""
    logger.info("Starting master integration...")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "update":
            success = run_data_update()
        elif command == "deadlines":
            success = run_deadline_checks()
        elif command == "alerts":
            success = run_priority_alerts()
        elif command == "weekly":
            success = run_weekly_summary()
        elif command == "backup":
            success = run_backup()
        elif command == "security":
            success = run_security_check()
        elif command == "all":
            # Run all functions
            results = {
                'data_update': run_data_update(),
                'deadlines': run_deadline_checks(),
                'alerts': run_priority_alerts(),
                'backup': run_backup(),
                'security': run_security_check()
            }
            
            success = all(results.values())
            logger.info(f"All functions completed: {results}")
        else:
            logger.error(f"Unknown command: {command}")
            success = False
    else:
        # Default: run data update
        success = run_data_update()
    
    if success:
        logger.info("Master integration completed successfully")
        sys.exit(0)
    else:
        logger.error("Master integration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()