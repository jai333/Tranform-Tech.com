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
    company = models.CharField(max_length=255, default='Protingent India')
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
# For this prototype, we'll primarily use the fields from AbstractUser 
# that match the plan's User table.
class User(AbstractUser):
    # Role choices
    ROLE_JOBSEEKER = 'jobseeker'
    ROLE_RECRUITER = 'recruiter'
    ROLE_ADMIN = 'admin'
    
    ROLE_CHOICES = [
        (ROLE_JOBSEEKER, 'Job Seeker'),
        (ROLE_RECRUITER, 'Recruiter'),
        (ROLE_ADMIN, 'Administrator'),
    ]
    
    # Add role field to User model
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_JOBSEEKER,
        help_text='Designates the role and permissions of this user.'
    )
    
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
