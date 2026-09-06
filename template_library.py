#!/usr/bin/env python3
"""
Template library for cover letters, emails, and communications
"""
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class TemplateLibrary:
    def __init__(self):
        self.templates = {
            'cover_letters': {},
            'emails': {},
            'follow_ups': {},
            'thank_you': {},
            'withdrawal': {}
        }
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default communication templates"""
        
        # Cover letter templates
        self.templates['cover_letters'] = {
            'underclassman_program': """
Dear Hiring Manager,

I am writing to express my strong interest in the {role} position at {company}. As a sophomore Computer Science student at UIUC, I am particularly excited about {company}'s commitment to developing early-career talent through your underclassman program.

My academic background in computer science, combined with my passion for {relevant_skill}, has prepared me well for this opportunity. I have experience with {tech_stack_1} and {tech_stack_2}, which I believe aligns well with the requirements of this position.

I am particularly drawn to {company} because of {company_specific_reason}. I admire your work on {specific_project_or_initiative} and would be thrilled to contribute to similar projects.

As an F-1 international student, I am authorized for CPT work authorization during my internship and am excited about the possibility of contributing to {company}'s innovative team.

Thank you for considering my application. I look forward to the opportunity to discuss how my skills and enthusiasm would be a great fit for your team.

Best regards,
{your_name}
{your_email}
{your_phone}
""",
            'big_tech': """
Dear Hiring Team,

I am excited to apply for the {role} position at {company}. As a Computer Science student at UIUC with a strong foundation in {relevant_area}, I am eager to contribute to {company}'s mission of {company_mission}.

Through my coursework and personal projects, I have developed proficiency in {tech_stack_1}, {tech_stack_2}, and {tech_stack_3}. My experience includes {specific_experience_or_project}, where I {specific_achievement}.

I have long admired {company}'s impact on the tech industry, particularly in {specific_area}. The opportunity to work alongside talented engineers at {company} would be invaluable for my growth and contribution.

I am authorized for CPT work authorization during my internship and am enthusiastic about the possibility of joining {company}'s team.

Thank you for your time and consideration. I look forward to potentially discussing this opportunity further.

Sincerely,
{your_name}
{your_email}
{your_phone}
""",
            'fintech': """
Dear Hiring Manager,

I am writing to apply for the {role} position at {company}. As a Computer Science student at UIUC with a strong interest in financial technology, I am excited about the opportunity to contribute to {company}'s innovative solutions in the fintech space.

My technical skills include {tech_stack_1} and {tech_stack_2}, which I have applied in projects involving {relevant_experience}. I am particularly fascinated by {specific_fintech_interest}, and I believe {company}'s approach to {company_approach} is industry-leading.

I understand that {company} values {company_value}, which aligns perfectly with my own approach to {your_approach}. As an F-1 student with CPT authorization, I am eager to bring my technical skills and enthusiasm to your team.

Thank you for considering my application. I would welcome the opportunity to discuss how I can contribute to {company}'s continued success.

Best regards,
{your_name}
{your_email}
{your_phone}
"""
        }
        
        # Email templates
        self.templates['emails'] = {
            'application_submission': """
Subject: Application for {role} Position - {your_name}

Dear Hiring Manager,

I hope this email finds you well. I am writing to submit my application for the {role} position at {company}.

I have attached my resume and would appreciate the opportunity to discuss my qualifications further. As a Computer Science student at UIUC, I believe my skills in {key_skill_1} and {key_skill_2} make me a strong candidate for this role.

I am particularly excited about {company} because of {specific_reason}. I am authorized for CPT work authorization during my internship.

Thank you for your time and consideration.

Best regards,
{your_name}
{your_email}
{your_phone}
""",
            'follow_up_application': """
Subject: Follow-up: {role} Application - {your_name}

Dear Hiring Manager,

I hope you're doing well. I wanted to follow up on my application for the {role} position at {company}, which I submitted on {submission_date}.

I remain very interested in this opportunity and would appreciate any updates you might have regarding the status of my application. I am particularly excited about the possibility of contributing to {company}'s team and bringing my skills in {key_skill} to your organization.

Please let me know if there's any additional information I can provide to support my application.

Thank you again for your time and consideration.

Best regards,
{your_name}
{your_email}
{your_phone}
""",
            'interview_confirmation': """
Subject: Interview Confirmation: {role} at {company} - {your_name}

Dear {interviewer_name},

Thank you for inviting me to interview for the {role} position at {company}. I am excited about this opportunity and confirm my availability for the interview on {interview_date} at {interview_time}.

I look forward to discussing my qualifications and learning more about the team and the role. Please let me know if there's anything specific I should prepare or bring to the interview.

Thank you again for this opportunity.

Best regards,
{your_name}
{your_email}
{your_phone}
"""
        }
        
        # Follow-up templates
        self.templates['follow_ups'] = {
            'post_interview': """
Subject: Thank You - {role} Interview - {your_name}

Dear {interviewer_name},

Thank you for taking the time to interview me for the {role} position at {company}. I truly enjoyed our conversation and learning more about {specific_topic_discussed}.

Our discussion about {interview_topic} further confirmed my interest in joining {company}. I am particularly excited about the opportunity to contribute to {specific_project_or_team} and believe my experience with {relevant_skill} would allow me to make meaningful contributions.

I remain very enthusiastic about this opportunity and would welcome any updates you might have regarding the next steps in the process.

Thank you again for your time and consideration.

Best regards,
{your_name}
{your_email}
{your_phone}
""",
            'networking_follow_up': """
Subject: Following Up - {context} - {your_name}

Dear {contact_name},

