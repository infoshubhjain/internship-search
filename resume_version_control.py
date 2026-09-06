#!/usr/bin/env python3
"""
Resume version control system for tracking different resume versions
"""
import os
import shutil
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)

@dataclass
class ResumeVersion:
    """Resume version metadata"""
    version_id: str
    name: str
    description: str
    file_path: str
    target_company_type: str
    created_at: datetime
    file_hash: str
    used_count: int = 0
    success_count: int = 0

class ResumeVersionControl:
    def __init__(self, base_dir: str = "resumes"):
        self.base_dir = base_dir
        self.versions = {}
        self._initialize_directories()
        self._load_versions()
    
    def _initialize_directories(self):
        """Create necessary directories"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "versions"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "templates"), exist_ok=True)
    
    def _load_versions(self):
        """Load existing version metadata"""
        metadata_file = os.path.join(self.base_dir, "versions", "metadata.json")
        
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                    for version_id, version_data in data.items():
                        version_data['created_at'] = datetime.fromisoformat(version_data['created_at'])
                        self.versions[version_id] = ResumeVersion(**version_data)
                
                logger.info(f"Loaded {len(self.versions)} resume versions")
            except Exception as e:
                logger.error(f"Error loading versions: {e}")
    
    def _save_versions(self):
        """Save version metadata"""
        metadata_file = os.path.join(self.base_dir, "versions", "metadata.json")
        
        try:
            serializable_versions = {}
            for version_id, version in self.versions.items():
                version_dict = asdict(version)
                version_dict['created_at'] = version.created_at.isoformat()
                serializable_versions[version_id] = version_dict
            
            with open(metadata_file, 'w') as f:
                json.dump(serializable_versions, f, indent=2)
            
            logger.info("Saved resume versions metadata")
            
        except Exception as e:
            logger.error(f"Error saving versions: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def create_version(self, source_file: str, name: str, description: str, 
                      target_company_type: str) -> str:
        """Create a new resume version"""
        try:
            # Generate version ID
            version_id = f"v{len(self.versions) + 1:03d}_{datetime.now().strftime('%Y%m%d')}"
            
            # Copy file to versions directory
            version_filename = f"{version_id}_{os.path.basename(source_file)}"
            version_path = os.path.join(self.base_dir, "versions", version_filename)
            shutil.copy2(source_file, version_path)
            
            # Calculate file hash
            file_hash = self._calculate_file_hash(version_path)
            
            # Create version metadata
            version = ResumeVersion(
                version_id=version_id,
                name=name,
                description=description,
                file_path=version_path,
                target_company_type=target_company_type,
                created_at=datetime.now(),
                file_hash=file_hash
            )
            
            self.versions[version_id] = version
            self._save_versions()
            
            logger.info(f"Created resume version: {version_id}")
            return version_id
            
        except Exception as e:
            logger.error(f"Error creating resume version: {e}")
            raise
    
    def get_version(self, version_id: str) -> Optional[ResumeVersion]:
        """Get a specific resume version"""
        return self.versions.get(version_id)
    
    def list_versions(self, target_type: str = None) -> List[ResumeVersion]:
        """List all resume versions, optionally filtered by target type"""
        versions = list(self.versions.values())
        
        if target_type:
            versions = [v for v in versions if v.target_company_type == target_type]
        
        return sorted(versions, key=lambda x: x.created_at, reverse=True)
    
    def get_recommended_version(self, company_name: str) -> Optional[str]:
        """Get recommended resume version for a company"""
        company_lower = company_name.lower()
        
        # Simple recommendation logic
        if any(big_tech in company_lower for big_tech in ['google', 'microsoft', 'amazon', 'meta', 'apple']):
            target_type = 'big_tech'
        elif any(bank in company_lower for bank in ['jpmorgan', 'goldman', 'morgan', 'bank', 'citi']):
            target_type = 'finance'
        elif any(startup in company_lower for startup in ['startup', 'tech', 'software']):
            target_type = 'startup'
        else:
            target_type = 'general'
        
        # Get most recent version for target type
        versions = self.list_versions(target_type)
        
        if versions:
            return versions[0].version_id
        
        # Fallback to most recent general version
        general_versions = self.list_versions('general')
        if general_versions:
            return general_versions[0].version_id
        
        return None
    
    def record_usage(self, version_id: str, success: bool = False):
        """Record that a version was used"""
        if version_id in self.versions:
            self.versions[version_id].used_count += 1
            if success:
                self.versions[version_id].success_count += 1
            self._save_versions()
    
    def get_version_stats(self) -> Dict:
        """Get statistics about resume versions"""
        stats = {
            'total_versions': len(self.versions),
            'total_uses': sum(v.used_count for v in self.versions.values()),
            'total_successes': sum(v.success_count for v in self.versions.values()),
            'success_rate': 0.0,
            'by_type': {},
            'top_performers': []
        }
        
        if stats['total_uses'] > 0:
            stats['success_rate'] = (stats['total_successes'] / stats['total_uses']) * 100
        
        # Stats by type
        for version in self.versions.values():
            if version.target_company_type not in stats['by_type']:
                stats['by_type'][version.target_company_type] = {
                    'count': 0,
                    'uses': 0,
                    'successes': 0
                }
            
            stats['by_type'][version.target_company_type]['count'] += 1
            stats['by_type'][version.target_company_type]['uses'] += version.used_count
            stats['by_type'][version.target_company_type]['successes'] += version.success_count
        
        # Top performers
        performers = sorted(
            self.versions.values(),
            key=lambda x: x.success_count / x.used_count if x.used_count > 0 else 0,
            reverse=True
        )
        stats['top_performers'] = [
            {'version_id': v.version_id, 'name': v.name, 'success_rate': v.success_count / v.used_count if v.used_count > 0 else 0}
            for v in performers[:5]
        ]
        
        return stats
    
    def create_template(self, name: str, content: str):
        """Create a resume template"""
        template_path = os.path.join(self.base_dir, "templates", f"{name}.txt")
        
        with open(template_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Created resume template: {name}")
    
    def get_template(self, name: str) -> Optional[str]:
        """Get a resume template"""
        template_path = os.path.join(self.base_dir, "templates", f"{name}.txt")
        
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read()
        
        return None
    
    def list_templates(self) -> List[str]:
        """List available resume templates"""
        templates_dir = os.path.join(self.base_dir, "templates")
        
        if os.path.exists(templates_dir):
            return [f.replace('.txt', '') for f in os.listdir(templates_dir) if f.endswith('.txt')]
        
        return []

def main():
    """Example usage"""
    rvc = ResumeVersionControl()
    
    # Create a new version (example)
    # version_id = rvc.create_version(
    #     source_file="my_resume.pdf",
    #     name="Technical Resume v1",
    #     description="Focus on technical skills and projects",
    #     target_company_type="big_tech"
    # )
    
    # List versions
    versions = rvc.list_versions()
    print(f"Resume versions: {len(versions)}")
    
    # Get recommended version
    recommended = rvc.get_recommended_version("Google")
    print(f"Recommended version for Google: {recommended}")
    
    # Get statistics
    stats = rvc.get_version_stats()
    print(f"Resume stats: {stats}")

if __name__ == "__main__":
    main()