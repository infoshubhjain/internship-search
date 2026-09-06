#!/usr/bin/env python3
"""
Skill gap analysis for identifying areas to improve based on job requirements
"""
import logging
from typing import Dict, List, Set
from collections import Counter

logger = logging.getLogger(__name__)

class SkillGapAnalyzer:
    def __init__(self):
        self.common_skills = self._load_common_skills()
        self.skill_categories = self._load_skill_categories()
    
    def _load_common_skills(self) -> Dict[str, List[str]]:
        """Load common technical skills by category"""
        return {
            'programming_languages': [
                'Python', 'Java', 'C++', 'JavaScript', 'TypeScript', 'Go', 'Rust',
                'Swift', 'Objective-C', 'C#', '.NET', 'PHP', 'Ruby', 'Kotlin', 'Scala'
            ],
            'frameworks_libraries': [
                'React', 'Angular', 'Vue.js', 'Node.js', 'Express', 'Django', 'Flask',
                'Spring Boot', 'Rails', 'Laravel', 'TensorFlow', 'PyTorch', 'Keras',
                'Pandas', 'NumPy', 'Spring', '.NET Core', 'Entity Framework'
            ],
            'databases': [
                'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch',
                'Cassandra', 'DynamoDB', 'SQLite', 'Oracle', 'SQL Server'
            ],
            'cloud_platforms': [
                'AWS', 'Azure', 'Google Cloud', 'Heroku', 'DigitalOcean', 'Firebase'
            ],
            'devops_tools': [
                'Docker', 'Kubernetes', 'Jenkins', 'Git', 'CI/CD', 'Terraform',
                'Ansible', 'Puppet', 'Chef', 'Linux', 'Bash', 'Shell scripting'
            ],
            'data_structures': [
                'Arrays', 'Linked Lists', 'Trees', 'Graphs', 'Hash Tables',
                'Stacks', 'Queues', 'Heaps', 'Tries', 'Binary Search Trees'
            ],
            'algorithms': [
                'Sorting', 'Searching', 'Dynamic Programming', 'Greedy Algorithms',
                'Graph Algorithms', 'Tree Traversal', 'Divide and Conquer', 'Backtracking'
            ],
            'soft_skills': [
                'Communication', 'Teamwork', 'Problem Solving', 'Leadership',
                'Time Management', 'Adaptability', 'Critical Thinking'
            ]
        }
    
    def _load_skill_categories(self) -> Dict[str, str]:
        """Load skill category mappings"""
        categories = {}
        for category, skills in self.common_skills.items():
            for skill in skills:
                categories[skill.lower()] = category
        
        return categories
    
    def extract_skills_from_job_description(self, job_description: str) -> Set[str]:
        """Extract skills from job description text"""
        found_skills = set()
        description_lower = job_description.lower()
        
        for category, skills in self.common_skills.items():
            for skill in skills:
                if skill.lower() in description_lower:
                    found_skills.add(skill)
        
        return found_skills
    
    def extract_skills_from_requirements(self, requirements_text: str) -> Set[str]:
        """Extract skills from requirements section"""
        return self.extract_skills_from_job_description(requirements_text)
    
    def analyze_skill_gaps(self, your_skills: List[str], job_requirements: List[str]) -> Dict:
        """Analyze skill gaps between your skills and job requirements"""
        your_skills_set = set(skill.lower() for skill in your_skills)
        job_requirements_set = set(req.lower() for req in job_requirements)
        
        matched_skills = your_skills_set.intersection(job_requirements_set)
        missing_skills = job_requirements_set - your_skills_set
        extra_skills = your_skills_set - job_requirements_set
        
        # Convert back to original case
        matched_skills_original = [skill for skill in your_skills if skill.lower() in matched_skills]
        missing_skills_original = [req for req in job_requirements if req.lower() in missing_skills]
        extra_skills_original = [skill for skill in your_skills if skill.lower() in extra_skills]
        
        match_percentage = (len(matched_skills) / len(job_requirements) * 100) if job_requirements else 0
        
        return {
            'matched_skills': matched_skills_original,
            'missing_skills': missing_skills_original,
            'extra_skills': extra_skills_original,
            'match_percentage': match_percentage,
            'total_requirements': len(job_requirements),
            'total_matched': len(matched_skills),
            'total_missing': len(missing_skills)
        }
    
    def analyze_opportunity_fit(self, your_skills: List[str], opportunity_data: Dict) -> Dict:
        """Analyze how well your skills match an opportunity"""
        job_description = opportunity_data.get('description', '')
        role = opportunity_data.get('role', '')
        
        # Extract skills from role and description
        all_text = f"{role} {job_description}"
        required_skills = self.extract_skills_from_job_description(all_text)
        
        # Analyze gaps
        gap_analysis = self.analyze_skill_gaps(your_skills, list(required_skills))
        
        # Add recommendation
        if gap_analysis['match_percentage'] >= 70:
            recommendation = "Strong match - highly recommended to apply"
        elif gap_analysis['match_percentage'] >= 50:
            recommendation = "Good match - recommended to apply"
        elif gap_analysis['match_percentage'] >= 30:
            recommendation = "Moderate match - consider applying if willing to learn"
        else:
            recommendation = "Low match - focus on building missing skills first"
        
        gap_analysis['recommendation'] = recommendation
        
        return gap_analysis
    
    def get_most_requested_skills(self, opportunities: List[Dict]) -> Dict[str, int]:
        """Get most frequently requested skills across opportunities"""
        skill_counter = Counter()
        
        for opportunity in opportunities:
            description = opportunity.get('description', '')
            role = opportunity.get('role', '')
            
            all_text = f"{role} {description}"
            skills = self.extract_skills_from_job_description(all_text)
            
            skill_counter.update(skills)
        
        return dict(skill_counter.most_common(20))
    
    def get_learning_recommendations(self, missing_skills: List[str]) -> List[Dict]:
        """Get learning recommendations for missing skills"""
        recommendations = []
        
        skill_resources = {
            'Python': {
                'difficulty': 'Beginner',
                'time_estimate': '2-4 weeks',
                'resources': ['Codecademy', 'Coursera', 'freeCodeCamp'],
                'projects': ['Web scraper', 'Data analysis script', 'Automation tool']
            },
            'Java': {
                'difficulty': 'Intermediate',
                'time_estimate': '4-6 weeks',
                'resources': ['Oracle tutorials', 'Coursera', 'Udemy'],
                'projects': ['Android app', 'Spring Boot API', 'Console application']
            },
            'React': {
                'difficulty': 'Intermediate',
                'time_estimate': '3-5 weeks',
                'resources': ['React documentation', 'freeCodeCamp', 'Scrimba'],
                'projects': ['Todo app', 'Weather app', 'Portfolio site']
            },
            'AWS': {
                'difficulty': 'Advanced',
                'time_estimate': '6-8 weeks',
                'resources': ['AWS Training', 'A Cloud Guru', 'Udemy'],
                'projects': ['Deploy web app', 'Serverless function', 'CI/CD pipeline']
            },
            'Machine Learning': {
                'difficulty': 'Advanced',
                'time_estimate': '8-12 weeks',
                'resources': ['Coursera ML course', 'Fast.ai', 'Kaggle'],
                'projects': ['Image classifier', 'Sentiment analysis', 'Recommendation system']
            }
        }
        
        for skill in missing_skills:
            if skill in skill_resources:
                recommendations.append({
                    'skill': skill,
                    **skill_resources[skill]
                })
            else:
                recommendations.append({
                    'skill': skill,
                    'difficulty': 'Unknown',
                    'time_estimate': '4-8 weeks',
                    'resources': ['Google search', 'Documentation', 'YouTube tutorials'],
                    'projects': ['Practice project', 'Tutorial project', 'Contribution to open source']
                })
        
        return recommendations
    
    def prioritize_skill_learning(self, missing_skills: List[str], 
                                 skill_demand: Dict[str, int]) -> List[Dict]:
        """Prioritize skills to learn based on demand and difficulty"""
        prioritized = []
        
        for skill in missing_skills:
            demand = skill_demand.get(skill, 0)
            
            # Simple priority scoring
            priority_score = demand  # Higher demand = higher priority
            
            prioritized.append({
                'skill': skill,
                'demand': demand,
                'priority_score': priority_score
            })
        
        # Sort by priority score
        prioritized.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return prioritized

def main():
    """Example usage"""
    analyzer = SkillGapAnalyzer()
    
    # Your current skills
    my_skills = ['Python', 'Java', 'JavaScript', 'SQL', 'Git', 'Docker']
    
    # Job requirements
    job_requirements = ['Python', 'Java', 'React', 'AWS', 'Docker', 'SQL', 'Git']
    
    # Analyze gaps
    gap_analysis = analyzer.analyze_skill_gaps(my_skills, job_requirements)
    print(f"Skill gap analysis: {gap_analysis}")
    
    # Get learning recommendations
    missing = gap_analysis['missing_skills']
    recommendations = analyzer.get_learning_recommendations(missing)
    print(f"Learning recommendations: {recommendations}")
    
    # Analyze opportunity fit
    opportunity = {
        'role': 'Software Engineer Intern',
        'description': 'We are looking for a software engineer intern with experience in Python, Java, React, and AWS. Knowledge of Docker and SQL is a plus.'
    }
    
    fit_analysis = analyzer.analyze_opportunity_fit(my_skills, opportunity)
    print(f"Opportunity fit: {fit_analysis}")

if __name__ == "__main__":
    main()