I hope you're doing well. I wanted to follow up on our conversation regarding {context}.

I've been {action_taken_since_contact} and wanted to share this update with you. I believe this could be relevant to our discussion about {topic_of_interest}.

I would appreciate any insights or advice you might have regarding {specific_question}. Your perspective would be invaluable as I {current_goal}.

Thank you for your time and guidance.

Best regards,
{your_name}
{your_email}
{your_phone}
"""
        }
        
        # Thank you templates
        self.templates['thank_you'] = {
            'post_offer': """
Subject: Thank You for Offer - {role} at {company} - {your_name}

Dear {hiring_manager_name},

Thank you so much for offering me the {role} position at {company}. I am truly honored and excited about this opportunity.

I have reviewed the offer details and am very enthusiastic about joining {company}. The opportunity to work on {specific_project_or_team} and contribute to {company_goal} aligns perfectly with my career goals.

I plan to review the offer details carefully and will get back to you by {response_deadline} with my decision. In the meantime, please let me know if there's any additional information you need from me.

Thank you again for this incredible opportunity.

Best regards,
{your_name}
{your_email}
{your_phone}
""",
            'post_rejection': """
Subject: Thank You - {role} Application - {your_name}

Dear Hiring Manager,

Thank you for taking the time to review my application for the {role} position at {company}. While I was disappointed to learn that I was not selected for this role, I truly appreciate the opportunity to apply and learn more about {company}.

I would be grateful if you could provide any feedback on my application or interview, as I am always looking to improve and grow as a professional.

I remain very interested in {company} and hope to have the opportunity to apply for future positions that may be a good fit for my skills and experience.

Thank you again for your time and consideration.

Best regards,
{your_name}
{your_email}
{your_phone}
"""
        }
        
        # Withdrawal templates
        self.templates['withdrawal'] = {
            'accepted_another_offer': """
Subject: Withdrawal of Application - {role} at {company} - {your_name}

Dear Hiring Manager,

I hope you're doing well. I am writing to respectfully withdraw my application for the {role} position at {company}.

I have recently accepted an offer with another company that aligns well with my current career goals. While I was very impressed with {company} and the team, I felt this was the best decision for my professional development at this time.

I want to thank you for the time and consideration you gave my application. I was genuinely excited about the possibility of joining {company} and hope our paths might cross again in the future.

I wish you and the team all the best in finding the right candidate for this position.

Best regards,
{your_name}
{your_email}
{your_phone}
""",
            'timing_mismatch': """
Subject: Withdrawal of Application - {role} at {company} - {your_name}

Dear Hiring Manager,

I hope you're doing well. I am writing to respectfully withdraw my application for the {role} position at {company}.

After careful consideration, I have decided to focus my search on opportunities that better align with my current timeline and career goals. While I was very interested in {company}, I believe this decision is best for both parties at this time.

I want to thank you for the time and consideration you gave my application. I was genuinely impressed with {company} and hope to have the opportunity to apply for future positions that may be a better fit.

I wish you and the team all the best.

Best regards,
{your_name}
{your_email}
{your_phone}
"""
        }
    
    def get_template(self, category: str, template_name: str) -> str:
        """Get a specific template"""
        if category in self.templates and template_name in self.templates[category]:
            return self.templates[category][template_name]
        else:
            logger.warning(f"Template not found: {category}/{template_name}")
            return ""
    
    def customize_template(self, template: str, variables: Dict[str, str]) -> str:
        """Customize template with provided variables"""
        customized = template
        for key, value in variables.items():
            customized = customized.replace(f"{{{key}}}", value)
        return customized
    
    def save_custom_template(self, category: str, template_name: str, content: str):
        """Save a custom template"""
        if category not in self.templates:
            self.templates[category] = {}
        
        self.templates[category][template_name] = content
        logger.info(f"Saved custom template: {category}/{template_name}")
    
    def list_templates(self, category: str = None) -> Dict[str, List[str]]:
        """List available templates"""
        if category:
            if category in self.templates:
                return {category: list(self.templates[category].keys())}
            else:
                return {}
        else:
            return {cat: list(templates.keys()) for cat, templates in self.templates.items()}
    
    def export_templates(self, filepath: str):
        """Export all templates to JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.templates, f, indent=2)
            logger.info(f"Exported templates to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting templates: {e}")
    
    def import_templates(self, filepath: str):
        """Import templates from JSON file"""
        try:
            with open(filepath, 'r') as f:
                imported_templates = json.load(f)
            
            for category, templates in imported_templates.items():
                if category not in self.templates:
                    self.templates[category] = {}
                self.templates[category].update(templates)
            
            logger.info(f"Imported templates from {filepath}")
        except Exception as e:
            logger.error(f"Error importing templates: {e}")

def main():
    """Example usage"""
    library = TemplateLibrary()
    
    # Get a template
    cover_letter = library.get_template('cover_letters', 'underclassman_program')
    
    # Customize it
    variables = {
        'role': 'Software Engineer Intern',
        'company': 'Google',
        'relevant_skill': 'machine learning',
        'tech_stack_1': 'Python',
        'tech_stack_2': 'TensorFlow',
        'company_specific_reason': 'your commitment to AI research',
        'specific_project_or_initiative': 'Google Brain',
        'your_name': 'John Doe',
        'your_email': 'john.doe@example.com',
        'your_phone': '(123) 456-7890'
    }
    
    customized = library.customize_template(cover_letter, variables)
    print("Customized Cover Letter:")
    print(customized)
    
    # List all templates
    all_templates = library.list_templates()
    print(f"\nAvailable templates: {all_templates}")

if __name__ == "__main__":
    main()