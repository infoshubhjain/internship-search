#!/usr/bin/env python3
"""
A/B testing framework for optimizing application strategies
"""
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class TestType(Enum):
    RESUME_VERSION = "resume_version"
    COVER_LETTER_TEMPLATE = "cover_letter_template"
    APPLICATION_TIMING = "application_timing"
    FOLLOW_UP_STRATEGY = "follow_up_strategy"

@dataclass
class ABTest:
    """A/B test configuration"""
    test_id: str
    test_name: str
    test_type: TestType
    variant_a: Dict
    variant_b: Dict
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "active"
    metrics: Dict = None
    results: Dict = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if self.results is None:
            self.results = {}

class ABTestingFramework:
    def __init__(self):
        self.active_tests = {}
        self.completed_tests = {}
        self._load_default_tests()
    
    def _load_default_tests(self):
        """Load default A/B tests"""
        
        # Resume version test
        resume_test = ABTest(
            test_id="resume_version_test_001",
            test_name="Resume Version A/B Test",
            test_type=TestType.RESUME_VERSION,
            variant_a={
                'name': 'Technical Resume',
                'description': 'Focus on technical skills and projects',
                'sections': ['Skills', 'Projects', 'Experience', 'Education']
            },
            variant_b={
                'name': 'Balanced Resume',
                'description': 'Balance of technical and soft skills',
                'sections': ['Summary', 'Skills', 'Experience', 'Projects', 'Education']
            },
            start_date=datetime.now(),
            metrics={'applications': 0, 'interviews': 0, 'offers': 0}
        )
        
        # Application timing test
        timing_test = ABTest(
            test_id="timing_test_001",
            test_name="Application Timing A/B Test",
            test_type=TestType.APPLICATION_TIMING,
            variant_a={
                'name': 'Morning Applications',
                'description': 'Submit applications between 9-11 AM',
                'time_range': '09:00-11:00'
            },
            variant_b={
                'name': 'Evening Applications',
                'description': 'Submit applications between 6-8 PM',
                'time_range': '18:00-20:00'
            },
            start_date=datetime.now(),
            metrics={'applications': 0, 'responses': 0, 'interviews': 0}
        )
        
        self.active_tests['resume_version_test_001'] = resume_test
        self.active_tests['timing_test_001'] = timing_test
    
    def create_test(self, test: ABTest) -> str:
        """Create a new A/B test"""
        self.active_tests[test.test_id] = test
        logger.info(f"Created A/B test: {test.test_name}")
        return test.test_id
    
    def assign_variant(self, test_id: str, entity_id: str) -> str:
        """Assign a variant (A or B) to an entity"""
        if test_id not in self.active_tests:
            logger.warning(f"Test {test_id} not found")
            return "A"
        
        # Simple hash-based assignment for consistency
        hash_value = hash(entity_id) % 2
        variant = "A" if hash_value == 0 else "B"
        
        logger.debug(f"Assigned variant {variant} to {entity_id} for test {test_id}")
        return variant
    
    def record_metric(self, test_id: str, variant: str, metric_name: str, value: int = 1):
        """Record a metric for a specific variant"""
        if test_id not in self.active_tests:
            logger.warning(f"Test {test_id} not found")
            return
        
        test = self.active_tests[test_id]
        
        metric_key = f"{variant}_{metric_name}"
        test.metrics[metric_key] = test.metrics.get(metric_key, 0) + value
        
        logger.debug(f"Recorded metric {metric_name}={value} for variant {variant} in test {test_id}")
    
    def complete_test(self, test_id: str, results: Dict = None):
        """Mark a test as complete and analyze results"""
        if test_id not in self.active_tests:
            logger.warning(f"Test {test_id} not found")
            return
        
        test = self.active_tests[test_id]
        test.end_date = datetime.now()
        test.status = "completed"
        
        if results:
            test.results = results
        else:
            test.results = self._analyze_results(test)
        
        # Move to completed tests
        self.completed_tests[test_id] = test
        del self.active_tests[test_id]
        
        logger.info(f"Completed test {test_id} with results: {test.results}")
    
    def _analyze_results(self, test: ABTest) -> Dict:
        """Analyze test results and determine winner"""
        results = {
            'test_id': test.test_id,
            'test_name': test.test_name,
            'duration_days': (test.end_date - test.start_date).days,
            'variant_a_metrics': {},
            'variant_b_metrics': {},
            'winner': None,
            'confidence': 0.0,
            'recommendation': ''
        }
        
        # Extract metrics for each variant
        for key, value in test.metrics.items():
            if key.startswith('A_'):
                metric_name = key[2:]
                results['variant_a_metrics'][metric_name] = value
            elif key.startswith('B_'):
                metric_name = key[2:]
                results['variant_b_metrics'][metric_name] = value
        
        # Simple comparison (in real implementation, use statistical tests)
        variant_a_total = sum(results['variant_a_metrics'].values())
        variant_b_total = sum(results['variant_b_metrics'].values())
        
        if variant_a_total > variant_b_total:
            results['winner'] = 'A'
            results['confidence'] = min(95, (variant_a_total / (variant_a_total + variant_b_total)) * 100)
            results['recommendation'] = f"Variant A ({test.variant_a['name']}) performed better"
        elif variant_b_total > variant_a_total:
            results['winner'] = 'B'
            results['confidence'] = min(95, (variant_b_total / (variant_a_total + variant_b_total)) * 100)
            results['recommendation'] = f"Variant B ({test.variant_b['name']}) performed better"
        else:
            results['winner'] = 'tie'
            results['confidence'] = 0.0
            results['recommendation'] = "No significant difference between variants"
        
        return results
    
    def get_test_results(self, test_id: str) -> Optional[Dict]:
        """Get results for a specific test"""
        if test_id in self.completed_tests:
            return self.completed_tests[test_id].results
        elif test_id in self.active_tests:
            return self._analyze_results(self.active_tests[test_id])
        else:
            return None
    
    def get_all_tests(self) -> Dict[str, List[Dict]]:
        """Get all tests with their status"""
        all_tests = {
            'active': [asdict(test) for test in self.active_tests.values()],
            'completed': [asdict(test) for test in self.completed_tests.values()]
        }
        return all_tests
    
    def export_results(self, filepath: str):
        """Export all test results to JSON file"""
        try:
            export_data = {
                'active_tests': {k: asdict(v) for k, v in self.active_tests.items()},
                'completed_tests': {k: asdict(v) for k, v in self.completed_tests.items()},
                'export_date': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported A/B test results to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")

def main():
    """Example usage"""
    framework = ABTestingFramework()
    
    # Create a custom test
    cover_letter_test = ABTest(
        test_id="cover_letter_test_001",
        test_name="Cover Letter Template A/B Test",
        test_type=TestType.COVER_LETTER_TEMPLATE,
        variant_a={
            'name': 'Standard Template',
            'description': 'Traditional cover letter format',
            'template': 'standard'
        },
        variant_b={
            'name': 'Conversational Template',
            'description': 'More casual, conversational tone',
            'template': 'conversational'
        },
        start_date=datetime.now(),
        metrics={'applications': 0, 'responses': 0}
    )
    
    framework.create_test(cover_letter_test)
    
    # Assign variants to companies
    companies = ['Google', 'Microsoft', 'Amazon', 'Meta', 'Apple']
    for company in companies:
        variant = framework.assign_variant('resume_version_test_001', company)
        print(f"{company} assigned to variant {variant}")
    
    # Record some metrics
    framework.record_metric('resume_version_test_001', 'A', 'applications', 5)
    framework.record_metric('resume_version_test_001', 'B', 'applications', 3)
    framework.record_metric('resume_version_test_001', 'A', 'interviews', 2)
    framework.record_metric('resume_version_test_001', 'B', 'interviews', 1)
    
    # Complete a test
    framework.complete_test('resume_version_test_001')
    
    # Get results
    results = framework.get_test_results('resume_version_test_001')
    print(f"Test results: {results}")
    
    # Get all tests
    all_tests = framework.get_all_tests()
    print(f"All tests: {all_tests}")

if __name__ == "__main__":
    main()