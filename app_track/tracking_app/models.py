from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Q

# Create your models here.

class Candidate(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    resume = models.TextField(blank=True, null=True) # Storing resume content or path
    application_date = models.DateField(auto_now_add=True)
    # Add user field to track who created this candidate
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='candidates', null=True)

    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='%(class)ss')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ('full-time', 'Full-time'),
        ('part-time', 'Part-time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('internship', 'Internship'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('filled', 'Filled'),
        ('expired', 'Expired'),
        ('draft', 'Draft'),
    ]
    
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, default='Transform-Tech')
    department = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField()
    requirements = models.TextField(blank=True, null=True, help_text="List job requirements and qualifications")
    benefits = models.TextField(blank=True, null=True, help_text="List benefits and perks offered")
    location = models.CharField(max_length=255, blank=True, null=True)
    salary = models.CharField(max_length=100, blank=True, null=True, help_text="Salary range or compensation details")
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='full-time')
    skills = models.CharField(max_length=500, blank=True, null=True, help_text="Comma-separated list of required skills")
    experience = models.CharField(max_length=100, blank=True, null=True, help_text="Required experience level")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    posting_date = models.DateField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True, help_text="Application deadline")
    # Add user field to track who created this job
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='jobs', null=True)

    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='%(class)ss')

    def __str__(self):
        return self.title
        
    def get_skills(self):
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.split(',')]
        
    def get_status_color(self):
        status_colors = {
            'active': 'success',
            'filled': 'info',
            'expired': 'danger',
            'draft': 'secondary',
        }
        return status_colors.get(self.status, 'secondary')

class Application(models.Model):
    STATUS_APPLIED = 'applied'
    STATUS_SCREENING = 'screening'
    STATUS_INTERVIEW = 'interview'
    STATUS_OFFER = 'offer'
    STATUS_HIRED = 'hired'
    STATUS_REJECTED = 'rejected'
    STATUS_WITHDRAWN = 'withdrawn'
    
    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_SCREENING, 'Screening'),
        (STATUS_INTERVIEW, 'Interview'),
        (STATUS_OFFER, 'Offer'),
        (STATUS_HIRED, 'Hired'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]
    
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applied_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_APPLIED)
    notes = models.TextField(blank=True, null=True)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='applications', null=True)
    tenant = models.ForeignKey('Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    
    def __str__(self):
        return f"{self.candidate} application for {self.job}"
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES)[self.status]
    
    def get_status_color(self):
        status_colors = {
            self.STATUS_APPLIED: 'primary',
            self.STATUS_SCREENING: 'info',
            self.STATUS_INTERVIEW: 'warning',
            self.STATUS_OFFER: 'success',
            self.STATUS_HIRED: 'success',
            self.STATUS_REJECTED: 'danger',
            self.STATUS_WITHDRAWN: 'secondary',
        }
        return status_colors.get(self.status, 'secondary')

class Interview(models.Model):
    STATUS_SCHEDULED = 'scheduled'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_NO_SHOW = 'no_show'
    
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_NO_SHOW, 'No Show'),
    ]
    
    TYPE_PHONE = 'phone'
    TYPE_VIDEO = 'video'
    TYPE_ONSITE = 'onsite'
    TYPE_TECHNICAL = 'technical'
    
    TYPE_CHOICES = [
        (TYPE_PHONE, 'Phone Screen'),
        (TYPE_VIDEO, 'Video'),
        (TYPE_ONSITE, 'On-site'),
        (TYPE_TECHNICAL, 'Technical'),
    ]
    
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='interviews')
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews', null=True)
    date_time = models.DateTimeField()
    interviewer = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_PHONE)
    feedback = models.TextField(blank=True, null=True)
    meeting_url = models.URLField(blank=True, null=True, help_text="URL for video conference meeting")
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='interviews', null=True)
    tenant = models.ForeignKey('Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='interviews')

    def __str__(self):
        return f"Interview for {self.candidate} for {self.job}"
    
    def get_status_color(self):
        status_colors = {
            self.STATUS_SCHEDULED: 'primary',
            self.STATUS_COMPLETED: 'success',
            self.STATUS_CANCELLED: 'danger',
            self.STATUS_NO_SHOW: 'warning',
        }
        return status_colors.get(self.status, 'secondary')

# Using Django's built-in User model features for simplicity and security
# Although the plan specifies a custom Users table, using AbstractUser 
# allows leveraging Django's auth system while adding custom fields if needed.

class InterviewScorecard(models.Model):
    RECOMMENDATION_CHOICES = [
        ('hire', 'Strong Hire'),
        ('maybe', 'Maybe'),
        ('reject', 'No Hire'),
    ]
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='scorecard')
    interviewer = models.ForeignKey('User', on_delete=models.CASCADE, related_name='scorecards')
    technical_score = models.IntegerField(default=3)
    communication_score = models.IntegerField(default=3)
    culture_fit_score = models.IntegerField(default=3)
    problem_solving_score = models.IntegerField(default=3)
    overall_rating = models.IntegerField(default=3)
    strengths = models.TextField(blank=True, null=True)
    weaknesses = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES, default='maybe')

    def __str__(self):
        return f"Scorecard for {self.interview}"

