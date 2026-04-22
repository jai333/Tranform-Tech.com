#!/usr/bin/env python3
"""
Script to parse job listings from sample_data.txt and create batch jobs in the database.

This script can be run in two ways:
1. Through Django shell: python manage.py shell < jobs_batch.py
   Note: Output may be suppressed when run this way.

2. Directly: python jobs_batch.py
   This will show all output and debugging information.
"""

import os
import django
import datetime
import json
import re
from bs4 import BeautifulSoup
from django.contrib.auth.hashers import make_password
from django.utils import timezone

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from tracking_app.models import Job, User

# Get or create recruiter user
RECRUITER_USERNAME = 'recruiter1'
RECRUITER_PASSWORD = 'bTiN!*Yk1GQij14y'
RECRUITER_EMAIL = 'recruiter1@example.com'

try:
    recruiter_user = User.objects.get(username=RECRUITER_USERNAME)
    print(f"Found existing recruiter user: {RECRUITER_USERNAME}")
except User.DoesNotExist:
    print(f"Creating new recruiter user: {RECRUITER_USERNAME}")
    recruiter_user = User.objects.create(
        username=RECRUITER_USERNAME,
        email=RECRUITER_EMAIL,
        password=make_password(RECRUITER_PASSWORD),  # Hash the password
        first_name='Recruiter',
        last_name='One',
        role='recruiter',
        is_staff=True  # Give staff access but not superuser
    )

def clean_html(html_content):
    """Remove HTML tags and clean the content"""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()
    # Replace multiple newlines with a single one
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def extract_sections(description):
    """Extract different sections from job description HTML"""
    if not description:
        return {
            "description": "",
            "responsibilities": "",
            "qualifications": "",
            "benefits": ""
        }
    
    soup = BeautifulSoup(description, 'html.parser')
    
    # Initialize sections
    sections = {
        "description": "",
        "responsibilities": "",
        "qualifications": "",
        "benefits": ""
    }
    
    # Extract job description
    desc_section = soup.find("strong", text=re.compile(r"(Job|Position)\s*Description", re.I))
    if desc_section:
        desc_text = []
        for sibling in desc_section.find_next_siblings():
            if sibling.name == "strong" and any(re.match(r"(Job|Position)?\s*(Responsibilities|Qualifications|Benefits|Details)", sibling.text, re.I) for _ in [None]):
                break
            desc_text.append(sibling.get_text(strip=True))
        sections["description"] = "\n".join(desc_text)
    
    # Extract responsibilities
    resp_section = soup.find("strong", text=re.compile(r"Job\s*Responsibilities", re.I))
    if resp_section:
        resp_list = []
        resp_ul = resp_section.find_next("ul")
        if resp_ul:
            for li in resp_ul.find_all("li"):
                resp_list.append("- " + li.get_text(strip=True))
        sections["responsibilities"] = "\n".join(resp_list)
    
    # Extract qualifications
    qual_section = soup.find("strong", text=re.compile(r"Job\s*Qualifications", re.I))
    if qual_section:
        qual_list = []
        qual_ul = qual_section.find_next("ul")
        if qual_ul:
            for li in qual_ul.find_all("li"):
                qual_list.append("- " + li.get_text(strip=True))
        sections["qualifications"] = "\n".join(qual_list)
    
    # Extract benefits
    ben_section = soup.find("strong", text=re.compile(r"Benefits\s*Package", re.I))
    if ben_section:
        ben_text = ben_section.next_sibling
        if ben_text:
            sections["benefits"] = ben_text.strip()
    
    return sections

