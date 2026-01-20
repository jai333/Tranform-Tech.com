"""
Resume Parser Service
Handles resume file parsing and data extraction
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import json

# Document parsing
from docx import Document
import PyPDF2
import pdfplumber

# NLP
import spacy
from nltk.tokenize import sent_tokenize
import nltk

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


class ResumeParser:
    """Main resume parser class"""
    
    def __init__(self):
        """Initialize parser with NLP model"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise Exception("Please install spaCy model: python -m spacy download en_core_web_sm")
        
        # Common skill keywords
        self.technical_skills = [
            'Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Ruby',
            'Django', 'Flask', 'FastAPI', 'React', 'Angular', 'Vue',
            'SQL', 'PostgreSQL', 'MongoDB', 'MySQL', 'Redis',
            'AWS', 'Google Cloud', 'Azure', 'Docker', 'Kubernetes',
            'Git', 'Linux', 'Windows', 'macOS', 'REST', 'GraphQL',
            'HTML', 'CSS', 'SASS', 'Bootstrap', 'Tailwind',
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch',
            'Data Science', 'Analytics', 'Tableau', 'Power BI'
        ]
        
        self.soft_skills = [
            'Leadership', 'Communication', 'Problem Solving', 'Teamwork',
            'Project Management', 'Time Management', 'Critical Thinking',
            'Creativity', 'Adaptability', 'Negotiation', 'Presentation',
            'Writing', 'Research', 'Decision Making', 'Mentoring'
        ]
    
    def parse_file(self, file_path: str) -> Dict:
        """
        Parse resume file and extract information
        
        Args:
            file_path: Path to resume file (PDF, DOCX, TXT)
        
        Returns:
            Dict containing extracted resume data
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            text = self._extract_from_pdf(file_path)
        elif file_extension == '.docx':
            text = self._extract_from_docx(file_path)
        elif file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        return self.parse_text(text)
    
    def parse_text(self, text: str) -> Dict:
        """
        Parse resume text and extract structured data
        
        Args:
            text: Raw resume text
        
        Returns:
            Structured resume data
        """
        # Process with spaCy
        doc = self.nlp(text)
        
        # Extract information
        result = {
            'raw_text': text,
            'contact_info': self._extract_contact_info(text),
            'personal_info': self._extract_personal_info(doc),
            'skills': self._extract_skills(text),
            'experience': self._extract_experience(text),
            'education': self._extract_education(text),
            'certifications': self._extract_certifications(text),
            'total_experience_years': self._calculate_experience_years(text),
        }
        
        return result
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        
        return text
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    
    def _extract_contact_info(self, text: str) -> Dict:
        """Extract email, phone, LinkedIn, etc."""
        contact_info = {}
        
        # Email regex
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['email'] = emails[0]
        
        # Phone regex
        phone_pattern = r'(\+?1?\s?)?(\([0-9]{3}\)|[0-9]{3})[\s.-]?[0-9]{3}[\s.-]?[0-9]{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info['phone'] = phones[0][2] if phones[0][2] else phones[0][0]
        
        # LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin = re.findall(linkedin_pattern, text)
        if linkedin:
            contact_info['linkedin'] = linkedin[0]
        
        return contact_info
    
    def _extract_personal_info(self, doc) -> Dict:
        """Extract name and location using NLP"""
        personal_info = {}
        
        # Extract entities
        for ent in doc.ents:
            if ent.label_ == 'PERSON' and not personal_info.get('name'):
                personal_info['name'] = ent.text
            elif ent.label_ == 'GPE':
                if not personal_info.get('location'):
                    personal_info['location'] = ent.text
        
        return personal_info
    
    def _extract_skills(self, text: str) -> List[Dict]:
        """Extract technical and soft skills"""
        skills = []
        text_lower = text.lower()
        
        # Find technical skills
        for skill in self.technical_skills:
            if skill.lower() in text_lower:
                skills.append({
                    'skill': skill,
                    'category': 'technical',
                    'proficiency': self._estimate_proficiency(text, skill)
                })
        
        # Find soft skills
        for skill in self.soft_skills:
            if skill.lower() in text_lower:
                skills.append({
                    'skill': skill,
                    'category': 'soft',
                    'proficiency': 'intermediate'
                })
        
        return skills
    
    def _extract_experience(self, text: str) -> List[Dict]:
        """Extract work experience"""
        experience = []
        
        # Pattern for job entries (simplified)
        job_pattern = r'(?:experience|career|employment).*?(?=education|certification|$)'
        sections = re.findall(job_pattern, text, re.IGNORECASE | re.DOTALL)
        
        for section in sections:
            # Extract job entries
            jobs = re.split(r'[\n]{2,}', section)
            for job in jobs:
                if len(job.strip()) > 20:
                    experience.append({
                        'raw_text': job,
                        'parsed': False  # Mark for manual review if needed
                    })
        
        return experience
    
    def _extract_education(self, text: str) -> List[Dict]:
        """Extract education information"""
        education = []
        
        degrees = ['Bachelor', 'Master', 'PhD', 'Associate', 'Diploma', 'B.A.', 'M.A.', 'B.S.', 'M.S.']
        
        for degree in degrees:
            if degree in text:
                education.append({
                    'degree_type': degree,
                    'mentioned': True
                })
        
        return education
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications and credentials"""
        certifications = []
        
        cert_keywords = [
            'AWS Certified', 'Google Cloud', 'Azure Certified',
            'PMP', 'Scrum Master', 'TOGAF', 'CISSP',
            'CPA', 'CFA', 'CFP'
        ]
        
        for cert in cert_keywords:
            if cert.lower() in text.lower():
                certifications.append(cert)
        
        return certifications
    
    def _calculate_experience_years(self, text: str) -> float:
        """Estimate total years of experience"""
        # Look for year patterns
        years = re.findall(r'(20\d{2}|19\d{2})', text)
        
        if len(years) >= 2:
            try:
                years_int = sorted([int(y) for y in years])
                return (years_int[-1] - years_int[0]) / 10  # Rough estimate
            except:
                return 0
        
        return 0
    
    def _estimate_proficiency(self, text: str, skill: str) -> str:
        """Estimate skill proficiency level"""
        text_lower = text.lower()
        skill_lower = skill.lower()
        
        # Look for proficiency indicators around skill
        proficiency_keywords = {
            'expert': ['expert', 'master', 'advanced', 'senior'],
            'intermediate': ['proficient', 'experienced', 'skilled'],
            'beginner': ['familiar', 'basic', 'introductory']
        }
        
        # Find context around skill
        pattern = f'.{{0,30}}{skill_lower}.{{0,30}}'
        matches = re.findall(pattern, text_lower)
        
        for match in matches:
            for level, keywords in proficiency_keywords.items():
                if any(kw in match for kw in keywords):
                    return level
        
        # Default to intermediate if found
        return 'intermediate'


# Example usage
if __name__ == '__main__':
    parser = ResumeParser()
    
    # Parse a resume file
    result = parser.parse_file('sample_resume.pdf')
    
    # Print extracted data
    print(json.dumps(result, indent=2))