class Tenant(models.Model):
    """Represents a company or organization using the platform (Multi-Tenancy)."""
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('starter', 'Starter — $49/mo'),
        ('growth', 'Growth — $149/mo'),
        ('enterprise', 'Enterprise — $399/mo'),
    ]

    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Phase 2 — Billing
    subscription_plan = models.CharField(max_length=32, choices=PLAN_CHOICES, default='enterprise')
    stripe_customer_id = models.CharField(max_length=128, blank=True, null=True)

    # Phase 3 — Advanced Tenant Mail Integration
    mail_registered_email = models.EmailField(blank=True, null=True, help_text="Registered corporate email address for sending and receiving")
    mail_sender_name = models.CharField(max_length=150, blank=True, null=True, help_text="Sender display name (e.g., Nexus AI Sales)")
    mail_reply_to = models.EmailField(blank=True, null=True, help_text="Dedicated inbound inbox for automated AI reply parsing")
    mail_smtp_host = models.CharField(max_length=150, default='smtp.gmail.com', blank=True, null=True)
    mail_smtp_port = models.IntegerField(default=587, blank=True, null=True)
    mail_smtp_username = models.CharField(max_length=150, blank=True, null=True)
    mail_smtp_password = models.CharField(max_length=255, blank=True, null=True)
    mail_use_tls = models.BooleanField(default=True)
    mail_auto_sync = models.BooleanField(default=True, help_text="Automatically parse and sync two-way email communications")
    mail_integration_status = models.CharField(
        max_length=32,
        choices=[('unconfigured', 'Unconfigured'), ('connected', 'Connected & Active'), ('error', 'Connection Warning')],
        default='unconfigured'
    )

    def __str__(self):
        return self.name

    @property
    def is_paid(self):
        return self.subscription_plan != 'free'

# For this prototype, we'll primarily use the fields from AbstractUser 
# that match the plan's User table.
class User(AbstractUser):
    # Role choices
    ROLE_JOBSEEKER = 'jobseeker'
    ROLE_RECRUITER = 'recruiter'
    ROLE_SALES = 'sales'
    ROLE_IT = 'it'
    ROLE_ADMIN = 'admin'
    
    ROLE_CHOICES = [
        (ROLE_JOBSEEKER, 'Job Seeker'),
        (ROLE_RECRUITER, 'Recruiter / HR'),
        (ROLE_SALES, 'Sales Professional'),
        (ROLE_IT, 'IT Helpdesk Agent'),
        (ROLE_ADMIN, 'Administrator'),
    ]
    
    # Add role field to User model
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_JOBSEEKER,
        help_text='Designates the role and permissions of this user.'
    )
    
    # Dashboard Permissions (RBAC)
    can_view_ats = models.BooleanField(default=True)
    can_view_sales = models.BooleanField(default=True)
    can_view_it = models.BooleanField(default=True)
    can_view_executive = models.BooleanField(default=False)
    
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    
    # Add profile image field
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    
    # Add about me and skills
    about_me = models.TextField(blank=True, null=True, help_text='Tell us about yourself')
    skills = models.TextField(blank=True, null=True, help_text='List your skills, separated by commas')
    
    # Add professional headline
    headline = models.CharField(max_length=100, blank=True, null=True, help_text='Your professional headline')
    
    # Add phone number
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # The AbstractUser model already includes username, password, first_name, last_name, email, and is_staff
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text=
            'The groups this user belongs to. A user will get all permissions ' +
            'granted to each of their groups.',
        related_name="tracking_app_users",
        related_query_name="tracking_app_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="tracking_app_user_permissions",
        related_query_name="tracking_app_user_permission",
    )
    
    # Helper property methods for role checks
    @property
    def is_jobseeker(self):
        return self.role == self.ROLE_JOBSEEKER
    
    @property
    def is_recruiter(self):
        return self.role == self.ROLE_RECRUITER
    
    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_it_agent(self):
        # Determine if the user is an IT agent based on their role or staff status
        return self.is_staff or self.can_view_it or self.role in [self.ROLE_ADMIN, self.ROLE_IT, 'it_admin']

    @property
    def is_it_admin(self):
        # Determine if the user is an IT admin
        return self.is_superuser or self.can_view_it or self.role in [self.ROLE_ADMIN, 'it_admin']

    @property
    def is_it_enduser(self):
        # Determine if the user is a standard end-user for IT Helpdesk purposes
        return not self.is_it_agent

    def get_initials(self):
        return ''.join(word[0] for word in self.first_name.split() if word[0].isupper()) + ''.join(word[0] for word in self.last_name.split() if word[0].isupper())

