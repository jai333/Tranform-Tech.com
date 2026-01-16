#!/usr/bin/env python3
"""
Script to create 5 realistic job listings and 10 job seeker accounts in the database.
Run this script with: python manage.py shell < create_jobs.py
"""

import os
import django
import datetime
import random
from django.contrib.auth.hashers import make_password

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from tracking_app.models import Job, User
from django.utils import timezone

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

# Create job seeker accounts
def create_job_seekers(num_accounts=10):
    """Create multiple job seeker accounts"""
    print("\nCreating job seeker accounts...")
    
    # Sample data for generating realistic profiles
    first_names = ["Raj", "Priya", "Arjun", "Neha", "Vikram", "Ananya", "Sanjay", "Divya", "Amit", "Kavita",
                   "Rohit", "Meera", "Rahul", "Aisha", "Nikhil", "Shreya", "Karan", "Nandini", "Vishal", "Tanvi"]
    
    last_names = ["Sharma", "Patel", "Singh", "Verma", "Gupta", "Desai", "Kumar", "Shah", "Mehta", "Joshi",
                  "Khanna", "Agarwal", "Malhotra", "Kapoor", "Reddy", "Nair", "Banerjee", "Chatterjee", "Iyer", "Pillai"]
    
    skills_options = [
        "Python, JavaScript, React, Django, SQL",
        "Java, Spring Boot, Hibernate, PostgreSQL",
        "C++, Data Structures, Algorithms, System Design",
        "HTML, CSS, JavaScript, UI/UX Design",
        "AWS, Docker, Kubernetes, DevOps",
        "Machine Learning, TensorFlow, PyTorch, Data Analysis",
        "Node.js, Express, MongoDB, RESTful APIs",
        "Swift, iOS Development, Mobile UI Design",
        "Flutter, Dart, Cross-platform Development",
        "Project Management, Agile, Scrum, Leadership"
    ]
    
    created_count = 0
    password = make_password("job@123")  # Hash password once for all accounts
    
    for i in range(1, num_accounts + 1):
        username = f"job{i}"
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"Job seeker {username} already exists")
            continue
            
        # Create a random profile
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{username}@example.com"
        about_me = f"Passionate professional with experience in software development."
        skills = random.choice(skills_options)
        
        # Create the user
        User.objects.create(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role="jobseeker",
            about_me=about_me,
            skills=skills
        )
        
        created_count += 1
        print(f"Created job seeker: {username} ({first_name} {last_name})")
    
    return created_count