def extract_job_details(job_data):
    """Extract key job details from the raw data"""
    # Extract basic fields
    title = job_data.get("POST_TITLE", "")
    
    # Extract and clean description
    description_html = job_data.get("POST_DESCRIPTION", "")
    sections = extract_sections(description_html)
    
    # Get location information
    city = job_data.get("POST_CITY", "")
    state = job_data.get("POST_STATE", "")
    country = job_data.get("POST_COUNTRY", "")
    location = job_data.get("POST_LOCATION", "")
    
    if not location and (city or state):
        location = f"{city}, {state}" if city and state else (city or state)
    
    # Get salary information
    salary = ""
    if job_data.get("POST_SALARY"):
        salary = f"${job_data.get('POST_SALARY')}/hr"
    elif job_data.get("POST_PAYRATE"):
        salary = f"${job_data.get('POST_PAYRATE')}/hr"
    else:
        # Try to extract salary from description
        desc_soup = BeautifulSoup(description_html, 'html.parser')
        pay_section = desc_soup.find(text=re.compile(r"Pay Range", re.I))
        if pay_section:
            pay_text = pay_section.parent.get_text()
            salary_match = re.search(r'\$[\d\.]+-\$?[\d\.]+', pay_text)
            if salary_match:
                salary = salary_match.group(0)
    
    # Get job type
    job_type = job_data.get("POST_EMPLOYMENT_TYPE", "").lower()
    if not job_type:
        # Try to find it in the description
        if re.search(r'contract', description_html, re.I):
            job_type = "contract"
        elif re.search(r'full[ -]time', description_html, re.I):
            job_type = "full-time"
        elif re.search(r'part[ -]time', description_html, re.I):
            job_type = "part-time"
        elif re.search(r'internship', description_html, re.I):
            job_type = "internship"
        else:
            job_type = "full-time"  # Default
    
    # Get department/industry
    department = ""
    if job_data.get("POST_FIELD2"):
        # Format like "MDEV - Medical Device" -> "Medical Device"
        dept_match = re.search(r'[A-Z]+ - (.+)', job_data.get("POST_FIELD2", ""))
        if dept_match:
            department = dept_match.group(1)
        else:
            department = job_data.get("POST_FIELD2")
    
    # Get experience requirement
    experience = job_data.get("POST_EXPERIENCE_REQUIRED", "")
    if not experience:
        # Try to extract from qualifications
        exp_match = re.search(r'(\d+[\-\+]?\s*\d*\s*years?)', sections["qualifications"], re.I)
        if exp_match:
            experience = exp_match.group(0)
    
    # Get deadline
    deadline = None
    if job_data.get("POST_EXPIRATION_DATE"):
        try:
            deadline = datetime.datetime.strptime(job_data.get("POST_EXPIRATION_DATE"), "%Y-%m-%d").date()
        except ValueError:
            deadline = timezone.now().date() + datetime.timedelta(days=30)
    else:
        deadline = timezone.now().date() + datetime.timedelta(days=30)
    
    # Extract skills from qualifications
    skills = []
    if sections["qualifications"]:
        # Look for technical skills
        tech_skills = re.findall(r'(Python|Java|JavaScript|C\+\+|C#|SQL|React|Angular|AWS|Docker|AutoCAD|Excel|SolidWorks|MATLAB)\b', 
                                sections["qualifications"], re.I)
        skills.extend(tech_skills)
    
    return {
        "title": title,
        "company": "Transform.io",  # Default from job data
        "department": department,
        "description": sections["description"] + "\n\n" + sections["responsibilities"],
        "requirements": sections["qualifications"],
        "benefits": sections["benefits"],
        "location": location,
        "salary": salary,
        "job_type": job_type,
        "skills": ", ".join(skills) if skills else "",
        "experience": experience,
        "status": "active",
        "deadline": deadline,
    }

