#!/usr/bin/env python3
"""
Master integration script that ties all systems together
"""
import logging
import sys

from tracker_io import SCRAPED_FILE, TRACKER_FILE

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
    """Scrape all sources and merge into the tracker.

    Delegates to update_all so the scrape and the merge always read and write
    the same files; running the scrape alone would leave the tracker stale.
    """
    logger.info("Starting data update...")

    try:
        import update_all
        return update_all.main() == 0
    except Exception as e:
        logger.error(f"Data update failed: {e}")
        return False

def run_deadline_checks():
    """Check for upcoming deadlines and send alerts"""
    logger.info("Running deadline checks...")
    
    try:
        from deadline_tracker import DeadlineTracker
        
        tracker = DeadlineTracker(TRACKER_FILE)
        
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
    """Report the high-priority listings the last merge actually added.

    This used to infer novelty by comparing 'Date Posted' against a saved
    timestamp - but the merge stamps that field itself, so every row looked
    new on a first run. The merge now records exactly what it added.
    """
    logger.info("Running priority alerts...")

    try:
        from merge_internship_data import read_new_listings

        new_opps = read_new_listings()
        if not new_opps:
            logger.info("No new priority 1-2 listings since the last merge")
            return True

        logger.info(f"Found {len(new_opps)} new priority opportunities")
        for opp in new_opps:
            logger.info(f"NEW: P{opp.get('Priority')} {opp.get('Company')} - {opp.get('Role')}")

        from notification_system import NotificationSystem

        notifier = NotificationSystem()
        if notifier.email_config:
            notifier.send_priority_alert(new_opps, notifier.email_config['email'])
        else:
            logger.info("Email not configured; alerts logged only")

        return True

    except Exception as e:
        logger.error(f"Priority alerts failed: {e}")
        return False


def run_international():
    """Search company boards for international Summer 2027 internships."""
    logger.info("Running international search...")

    try:
        import intl_tracker
        return intl_tracker.run() == 0
    except Exception as e:
        logger.error(f"International search failed: {e}")
        return False


def run_weekly_summary():
    """Generate weekly summary"""
    logger.info("Running weekly summary...")
    
    try:
        import csv
        
        # Calculate basic statistics
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
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
        
        from tracker_io import INTL_TRACKER_FILE
        for path in (TRACKER_FILE, SCRAPED_FILE, INTL_TRACKER_FILE):
            if os.path.exists(path):
                files_to_backup.append(path)
        
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
        
        logger.info(f"Security check completed: {report['backups_count']} backups")
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
        elif command == "international":
            success = run_international()
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
                'international': run_international(),
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