class Friendship(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    sender = models.ForeignKey(User, related_name='sent_friendships', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_friendships', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('sender', 'receiver')
        verbose_name = 'Friendship'
        verbose_name_plural = 'Friendships'
    
    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"
    
    @classmethod
    def get_friendship(cls, user1, user2):
        """Get friendship between two users regardless of who is the sender/receiver"""
        try:
            return cls.objects.get(
                (Q(sender=user1) & Q(receiver=user2)) | 
                (Q(sender=user2) & Q(receiver=user1))
            )
        except cls.DoesNotExist:
            return None

class Message(models.Model):
    friendship = models.ForeignKey(Friendship, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class Notification(models.Model):
    TYPE_FRIEND_REQUEST = 'friend_request'
    TYPE_MESSAGE = 'message'
    TYPE_SYSTEM = 'system'
    TYPE_JOB_APPLICATION = 'job_application'
    
    TYPE_CHOICES = [
        (TYPE_FRIEND_REQUEST, 'Friend Request'),
        (TYPE_MESSAGE, 'New Message'),
        (TYPE_SYSTEM, 'System Notification'),
        (TYPE_JOB_APPLICATION, 'Job Application'),
    ]
    
    recipient = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    content = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.content[:30]}"

class JobSeekerApplication(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_REVIEWED = 'reviewed'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_WITHDRAWN = 'withdrawn'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_REVIEWED, 'Reviewed'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='jobseeker_applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications')
    cover_letter = models.TextField(blank=True, null=True)
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    applied_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('job', 'applicant')
        verbose_name = 'Job Application'
        verbose_name_plural = 'Job Applications'
    
    def __str__(self):
        return f"{self.applicant.username}'s application for {self.job.title}"
    
    def get_status_color(self):
        status_colors = {
            self.STATUS_PENDING: 'warning',
            self.STATUS_REVIEWED: 'info',
            self.STATUS_ACCEPTED: 'success',
            self.STATUS_REJECTED: 'danger',
            self.STATUS_WITHDRAWN: 'secondary',
        }
        return status_colors.get(self.status, 'secondary')

class Note(models.Model):
    candidate = models.ForeignKey(Candidate, related_name='notes', on_delete=models.CASCADE)
    content = models.TextField()
    created_by = models.ForeignKey(User, related_name='created_notes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note for {self.candidate} by {self.created_by}"


# AI/ML Related Models

class ResumeData(models.Model):
    """Store parsed resume data and extracted information"""
    candidate = models.OneToOneField(Candidate, on_delete=models.CASCADE, related_name='resume_data')
    resume_file = models.FileField(upload_to='resumes/', null=True, blank=True)
    
    # Extracted contact information
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    
    # Extracted professional information
    skills = models.JSONField(default=list, help_text="List of extracted skills with proficiency levels")
    experience_years = models.FloatField(null=True, blank=True, help_text="Total years of experience")
    education = models.JSONField(default=list, help_text="List of education details")
    certifications = models.JSONField(default=list, help_text="List of certifications")
    
    # Metadata
    raw_text = models.TextField(blank=True, null=True, help_text="Raw extracted text from resume")
    parse_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('success', 'Success'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    parse_error = models.TextField(blank=True, null=True)
    
    parsed_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Resume data for {self.candidate.full_name}"


class JobMatch(models.Model):
    """Store job-to-candidate matching scores and analysis"""
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='job_matches')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='candidate_matches')
    
    # Match scores (0-100)
    overall_score = models.IntegerField(help_text="Overall match score 0-100")
    skill_match_score = models.IntegerField(help_text="Skill match percentage")
    experience_match_score = models.IntegerField(help_text="Experience match percentage")
    education_match_score = models.IntegerField(help_text="Education match percentage")
    culture_fit_score = models.IntegerField(help_text="Culture fit percentage")
    availability_score = models.IntegerField(help_text="Availability match percentage")
    
    # Analysis data
    matching_skills = models.JSONField(default=list, help_text="Skills that match job requirements")
    missing_skills = models.JSONField(default=list, help_text="Required skills candidate doesn't have")
    experience_gap = models.TextField(blank=True, null=True, help_text="Experience gaps analysis")
    recommendations = models.JSONField(default=list, help_text="Recommendations for improvement")
    
    is_auto_matched = models.BooleanField(default=False, help_text="Auto-matched by AI algorithm")
    calculated_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('candidate', 'job')
        ordering = ['-overall_score']
    
    def __str__(self):
        return f"{self.candidate.full_name} -> {self.job.title} ({self.overall_score}%)"


class CandidateAISummary(models.Model):
    """AI-generated summaries and insights about candidates"""
    candidate = models.OneToOneField(Candidate, on_delete=models.CASCADE, related_name='ai_summary')
    
    # AI Generated summaries
    professional_summary = models.TextField(help_text="AI-generated professional summary")
    key_strengths = models.JSONField(default=list, help_text="Top 5 key strengths")
    development_areas = models.JSONField(default=list, help_text="Areas for development")
    ideal_roles = models.JSONField(default=list, help_text="Recommended job roles")
    
    # Scores and ratings
    overall_profile_score = models.IntegerField(help_text="Overall candidate quality score 0-100")
    communication_score = models.IntegerField(help_text="Communication skills score")
    technical_score = models.IntegerField(help_text="Technical skills score")
    leadership_score = models.IntegerField(help_text="Leadership potential score")
    
    # Summary metadata
    summary_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    generated_by = models.CharField(max_length=50, default='ai_engine')
    
    def __str__(self):
        return f"AI Summary for {self.candidate.full_name}"


class AdvancedSearch(models.Model):
    """Store saved advanced search filters and queries"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    
    name = models.CharField(max_length=255, help_text="Name of the saved search")
    description = models.TextField(blank=True, null=True)
    
    # Search filters
    skills_filter = models.JSONField(default=list, help_text="Required skills")
    experience_min = models.FloatField(null=True, blank=True)
    experience_max = models.FloatField(null=True, blank=True)
    location_filter = models.JSONField(default=list, help_text="Location preferences")
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    job_type_filter = models.JSONField(default=list, help_text="Job types")
    education_filter = models.JSONField(default=list, help_text="Education requirements")
    
    # Query metadata
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    last_used_date = models.DateTimeField(null=True, blank=True)
    result_count = models.IntegerField(default=0, help_text="Number of results from last search")
    
    class Meta:
        ordering = ['-updated_date']
    
    def __str__(self):
        return f"{self.user.username}'s search: {self.name}"


class ThirdPartyIntegration(models.Model):
    """Configuration for third-party integrations (Bullhorn, LinkedIn, etc.)"""
    PROVIDER_CHOICES = [
        ('bullhorn', 'Bullhorn'),
        ('linkedin', 'LinkedIn'),
        ('greenhouse', 'Greenhouse'),
        ('workday', 'Workday'),
        ('generic_api', 'Generic API'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='integrations')
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    
    # Credentials and configuration
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    oauth_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    api_endpoint = models.URLField(blank=True, null=True, help_text="Custom API endpoint for generic APIs")
    
    # Field mappings for data sync
    field_mappings = models.JSONField(default=dict, help_text="Mapping of internal fields to provider fields")
    
    # Sync configuration
    is_active = models.BooleanField(default=True)
    auto_sync_enabled = models.BooleanField(default=False)
    last_sync_date = models.DateTimeField(null=True, blank=True)
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s {self.get_provider_display()} integration"


class SyncLog(models.Model):
    """Log all sync operations between systems"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partially Synced'),
    ]
    
    integration = models.ForeignKey(ThirdPartyIntegration, on_delete=models.CASCADE, related_name='sync_logs')
    sync_type = models.CharField(max_length=50, help_text="e.g., 'sync_candidates', 'sync_jobs'")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Sync details
    records_processed = models.IntegerField(default=0)
    records_successful = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    # Metadata
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.integration} - {self.sync_type} ({self.status})"