# Job listings data
job_listings = [
    {
        "title": "Senior Software Engineer - Python",
        "company": "Protingent India",
        "department": "Engineering",
        "description": (
            "We're looking for an experienced Senior Software Engineer with strong Python skills to join our "
            "growing engineering team. You'll be responsible for designing, building, and maintaining scalable "
            "web applications using Django and other modern technologies.\n\n"
            "As a senior member of the team, you'll mentor junior developers, participate in architectural "
            "decisions, and help define coding standards and best practices.\n\n"
            "This is a full-time position with competitive compensation and benefits."
        ),
        "requirements": (
            "- Bachelor's degree in Computer Science or related field\n"
            "- 5+ years of experience with Python\n"
            "- Strong knowledge of Django framework\n"
            "- Experience with RESTful APIs\n"
            "- Familiarity with AWS services\n"
            "- Experience working in a microservices architecture\n"
            "- Good understanding of database design and optimization\n"
            "- Excellent problem-solving skills and attention to detail"
        ),
        "benefits": (
            "- Flexible work hours\n"
            "- Health insurance with family coverage\n"
            "- Annual performance bonus\n"
            "- Professional development budget\n"
            "- Regular team outings and events\n"
            "- Modern office space with amenities"
        ),
        "location": "Bangalore, India",
        "salary": "₹18-25 LPA",
        "job_type": "full-time",
        "skills": "Python, Django, REST, AWS, Microservices, SQL",
        "experience": "5+ years",
        "status": "active",
        "deadline": timezone.now().date() + datetime.timedelta(days=30),
    },
    {
        "title": "Data Scientist",
        "company": "Protingent India",
        "department": "Data Science",
        "description": (
            "Join our data science team to build machine learning models and analyze large datasets "
            "that drive business decisions. You'll collaborate with stakeholders to understand requirements "
            "and deliver data-driven insights.\n\n"
            "You'll be responsible for developing and implementing data models, using machine learning "
            "techniques, and translating complex findings into actionable insights for the business.\n\n"
            "This role offers the flexibility of remote work with occasional visits to our offices for team meetings."
        ),
        "requirements": (
            "- MS or PhD in Data Science, Statistics, or related field\n"
            "- 3+ years of experience in data science\n"
            "- Proficiency in Python and data science libraries (NumPy, Pandas, Scikit-learn)\n"
            "- Experience with deep learning frameworks (TensorFlow, PyTorch)\n"
            "- Strong SQL skills and database knowledge\n"
            "- Experience with big data technologies (Hadoop, Spark) is a plus\n"
            "- Excellent communication skills to present findings to non-technical stakeholders"
        ),
        "benefits": (
            "- Remote work flexibility\n"
            "- Health insurance\n"
            "- Education allowance for courses and conferences\n"
            "- Stock options\n"
            "- Quarterly team retreats\n"
            "- Access to high-performance computing resources"
        ),
        "location": "Remote",
        "salary": "₹15-22 LPA",
        "job_type": "full-time",
        "skills": "Python, TensorFlow, PyTorch, SQL, Data Visualization, Statistics",
        "experience": "3+ years",
        "status": "active",
        "deadline": timezone.now().date() + datetime.timedelta(days=45),
    },
    {
        "title": "DevOps Engineer",
        "company": "Protingent India",
        "department": "Infrastructure",
        "description": (
            "We're seeking a talented DevOps Engineer to help automate our infrastructure and improve "
            "our CI/CD pipelines. You'll work closely with developers to deploy and scale applications "
            "in cloud environments.\n\n"
            "Your responsibilities will include managing container orchestration, implementing infrastructure "
            "as code, optimizing system performance, and ensuring high availability of our services.\n\n"
            "Join us to build and maintain the backbone of our growing technology platform."
        ),
        "requirements": (
            "- Strong experience with Docker and Kubernetes\n"
            "- Familiarity with AWS services (EC2, S3, RDS, Lambda)\n"
            "- Experience with CI/CD tools like Jenkins or GitLab CI\n"
            "- Scripting skills in Bash and Python\n"
            "- Knowledge of monitoring and logging systems (Prometheus, Grafana, ELK stack)\n"
            "- Understanding of security best practices in cloud environments\n"
            "- Experience with infrastructure as code (Terraform, CloudFormation)"
        ),
        "benefits": (
            "- Flexible work schedule\n"
            "- Health and dental insurance\n"
            "- Annual team retreats\n"
            "- Learning and development budget\n"
            "- Internet allowance for home office\n"
            "- Latest hardware and tools"
        ),
        "location": "Mumbai, India",
        "salary": "₹12-18 LPA",
        "job_type": "full-time",
        "skills": "Docker, Kubernetes, AWS, CI/CD, Linux, Terraform",
        "experience": "2-5 years",
        "status": "active",
        "deadline": timezone.now().date() + datetime.timedelta(days=60),
    },
    {
        "title": "UI/UX Designer",
        "company": "Protingent India",
        "department": "Design",
        "description": (
            "We're looking for a creative UI/UX Designer to craft beautiful and functional user experiences. "
            "You'll collaborate with product managers and developers to create wireframes, prototypes, and "
            "visual designs.\n\n"
            "Your designs will shape how users interact with our products, and you'll be involved in the entire "
            "design process from research to implementation.\n\n"
            "This is a contract position with the possibility of conversion to full-time."
        ),
        "requirements": (
            "- Portfolio demonstrating UI/UX design skills\n"
            "- Experience with design tools like Figma and Adobe XD\n"
            "- Knowledge of user research methodologies\n"
            "- Understanding of accessibility standards\n"
            "- Ability to create interactive prototypes\n"
            "- Experience working with design systems\n"
            "- Basic understanding of frontend development is a plus"
        ),
        "benefits": (
            "- Flexible work arrangements\n"
            "- Design conference allowance\n"
            "- Latest design tools and equipment\n"
            "- Collaborative and creative work environment\n"
            "- Opportunity to work on diverse projects"
        ),
        "location": "Pune, India",
        "salary": "₹8-15 LPA",
        "job_type": "contract",
        "skills": "Figma, Adobe XD, User Research, Wireframing, Prototyping",
        "experience": "3+ years",
        "status": "active",
        "deadline": timezone.now().date() + datetime.timedelta(days=30),
    },
    {
        "title": "Frontend Developer Intern",
        "company": "Protingent India",
        "department": "Engineering",
        "description": (
            "We're offering an exciting internship opportunity for aspiring frontend developers. "
            "You'll learn modern web development practices while building real-world projects under "
            "the guidance of experienced developers.\n\n"
            "This internship will provide hands-on experience with React and other frontend technologies, "
            "giving you valuable skills to kickstart your career in web development.\n\n"
            "Successful interns may be considered for full-time positions after the internship period."
        ),
        "requirements": (
            "- Basic knowledge of HTML, CSS, and JavaScript\n"
            "- Familiarity with React or willingness to learn\n"
            "- Understanding of responsive design principles\n"
            "- Ability to work in a collaborative environment\n"
            "- Strong desire to learn and grow as a developer\n"
            "- Some knowledge of Git version control\n"
            "- Currently pursuing or recently completed a degree in Computer Science or related field"
        ),
        "benefits": (
            "- Mentorship from senior developers\n"
            "- Certificate upon completion\n"
            "- Possibility of full-time employment\n"
            "- Flexible hours\n"
            "- Exposure to real-world projects and workflows\n"
            "- Networking opportunities"
        ),
        "location": "Remote",
        "salary": "₹25-35K per month",
        "job_type": "internship",
        "skills": "HTML, CSS, JavaScript, React",
        "experience": "0-1 years",
        "status": "active",
        "deadline": timezone.now().date() + datetime.timedelta(days=20),
    }
]

# Create job listings
created_count = 0
for job_data in job_listings:
    # Check if job with this title already exists to avoid duplicates
    if not Job.objects.filter(title=job_data["title"]).exists():
        job = Job(user=recruiter_user, **job_data)
        job.save()
        created_count += 1
        print(f"Created job: {job.title}")
    else:
        print(f"Job already exists: {job_data['title']}")

# Create job seeker accounts
jobseekers_created = create_job_seekers(10)

# Print summary
print("\n=== Summary ===")
print(f"Created {created_count} new job listings using recruiter: {recruiter_user.username}")
print(f"Created {jobseekers_created} job seeker accounts (username: job1-job10, password: job@123)")
print("================================") 