def parse_sample_data(file_path):
    """
    Parse the sample_data.txt file which contains job listings in a custom format
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Successfully opened {file_path}. Content length: {len(content)}")
            
            # Strip trailing characters if present
            if content.endswith('%\n\n'):
                content = content[:-3]
                
            # Check if content starts directly with "ResultSet":
            # If so, prepend a "{" to make it valid JSON
            if content.strip().startswith('"ResultSet":'):
                content = '{' + content
                
            # Ensure content ends with closing brace
            if not content.strip().endswith('}'):
                content = content + '}'
                
            try:
                # Attempt to parse as JSON
                data = json.loads(content)
                print(f"Successfully parsed JSON. Keys: {list(data.keys())}")
                
                # The structure seems to be ResultSet -> list -> [job listings]
                if 'ResultSet' in data:
                    if isinstance(data['ResultSet'], dict) and 'list' in data['ResultSet']:
                        job_listings = data['ResultSet']['list']
                        print(f"Found {len(job_listings)} job listings in ResultSet.list")
                        return job_listings
                    elif isinstance(data['ResultSet'], list):
                        print(f"Found {len(data['ResultSet'])} job listings directly in ResultSet array")
                        return data['ResultSet']
                
                # If no job listings found in standard locations, try to find any array of job objects
                for key, value in data.items():
                    if isinstance(value, dict) and 'list' in value and isinstance(value['list'], list):
                        jobs = value['list']
                        if jobs and isinstance(jobs[0], dict) and 'POST_TITLE' in jobs[0]:
                            print(f"Found {len(jobs)} job listings in {key}.list")
                            return jobs
                    elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                        if 'POST_TITLE' in value[0]:
                            print(f"Found {len(value)} job listings in {key}")
                            return value
                
                print("Could not find job listings in the parsed JSON structure.")
                print(f"Available keys in data: {list(data.keys())}")
                if 'ResultSet' in data and isinstance(data['ResultSet'], dict):
                    print(f"Keys in ResultSet: {list(data['ResultSet'].keys())}")
                return []
                    
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed: {str(e)}")
                print(f"First 100 chars of content: {content[:100]}")
                
                # Try regex approach to extract job listings
                print("Attempting to extract job listings using regex...")
                pattern = r'\{(?:"POST_.*?|"SEO_.*?)\}'
                matches = re.findall(pattern, content, re.DOTALL)
                
                if matches:
                    print(f"Found {len(matches)} job listings using regex")
                    job_listings = []
                    for match in matches:
                        try:
                            job_listing = json.loads(match)
                            if 'POST_TITLE' in job_listing:
                                job_listings.append(job_listing)
                        except:
                            pass
                    
                    if job_listings:
                        print(f"Successfully parsed {len(job_listings)} job listings")
                        return job_listings
                
                return []
                
    except Exception as e:
        import traceback
        print(f"Error reading the sample data file: {str(e)}")
        print(traceback.format_exc())
        return []

def create_jobs_from_data(job_listings_data):
    """Create job objects from the parsed data"""
    created_count = 0
    
    for job_data in job_listings_data:
        processed_job = extract_job_details(job_data)
        
        # Check if job with this title already exists to avoid duplicates
        if not Job.objects.filter(title=processed_job["title"]).exists():
            job = Job(user=recruiter_user, **processed_job)
            job.save()
            created_count += 1
            print(f"Created job: {job.title}")
        else:
            print(f"Job already exists: {processed_job['title']}")
    
    return created_count

if __name__ == "__main__":
    # Path to sample data file
    sample_data_path = "sample_data.txt"
    
    # Print current directory for debugging
    import os
    print(f"Current working directory: {os.getcwd()}")
    print(f"Checking if file exists: {os.path.exists(sample_data_path)}")
    
    # Get file size
    if os.path.exists(sample_data_path):
        file_size = os.path.getsize(sample_data_path)
        print(f"File size: {file_size} bytes")
    else:
        print("ERROR: sample_data.txt file not found!")
        exit(1)
    
    # Analyze the first line of the file
    try:
        with open(sample_data_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            print(f"First line of file: {first_line[:100]}...")
    except Exception as e:
        print(f"Error reading first line: {str(e)}")
    
    # Parse the sample data file
    print(f"Parsing job listings from {sample_data_path}...")
    job_listings_data = parse_sample_data(sample_data_path)
    
    if job_listings_data:
        print(f"Found {len(job_listings_data)} job listings in the data file.")
        
        # Print sample of first listing for debugging
        if len(job_listings_data) > 0:
            first_job = job_listings_data[0]
            print("\nSample of first job listing:")
            print(f"Title: {first_job.get('POST_TITLE', 'N/A')}")
            print(f"Location: {first_job.get('POST_LOCATION', 'N/A')}")
            print(f"Salary: {first_job.get('POST_SALARY', 'N/A') or first_job.get('POST_PAYRATE', 'N/A')}")
            print(f"Keys in job data: {list(first_job.keys())}")
        
        # Try direct data extraction from the first job
        try:
            print("Testing direct job data extraction...")
            if 'POST_TITLE' in first_job:
                print(f"Job title extraction worked: {first_job['POST_TITLE']}")
            else:
                print(f"Job title not found in keys: {list(first_job.keys())}")
        except Exception as e:
            print(f"Error in direct data extraction: {str(e)}")
        
        # Create jobs from the data
        print("Creating jobs from data...")
        created_count = create_jobs_from_data(job_listings_data)
        
        # Print summary
        print("\n=== Summary ===")
        print(f"Created {created_count} new job listings using recruiter: {recruiter_user.username}")
        print("================================")
    else:
        print("No job listings found in the data file or couldn't parse the file.") 