class FieldMappingConfig(models.Model):
    """Configuration for field mappings between systems"""
    integration = models.ForeignKey(ThirdPartyIntegration, on_delete=models.CASCADE, related_name='field_configs')
    
    internal_field = models.CharField(max_length=100, help_text="Field name in our system")
    external_field = models.CharField(max_length=100, help_text="Field name in external system")
    field_type = models.CharField(
        max_length=50,
        choices=[
            ('string', 'String'),
            ('integer', 'Integer'),
            ('date', 'Date'),
            ('boolean', 'Boolean'),
            ('json', 'JSON'),
        ],
        default='string'
    )
    
    is_required = models.BooleanField(default=False)
    is_bidirectional = models.BooleanField(default=False, help_text="Sync in both directions")
    transform_function = models.CharField(max_length=255, blank=True, null=True, help_text="Optional data transformation")
    
    class Meta:
        unique_together = ('integration', 'internal_field', 'external_field')
    
    def __str__(self):
        return f"{self.integration} - {self.internal_field} -> {self.external_field}"


# ─── Import AI Sales System models so Django migrations pick them up ───
from .sales_models import (  # noqa: F401, E402
    Lead, EmailSequence, EmailSequenceStep, LeadSequenceEnrollment,
    OutreachEmail, EmailReply, DemoBooking, Deal, DealActivity,
    SalesDailySnapshot, SalesAlert, OnboardingFunnel,
)


