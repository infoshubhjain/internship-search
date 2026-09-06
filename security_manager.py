#!/usr/bin/env python3
"""
Security and backup management system
"""
import os
import shutil
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.backup_dir = os.path.join(base_dir, "backups")
        self._initialize_security()
    
    def _initialize_security(self):
        """Initialize security systems"""
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Create .gitignore entry for secrets
        gitignore_path = os.path.join(self.base_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, 'w') as f:
                f.write(".secrets.json\n")
                f.write("backups/\n")
                f.write("token.json\n")
                f.write("credentials.json\n")
                f.write("internship_tracker.log\n")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Read a secret from the environment.

        This previously kept a .secrets.json store whose "encryption" was a
        SHA-256 digest - a one-way hash, so the stored value could never be
        read back and callers received a hex digest where they expected a
        password. Secrets now come from the environment (or a local .env,
        which is gitignored), which is also what GitHub Actions provides.
        """
        value = os.environ.get(key)
        if value:
            return value

        env_path = os.path.join(self.base_dir, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    name, _, raw = line.partition('=')
                    if name.strip() == key:
                        return raw.strip().strip('\'"')
        return None

    def require_secret(self, key: str) -> str:
        """Read a secret, failing loudly if it is not configured."""
        value = self.get_secret(key)
        if not value:
            raise KeyError(
                f"{key} is not set. Export it, or add it to a local .env file."
            )
        return value

    def backup_files(self, files_to_backup: List[str], backup_name: str = None) -> str:
        """Backup specified files"""
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = os.path.join(self.backup_dir, backup_name)
        os.makedirs(backup_path, exist_ok=True)
        
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                dest_path = os.path.join(backup_path, filename)
                shutil.copy2(file_path, dest_path)
                logger.info(f"Backed up: {file_path}")
        
        return backup_path
    
    def backup_database(self, db_path: str = "internship_tracker.db") -> str:
        """Backup SQLite database"""
        if os.path.exists(db_path):
            backup_name = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)
            shutil.copy2(db_path, backup_path)
            logger.info(f"Backed up database to: {backup_path}")
            return backup_path
        else:
            logger.warning(f"Database file not found: {db_path}")
            return ""
    
    def restore_backup(self, backup_path: str, dest_path: str):
        """Restore files from backup"""
        if os.path.exists(backup_path):
            if os.path.isdir(backup_path):
                # Restore directory backup
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(backup_path, dest_path)
            else:
                # Restore single file
                shutil.copy2(backup_path, dest_path)
            
            logger.info(f"Restored backup from: {backup_path}")
        else:
            logger.error(f"Backup not found: {backup_path}")
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        """Clean up old backups"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for item in os.listdir(self.backup_dir):
            item_path = os.path.join(self.backup_dir, item)
            item_time = datetime.fromtimestamp(os.path.getmtime(item_path))
            
            if item_time < cutoff_date:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                
                logger.info(f"Cleaned up old backup: {item}")
    
    def verify_integrity(self, file_path: str) -> bool:
        """Verify file integrity using hash"""
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Store hash for verification
            hash_file = f"{file_path}.sha256"
            
            if os.path.exists(hash_file):
                with open(hash_file, 'r') as f:
                    stored_hash = f.read().strip()
                
                return file_hash == stored_hash
            else:
                # Create hash file
                with open(hash_file, 'w') as f:
                    f.write(file_hash)
                return True
                
        except Exception as e:
            logger.error(f"Error verifying integrity: {e}")
            return False
    
    def generate_security_report(self) -> Dict:
        """Generate security report"""
        report = {
            'timestamp': datetime.now().isoformat(),

            'backups_count': len(os.listdir(self.backup_dir)) if os.path.exists(self.backup_dir) else 0,
            'recent_backups': [],
            'security_checks': {
                'gitignore_configured': os.path.exists(os.path.join(self.base_dir, ".gitignore")),
                'backup_dir_exists': os.path.exists(self.backup_dir)
            }
        }
        
        # List recent backups
        if os.path.exists(self.backup_dir):
            backups = sorted(
                [os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir)],
                key=os.path.getmtime,
                reverse=True
            )
            report['recent_backups'] = backups[:5]
        
        return report

class AccessControl:
    """Simple access control for sensitive operations"""
    
    def __init__(self):
        self.access_log = []
    
    def log_access(self, operation: str, user: str = "system", success: bool = True):
        """Log access attempt"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'user': user,
            'success': success
        }
        
        self.access_log.append(log_entry)
        logger.info(f"Access log: {log_entry}")
    
    def check_permission(self, operation: str, user: str = "system") -> bool:
        """Check if user has permission for operation"""
        # Simple permission check (in production, implement proper RBAC)
        allowed_operations = {
            'system': ['all'],
            'admin': ['read', 'write', 'delete', 'backup', 'restore'],
            'user': ['read', 'write']
        }
        
        user_role = 'user'  # In production, get from authentication
        
        if operation == 'all':
            return True
        
        if user_role in allowed_operations:
            if 'all' in allowed_operations[user_role] or operation in allowed_operations[user_role]:
                return True
        
        self.log_access(operation, user, success=False)
        return False

def main():
    """Example usage"""
    security = SecurityManager()
    
    # Store a secret
    
    # Backup files
    # backup_path = security.backup_files(['Summer2027_SWE_Tracker.csv', 'scraped_internships.csv'])
    # print(f"Backup created: {backup_path}")
    
    # Backup database
    # db_backup = security.backup_database()
    # print(f"Database backup: {db_backup}")
    
    # Generate security report
    report = security.generate_security_report()
    print(f"Security report: {report}")
    
    # Clean up old backups
    # security.cleanup_old_backups(days_to_keep=30)

if __name__ == "__main__":
    main()