# =============================================================================
# IT HELPDESK & ITSM MODELS
# =============================================================================

class ITVendor(models.Model):
    name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=150, null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=50, null=True, blank=True)
    support_portal_url = models.URLField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    tenant = models.ForeignKey('Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ITAsset(models.Model):
    ASSET_TYPES = [
        ('laptop', 'Laptop / Computer'),
        ('mobile', 'Mobile Device'),
        ('server', 'Server / Infrastructure'),
        ('network', 'Network Equipment'),
        ('software', 'Software License'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active / In Use'),
        ('available', 'Available in Inventory'),
        ('in_repair', 'In Repair'),
        ('retired', 'Retired / Decommissioned'),
        ('lost', 'Lost / Stolen'),
    ]
    asset_tag = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES, default='laptop')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='available')
    owner = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')
    vendor = models.ForeignKey(ITVendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    tenant = models.ForeignKey('Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.asset_tag} - {self.name}"

    def auto_generate_credentials(self):
        """Generate secure placeholder credentials for this asset."""
        import string
        import random
        # Generate a standard secure password
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(16))
        # Ensure it has at least one of each required type
        password = (
            random.choice(string.ascii_uppercase) +
            random.choice(string.ascii_lowercase) +
            random.choice(string.digits) +
            random.choice("!@#$%^&*") +
            ''.join(random.choice(chars) for _ in range(12))
        )
        
        # For this CRM, we just return the credentials so they can be flashed in the UI.
        return {"username": "admin", "password": password}

class SLAConfiguration(models.Model):
    priority = models.CharField(max_length=10, unique=True, choices=[
        ('p1', 'P1 - Critical'),
        ('p2', 'P2 - High'),
        ('p3', 'P3 - Medium'),
        ('p4', 'P4 - Low'),
    ])
    first_response_hours = models.FloatField(help_text="Hours until first response is required")
    resolution_hours = models.FloatField(help_text="Hours until full resolution is required")
    escalation_priority = models.CharField(max_length=10, null=True, blank=True, choices=[
        ('p1', 'P1 - Critical'),
        ('p2', 'P2 - High'),
        ('p3', 'P3 - Medium'),
        ('p4', 'P4 - Low'),
    ], help_text="Priority to bump to if breached")
    
    def __str__(self):
        return f"SLA config for {self.get_priority_display()}"


class ITTicket(models.Model):
    PRIORITY_CHOICES = [
        ('p1', 'P1 - Critical'),
        ('p2', 'P2 - High'),
        ('p3', 'P3 - Medium'),
        ('p4', 'P4 - Low'),
    ]
    CATEGORY_CHOICES = [
        ('network', 'Network / Connectivity'),
        ('hardware', 'Hardware'),
        ('software', 'Software / Applications'),
        ('cloud', 'Cloud Infrastructure'),
        ('security', 'Security Incident'),
        ('access', 'Access / Permissions'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('pending_user', 'Pending User Info'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    title = models.CharField(max_length=300)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='p3')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    submitted_by = models.ForeignKey('User', on_delete=models.CASCADE, related_name='submitted_tickets')
    assigned_to = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    resolution_notes = models.TextField(blank=True, null=True)
    asset = models.ForeignKey(ITAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    tenant = models.ForeignKey('Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    device_asset_tag = models.CharField(max_length=100, null=True, blank=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    attachment = models.FileField(upload_to='it_tickets/', blank=True, null=True)
    csat_triggered = models.BooleanField(default=False)
    
    # SLA Tracking Fields
    sla_due_at = models.DateTimeField(null=True, blank=True)
    sla_status = models.CharField(max_length=20, default='healthy', choices=[
        ('healthy', 'Healthy'),
        ('at_risk', 'At Risk'),
        ('breached', 'Breached')
    ])
    first_response_due_at = models.DateTimeField(null=True, blank=True)
    first_responded_at = models.DateTimeField(null=True, blank=True)
    resolve_due_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"TKT-{self.id}: {self.title}"

    def save(self, *args, **kwargs):
        from django.utils import timezone
        from datetime import timedelta
        
        is_new = self.pk is None
        
        if is_new or (self.pk and hasattr(self, '_original_priority') and self._original_priority != self.priority):
            try:
                sla_config = SLAConfiguration.objects.get(priority=self.priority)
                now = timezone.now()
                if not self.first_response_due_at or not self.first_responded_at:
                    self.first_response_due_at = now + timedelta(hours=sla_config.first_response_hours)
                self.resolve_due_at = now + timedelta(hours=sla_config.resolution_hours)
                if self.sla_status == 'breached':
                    self.sla_status = 'healthy'
            except SLAConfiguration.DoesNotExist:
                sla_hours_map = {'p1': 4, 'p2': 24, 'p3': 72, 'p4': 120}
                hours = sla_hours_map.get(self.priority, 24)
                self.resolve_due_at = timezone.now() + timedelta(hours=hours)

        if self.pk and not self.first_responded_at and self.status != 'open':
            self.first_responded_at = timezone.now()
            
        if self.status in ['resolved', 'closed'] and not self.resolved_at:
            self.resolved_at = timezone.now()
        if self.status in ['open', 'in_progress'] and self.resolved_at:
            self.resolved_at = None

        super().save(*args, **kwargs)

    def is_sla_breached(self):
        from django.utils import timezone
        if self.status not in ['resolved', 'closed']:
            if self.resolve_due_at and timezone.now() > self.resolve_due_at:
                return True
        return False

class ITTicketComment(models.Model):
    ticket = models.ForeignKey(ITTicket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('User', on_delete=models.CASCADE)
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.ticket} by {self.author.username}"

class RoutingRule(models.Model):
    category = models.CharField(max_length=50, unique=True, choices=ITTicket.CATEGORY_CHOICES)
    assign_to = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role__in': ['admin', 'it_agent']})

    def __str__(self):
        return f"{self.get_category_display()} -> {self.assign_to}"

class Workflow(models.Model):
    name = models.CharField(max_length=255)
    trigger_event = models.CharField(max_length=50)
    action_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

class TicketAuditLog(models.Model):
    ticket = models.ForeignKey(ITTicket, on_delete=models.CASCADE, related_name='audit_logs')
    actor = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    field_changed = models.CharField(max_length=50)
    old_value = models.CharField(max_length=255, null=True, blank=True)
    new_value = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket.id} - {self.field_changed} changed at {self.timestamp}"

class KBArticle(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    tags = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated tags")
    upvotes = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class TicketSurvey(models.Model):
    ticket = models.OneToOneField(ITTicket, on_delete=models.CASCADE, related_name='survey')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Survey for Ticket {self.ticket.id} - {self.rating}/5"

class TicketMacro(models.Model):
    title = models.CharField(max_length=100)
    response_text = models.TextField()
    auto_status = models.CharField(max_length=20, choices=ITTicket.STATUS_CHOICES, null=True, blank=True)
    auto_priority = models.CharField(max_length=10, choices=ITTicket.PRIORITY_CHOICES, null=True, blank=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class TicketWorkLog(models.Model):
    ticket = models.ForeignKey(ITTicket, on_delete=models.CASCADE, related_name='work_logs')
    agent = models.ForeignKey('User', on_delete=models.CASCADE)
    time_spent_minutes = models.PositiveIntegerField(help_text="Time spent in minutes")
    date = models.DateField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent.username} - {self.time_spent_minutes}m on Ticket {self.ticket.id}"

# =============================================================================
# CYBERSECURITY SOC MODELS
# =============================================================================

class ThreatIncident(models.Model):
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    CATEGORY_CHOICES = [
        ('malware', 'Malware / Ransomware'),
        ('phishing', 'Phishing / Social Engineering'),
        ('ddos', 'DDoS Attack'),
        ('data_breach', 'Data Breach / Leak'),
        ('unauthorized_access', 'Unauthorized Access'),
        ('insider_threat', 'Insider Threat'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('contained', 'Contained'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ]
    title = models.CharField(max_length=300)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    tenant = models.ForeignKey('Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    reported_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_incidents')
    assigned_to = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_incidents')
    detection_source = models.CharField(max_length=150, blank=True, null=True)
    file_hash = models.CharField(max_length=255, null=True, blank=True)
    affected_system = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    cvss_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    malicious_domain = models.CharField(max_length=255, null=True, blank=True)
    ioc_indicators = models.TextField(blank=True, null=True)
    estimated_impact = models.TextField(blank=True, null=True)
    attack_vector = models.CharField(max_length=255, null=True, blank=True)
    response_notes = models.TextField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-detected_at']

    def __str__(self):
        return f"INC-{self.id}: {self.title}"

class ITProblem(models.Model):
    title = models.CharField(max_length=300)
    description = models.TextField()
    workaround = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=[
        ('investigating', 'Investigating'),
        ('identified', 'Root Cause Identified'),
        ('resolved', 'Resolved')
    ], default='investigating')
    related_tickets = models.ManyToManyField(ITTicket, blank=True, related_name='problems')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"PRB-{self.id}: {self.title}"

class ITChangeRequest(models.Model):
    title = models.CharField(max_length=300)
    description = models.TextField()
    risk_level = models.CharField(max_length=20, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='low')
    backout_plan = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=[
        ('planning', 'Planning'),
        ('pending_cab', 'Pending CAB Approval'),
        ('approved', 'Approved'),
        ('implemented', 'Implemented'),
        ('rejected', 'Rejected')
    ], default='planning')
    requested_by = models.ForeignKey('User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ChangeApprovalBoard(models.Model):
    change_request = models.ForeignKey(ITChangeRequest, on_delete=models.CASCADE, related_name='cab_votes')
    approver = models.ForeignKey('User', on_delete=models.CASCADE)
    vote = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    comments = models.TextField(blank=True, null=True)
    voted_at = models.DateTimeField(null=True, blank=True)

class ServiceCatalogItem(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=[('hardware', 'Hardware'), ('software', 'Software'), ('access', 'Access Request')])
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    requires_approval = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class ServiceRequest(models.Model):
    item = models.ForeignKey(ServiceCatalogItem, on_delete=models.CASCADE)
    requested_by = models.ForeignKey('User', on_delete=models.CASCADE)
    justification = models.TextField()
    status = models.CharField(max_length=50, choices=[('pending_approval', 'Pending Approval'), ('approved', 'Approved'), ('fulfilled', 'Fulfilled'), ('rejected', 'Rejected')], default='pending_approval')
    created_at = models.DateTimeField(auto_now_add=True)

class TicketRoutingRule(models.Model):
    name = models.CharField(max_length=150)
    condition_category = models.CharField(max_length=50, choices=ITTicket.CATEGORY_CHOICES, null=True, blank=True)
    action_assign_to = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

class AssetRelationship(models.Model):
    primary_asset = models.ForeignKey(ITAsset, on_delete=models.CASCADE, related_name='downstream_rels')
    dependent_asset = models.ForeignKey(ITAsset, on_delete=models.CASCADE, related_name='upstream_rels')
    relationship_type = models.CharField(max_length=50, choices=[('runs_on', 'Runs On'), ('depends_on', 'Depends On')])

class SystemOutage(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=[('investigating', 'Investigating'), ('identified', 'Identified'), ('monitoring', 'Monitoring'), ('resolved', 'Resolved')])
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

class BusinessHoursSchedule(models.Model):
    name = models.CharField(max_length=100)
    timezone = models.CharField(max_length=50, default='UTC')
    work_start_time = models.TimeField(default='09:00:00')
    work_end_time = models.TimeField(default='17:00:00')

class HolidayCalendar(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()

# =============================================================================
# DEV PROJECT PORTAL MODELS
# =============================================================================

class DevProjectRequest(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('web', 'Web Application'),
        ('mobile', 'Mobile App'),
        ('api', 'API Integration'),
        ('migration', 'Cloud Migration'),
        ('data', 'Data Analytics/Engineering'),
        ('ai', 'AI/ML Model Development'),
        ('other', 'Other Custom Software'),
    ]
    STATUS_CHOICES = [
        ('new', 'New Request'),
        ('review', 'Under Review'),
        ('scoping', 'Scoping / Estimating'),
        ('approved', 'Approved / Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    BUDGET_CHOICES = [
        ('10k', 'Under $10,000'),
        ('25k', '$10,000 - $25,000'),
        ('50k', '$25,000 - $50,000'),
        ('100k', '$50,000 - $100,000'),
        ('100k+', '$100,000+'),
        ('discuss', 'Not Sure / Let\'s Discuss'),
    ]
    TIMELINE_CHOICES = [
        ('asap', 'ASAP (Urgent)'),
        ('1mo', 'Within 1 Month'),
        ('3mo', '1-3 Months'),
        ('6mo', '3-6 Months'),
        ('flexible', 'Flexible / No Rush'),
    ]

    contact_name = models.CharField(max_length=150)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    company_name = models.CharField(max_length=150, null=True, blank=True)
    project_type = models.CharField(max_length=50, choices=PROJECT_TYPE_CHOICES, default='other')
    project_title = models.CharField(max_length=300)
    description = models.TextField()
    tech_preferences = models.TextField(null=True, blank=True)
    budget_range = models.CharField(max_length=20, choices=BUDGET_CHOICES, default='discuss')
    timeline = models.CharField(max_length=20, choices=TIMELINE_CHOICES, default='flexible')
    has_existing_codebase = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PRJ-{self.id}: {self.project_title}"

# =============================================================================
# REPORTING & AUTOMATION MODELS
# =============================================================================

class ScheduledReport(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    report_type = models.CharField(max_length=50, choices=[
        ('it_metrics', 'IT Helpdesk Metrics'),
        ('sec_summary', 'Security Incident Summary'),
        ('sla_breach', 'SLA Breach Report')
    ])
    frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ])
    format = models.CharField(max_length=10, choices=[('pdf', 'PDF'), ('csv', 'CSV'), ('json', 'JSON')], default='pdf')
    recipients = models.TextField(help_text="Comma separated email addresses")
    created_by = models.ForeignKey('User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.get_frequency_display()})"

class AutomationRun(models.Model):
    run_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[('success', 'Success'), ('failed', 'Failed')])
    log_output = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.run_type} at {self.timestamp}"


# ═══════════════════════════════════════════════════════════════
#  CYBERSECURITY EXPANSION MODELS
# ═══════════════════════════════════════════════════════════════

class VulnerabilityScan(models.Model):
    SEVERITY_CHOICES = [
        ('critical',  'Critical'),
        ('high',      'High'),
        ('medium',    'Medium'),
        ('low',       'Low'),
        ('info',      'Informational'),
    ]
    STATUS_CHOICES = [
        ('open',      'Open'),
        ('in_progress','In Progress'),
        ('patched',   'Patched'),
        ('accepted',  'Risk Accepted'),
        ('false_positive','False Positive'),
    ]
    title       = models.CharField(max_length=255)
    cve_id      = models.CharField(max_length=30, blank=True, help_text='e.g. CVE-2024-1234')
    severity    = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    cvss_score  = models.FloatField(null=True, blank=True, help_text='CVSS score 0.0-10.0')
    affected_asset = models.ForeignKey('ITAsset', on_delete=models.SET_NULL, null=True, blank=True, related_name='vulnerabilities')
    description = models.TextField(blank=True)
    remediation = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    discovered_at = models.DateTimeField(auto_now_add=True)
    patched_at  = models.DateTimeField(null=True, blank=True)
    reported_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"


class IPBlocklist(models.Model):
    REASON_CHOICES = [
        ('malware',   'Malware / C2'),
        ('phishing',  'Phishing'),
        ('brute_force','Brute Force'),
        ('spam',      'Spam'),
        ('tor_exit',  'Tor Exit Node'),
        ('other',     'Other'),
    ]
    ip_address  = models.GenericIPAddressField(unique=True)
    reason      = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    description = models.TextField(blank=True)
    added_by    = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    added_at    = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField(null=True, blank=True)
    is_active   = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.ip_address} ({self.get_reason_display()})"


class PhishingReport(models.Model):
    STATUS_CHOICES = [
        ('pending',     'Pending Review'),
        ('confirmed',   'Confirmed Phishing'),
        ('false_positive','False Positive'),
    ]
    reported_by     = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='phishing_reports')
    sender_email    = models.EmailField()
    subject         = models.CharField(max_length=500)
    description     = models.TextField()
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by     = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_phishing')
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Phishing report from {self.reported_by} – {self.subject[:50]}"


# ── Webhooks (Enterprise Developer Settings) ──────────────────

class WebhookEndpoint(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='webhooks')
    target_url = models.URLField(max_length=500)
    secret_key = models.CharField(max_length=64, blank=True)
    events = models.CharField(max_length=255, help_text="Comma separated events: candidate.created, job.updated, etc.", default="*")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.secret_key:
            import secrets
            self.secret_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tenant.name} - {self.target_url}"

class WebhookLog(models.Model):
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='logs')
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.event_type} -> {self.endpoint.target_url} ({self.status_code})"
