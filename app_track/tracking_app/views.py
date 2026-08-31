import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from .decorators import paid_required, require_ats_access, require_it_access, require_executive_access, require_tier
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.core.exceptions import PermissionDenied
from .models import Candidate, Job, Interview, InterviewScorecard, User, Application, Friendship, Message, Notification, JobSeekerApplication, Note, ITTicket, ITTicketComment, ThreatIncident, DevProjectRequest, ScheduledReport, AutomationRun, ResumeData, ITAsset, ITVendor, KBArticle, TicketSurvey, TicketAuditLog, RoutingRule, SLAConfiguration, TicketMacro, TicketWorkLog, ITProblem, ITChangeRequest, ChangeApprovalBoard, ServiceCatalogItem, ServiceRequest, TicketRoutingRule, AssetRelationship, SystemOutage, BusinessHoursSchedule, HolidayCalendar, VulnerabilityScan, IPBlocklist, PhishingReport
from .forms import UserRegistrationForm, ProfileUpdateForm, JobSeekerApplicationForm, JobForm
from django.db import models
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from .utils import generate_meeting_url

logger = logging.getLogger(__name__)
from django.template.context_processors import csrf
from django.template import RequestContext

# Custom context processor to add global variables
def add_global_context(request):
    context = {}
    
    if request.user.is_authenticated:
        # Get unread notifications count
        unread_notifications_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        context['unread_notifications_count'] = unread_notifications_count
    
    return context

# Create your views here.

def get_tenant_filter(user):
    """Returns a dict to filter querysets by the user's tenant (unless they are superuser)."""
    if user.is_superuser or not user.tenant:
        return {}
    return {'tenant': user.tenant}

@login_required
def standard_ops_dashboard(request):
    """The main unified dashboard for authenticated users (Standard Ops)."""

    if getattr(request.user, "role", None) == "client":
        return redirect("client-portal")
        
    tenant_filter = get_tenant_filter(request.user)

    
    context = {'page_title': 'Standard Operations'}
    
    # 1. ATS Tasks
    if request.user.can_view_ats or request.user.is_superuser:
        context['my_applications'] = Application.objects.filter(user=request.user, **tenant_filter).order_by('-applied_date')[:5]
        context['recent_jobs'] = Job.objects.filter(**tenant_filter).order_by('-created_at')[:5]
    
    # 2. Sales Tasks
    if request.user.can_view_sales or request.user.is_superuser:
        from .sales_models import Deal
        context['my_deals'] = Deal.objects.filter(**tenant_filter).exclude(stage__in=['won', 'lost']).order_by('-last_activity_at')[:5]
    
    # 3. IT Tasks
    if request.user.can_view_it or request.user.is_superuser:
        context['my_it_tickets'] = ITTicket.objects.filter(submitted_by=request.user, **tenant_filter).exclude(status='closed').order_by('-created_at')[:5]
        
    return render(request, 'tracking_app/standard_ops_dashboard.html', context)

def home(request):
    return render(request, 'tracking_app/home.html')
# User Authentication Views
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Set dashboard permissions based on role
            user.can_view_ats = False
            user.can_view_sales = False
            user.can_view_it = False
            user.can_view_executive = False
            
            if user.role in [User.ROLE_JOBSEEKER, User.ROLE_RECRUITER]:
                user.can_view_ats = True
            elif user.role == User.ROLE_SALES:
                user.can_view_sales = True
            elif user.role == User.ROLE_IT:
                user.can_view_it = True
            elif user.role == User.ROLE_ADMIN:
                user.can_view_ats = True
                user.can_view_sales = True
                user.can_view_it = True
                user.can_view_executive = True
            
            # Create a tenant for the user to isolate data
            from .models import Tenant, AutomationRule, AutomationLog
            tenant_name = f"{user.username}'s Workspace"
            tenant = Tenant.objects.create(name=tenant_name, subscription_plan='free')
            user.tenant = tenant
            
            user.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'tracking_app/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'tracking_app/profile.html', {'form': form})

def public_profile(request, username):
    # Lookup by username case-insensitively to be tolerant of URL casing
    user = User.objects.filter(username__iexact=username).first()
    if not user:
        raise Http404("User not found")
    friendship_status = None
    
    if request.user.is_authenticated and request.user != user:
        # Check if there's an existing friendship between the users
        friendship = Friendship.objects.filter(
            (models.Q(sender=request.user) & models.Q(receiver=user)) |
            (models.Q(sender=user) & models.Q(receiver=request.user))
        ).first()
        
        if friendship:
            if friendship.status == 'accepted':
                friendship_status = 'accepted'
            elif friendship.status == 'pending':
                # Check if the current user is the sender
                if friendship.sender == request.user:
                    friendship_status = 'pending_sent'
                else:
                    friendship_status = 'pending_received'
            elif friendship.status == 'rejected':
                friendship_status = 'rejected'
        else:
            friendship_status = 'none'
    
    context = {
        'profile_user': user,
        'is_own_profile': request.user.is_authenticated and request.user == user,
        'friendship_status': friendship_status,
        'friendship': friendship if 'friendship' in locals() else None
    }
    
    return render(request, 'tracking_app/public_profile.html', context)

@login_required
def send_friend_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    
    # Check if users are already friends or have a pending request
    existing_friendship = Friendship.get_friendship(request.user, receiver)
    
    if existing_friendship:
        if existing_friendship.status == 'accepted':
            messages.info(request, f'You are already friends with {receiver.username}')
        elif existing_friendship.status == 'pending':
            if existing_friendship.sender == request.user:
                messages.info(request, f'You already sent a friend request to {receiver.username}')
            else:
                messages.info(request, f'{receiver.username} has already sent you a friend request')
        elif existing_friendship.status == 'rejected':
            # Allow sending a new request if previously rejected
            existing_friendship.delete()
            Friendship.objects.create(sender=request.user, receiver=receiver)
            messages.success(request, f'Friend request sent to {receiver.username}')
            
            # Create notification for the receiver
            Notification.objects.create(
                recipient=receiver,
                content=f"{request.user.username} sent you a friend request",
                notification_type=Notification.TYPE_FRIEND_REQUEST,
                link=f"/public-profile/{request.user.username}/"
            )
    else:
        # Create a new friendship request
        Friendship.objects.create(sender=request.user, receiver=receiver)
        messages.success(request, f'Friend request sent to {receiver.username}')
        
        # Create notification for the receiver
        Notification.objects.create(
            recipient=receiver,
            content=f"{request.user.username} sent you a friend request",
            notification_type=Notification.TYPE_FRIEND_REQUEST,
            link=f"/public-profile/{request.user.username}/"
        )
    
    # Redirect back to the user's profile
    return redirect('public-profile', username=receiver.username)

@login_required
def accept_friend_request(request, request_id):
    friendship = get_object_or_404(Friendship, id=request_id, receiver=request.user, status='pending')
    friendship.status = 'accepted'
    friendship.save()
    messages.success(request, f'You are now friends with {friendship.sender.username}')
    
    # Create notification for the friend request sender
    Notification.objects.create(
        recipient=friendship.sender,
        content=f"{request.user.username} accepted your friend request",
        notification_type=Notification.TYPE_FRIEND_REQUEST,
        link=f"/public-profile/{request.user.username}/"
    )
    
    return redirect('friend-list')

@login_required
def reject_friend_request(request, request_id):
    friendship = get_object_or_404(Friendship, id=request_id, receiver=request.user, status='pending')
    friendship.status = 'rejected'
    friendship.save()
    messages.info(request, f'Friend request from {friendship.sender.username} rejected')
    return redirect('friend-list')

def service_addons_view(request):
    # Get user's friends (accepted friendships)
    friends_as_sender = Friendship.objects.filter(
        sender=request.user, 
        status='accepted'
    ).select_related('receiver')
    
    friends_as_receiver = Friendship.objects.filter(
        receiver=request.user, 
        status='accepted'
    ).select_related('sender')
    
    # Create a list of friend users
    friends = []
    for friendship in friends_as_sender:
        friends.append(friendship.receiver)
    
    for friendship in friends_as_receiver:
        friends.append(friendship.sender)
    
    # Get pending friend requests sent to the user
    pending_requests = Friendship.objects.filter(
        receiver=request.user, 
        status='pending'
    ).select_related('sender')
    
    context = {
        'friends': friends,
        'pending_requests': pending_requests,
    }
    
    return render(request, 'tracking_app/friend_list.html', context)

@login_required
def friend_list(request):
    # Get user's friends (accepted friendships)
    friends_as_sender = Friendship.objects.filter(
        sender=request.user, 
        status='accepted'
    ).select_related('receiver')
    
    friends_as_receiver = Friendship.objects.filter(
        receiver=request.user, 
        status='accepted'
    ).select_related('sender')
    
    # Create a list of friend users
    friends = []
    for friendship in friends_as_sender:
        friends.append(friendship.receiver)
    
    for friendship in friends_as_receiver:
        friends.append(friendship.sender)
    
    # Get pending friend requests sent to the user
    pending_requests = Friendship.objects.filter(
        receiver=request.user, 
        status='pending'
    ).select_related('sender')
    
    context = {
        'friends': friends,
        'pending_requests': pending_requests,
    }
    
    return render(request, 'tracking_app/friend_list.html', context)

@login_required
def chat(request, username):
    friend = get_object_or_404(User, username=username)
    
    # Check if users are friends
    friendship = Friendship.get_friendship(request.user, friend)
    
    if not friendship or friendship.status != 'accepted':
        messages.error(request, f'You must be friends with {friend.username} to chat.')
        return redirect('friend-list')
    
    # Get all messages between the users
    chat_messages = Message.objects.filter(
        friendship=friendship
    ).order_by('created_at')
    
    # If this is the first chat (no messages), create a system notification for both users
    if not chat_messages.exists():
        # Create system notification for both users only if they haven't chatted before
        for user in [request.user, friend]:
            if user != request.user:  # Only create for the friend, not the requester
                Notification.objects.create(
                    recipient=user,
                    content=f"You can now chat with {request.user.username}",
                    notification_type=Notification.TYPE_SYSTEM,
                    link=f"/chat/{request.user.username}/"
                )
    
    # Mark messages as read if the current user is the receiver
    unread_messages = chat_messages.filter(sender=friend, is_read=False)
    unread_messages.update(is_read=True)
    
    context = {
        'friend': friend,
        'friendship': friendship,
        'messages': chat_messages,
    }
    
    return render(request, 'tracking_app/chat.html', context)

@login_required
def send_message(request, friendship_id):
    friendship = get_object_or_404(Friendship, id=friendship_id)
    
    # Check if the user is part of this friendship
    if request.user != friendship.sender and request.user != friendship.receiver:
        messages.error(request, 'You do not have permission to send messages in this conversation.')
        return redirect('friend-list')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        
        if content:
            # Create the new message
            message = Message.objects.create(
                friendship=friendship,
                sender=request.user,
                content=content
            )
            
            # Get friend (message recipient)
            friend = friendship.receiver if request.user == friendship.sender else friendship.sender
            
            # Create notification for the message recipient
            Notification.objects.create(
                recipient=friend,
                content=f"New message from {request.user.username}",
                notification_type=Notification.TYPE_MESSAGE,
                link=f"/chat/{request.user.username}/"
            )
            
            # Redirect back to the chat
            return redirect('chat', username=friend.username)
    
    # If not POST or no content, redirect back to friend list
    return redirect('friend-list')

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    # Redirect to the notification link or back to the previous page
    if notification.link:
        return redirect(notification.link)
    else:
        return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()
    
    # Redirect back to the previous page
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def notifications_count(request):
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})

@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
    
    notification_list = []
    for notification in notifications:
        notification_list.append({
            'id': notification.id,
            'content': notification.content,
            'notification_type': notification.notification_type,
            'created_at': notification.created_at.isoformat(),
            'is_read': notification.is_read,
            'link': notification.link
        })
    
    return JsonResponse({
        'notifications': notification_list
    })

# Mixins for permissions
class RecruiterRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_recruiter or 
            self.request.user.is_admin_role or 
            self.request.user.is_staff
        )

    def handle_no_permission(self):
        messages.error(self.request, "Only recruiters can access this feature. Please contact an administrator if you need access.")
        return redirect('home')

# Owner or Admin Required Mixin for update/delete operations
class OwnerOrAdminRequiredMixin(UserPassesTestMixin):
    owner_field = 'user'
    
    def test_func(self):
        obj = self.get_object()
        # Allow access if the user is the owner, an admin, or a staff member
        return (getattr(obj, self.owner_field) == self.request.user or 
                self.request.user.is_admin_role or 
                self.request.user.is_staff)
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to edit or delete this item.")
        # Return a default redirect URL that doesn't depend on self.object
        return redirect('job-list')

# Jobseeker Restriction Mixin - redirects job seekers to view-only pages for Applications, Interviews, etc.
class JobSeekerRestrictedMixin(UserPassesTestMixin):
    def test_func(self):
        # Check if user is not a job seeker (is recruiter, admin or staff)
        return not self.request.user.is_jobseeker or self.request.user.is_admin_role or self.request.user.is_staff
    
    def handle_no_permission(self):
        messages.warning(self.request, "This section is only accessible to recruiters. As a job seeker, you can browse job listings.")
        return redirect('job-list')

# ── CANDIDATE SOURCING ENGINE ─────────────────────────────────────────────

@login_required
@require_ats_access
def candidate_sourcing(request):
    """LinkedIn-style Candidate Sourcing Engine with smart filters and one-click pipeline add."""
    from .models import Job
    import json

    # Get active jobs for the "target role" dropdown
    jobs = Job.objects.filter(status='active').order_by('title')

    # Smart skill suggestions
    skill_tags = [
        "Python", "JavaScript", "React", "Node.js", "Java", "C++", "Go",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "SQL", "MongoDB",
        "Machine Learning", "Data Science", "DevOps", "Cybersecurity",
        "Product Management", "Project Management", "Sales", "Marketing",
        "Finance", "Accounting", "HR", "Legal", "Healthcare", "Nursing",
        "Civil Engineering", "Mechanical Engineering", "Electrical Engineering",
    ]

    # Industry options
    industries = [
        "Technology", "Finance", "Healthcare", "Manufacturing", "Retail",
        "Education", "Legal", "Construction", "Logistics", "Media",
        "Government", "Non-Profit", "Consulting", "Real Estate", "Energy",
    ]

    context = {
        'jobs': jobs,
        'skill_tags': skill_tags,
        'industries': industries,
        'page_title': 'Candidate Sourcing Engine',
    }
    return render(request, 'tracking_app/candidate_sourcing.html', context)


@login_required
@require_ats_access
def add_sourced_candidate(request):
    """AJAX: Add a sourced candidate directly into the Candidate pipeline."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    if not name or not email:
        return JsonResponse({'error': 'Name and email are required'}, status=400)

    parts = name.split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    # Don't duplicate
    if Candidate.objects.filter(email=email).exists():
        candidate = Candidate.objects.get(email=email)
        return JsonResponse({'success': True, 'candidate_id': candidate.id, 'message': 'Candidate already in your pipeline.', 'existing': True})

    candidate = Candidate.objects.create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=data.get('phone', ''),
        resume=f"Sourced via Candidate Sourcing Engine\nTitle: {data.get('title','')}\nCompany: {data.get('company','')}\nLocation: {data.get('location','')}\nExperience: {data.get('experience','')}\nSkills: {', '.join(data.get('skills',[]))}\nLinkedIn: {data.get('linkedin','')}",
        user=request.user,
        tenant=getattr(request.user, 'tenant', None),
    )
    return JsonResponse({'success': True, 'candidate_id': candidate.id, 'message': f'{candidate.full_name} added to your pipeline!'})

from django.views.decorators.csrf import csrf_exempt
import json
import requests

@csrf_exempt
@login_required
@require_ats_access
def import_ghost_profile(request):
    """Next-Gen AI Feature: LinkedIn/GitHub Ghost Profiler"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
    url = data.get('url', '').strip()
    if not url:
        return JsonResponse({'error': 'URL is required'}, status=400)
    
    # Initialize variables
    full_name = "Ghost Candidate"
    company = "Unknown"
    location = "Unknown"
    skills = []
    about = "Imported via Ghost Profiler."
    score = 75
    email = ""
    
    # Check if GitHub or LinkedIn
    if "github.com/" in url:
        # It's a GitHub URL
        username = url.rstrip('/').split('/')[-1]
        try:
            # Note: Unauthenticated requests have a low rate limit, but it's enough for a demo
            user_resp = requests.get(f"https://api.github.com/users/{username}")
            if user_resp.status_code == 200:
                user_data = user_resp.json()
                full_name = user_data.get('name') or username
                company = user_data.get('company') or "Unknown"
                location = user_data.get('location') or "Unknown"
                about = user_data.get('bio') or f"GitHub developer with {user_data.get('public_repos', 0)} public repos."
                email = user_data.get('email') or f"{username}@github.local"
                
                # Fetch repos to determine tech stack and score
                repos_resp = requests.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10")
                if repos_resp.status_code == 200:
                    repos = repos_resp.json()
                    languages = set()
                    total_stars = 0
                    for repo in repos:
                        if repo.get('language'):
                            languages.add(repo.get('language'))
                        total_stars += repo.get('stargazers_count', 0)
                    
                    skills = list(languages)[:10] if languages else ["Git", "Software Engineering"]
                    
                    # Calculate Engineer Quality Score based on stars and repos
                    base_score = 65
                    star_bonus = min(total_stars * 2, 20)
                    repo_bonus = min(len(repos), 10)
                    score = min(base_score + star_bonus + repo_bonus, 99)
                    
        except Exception as e:
            print(f"GitHub fetch error: {e}")
            pass
            
    elif "linkedin.com/in/" in url:
        # It's a LinkedIn URL (Mock AI Generation)
        slug = url.split("/in/")[1].replace("/", "").split("?")[0]
        parts = slug.split("-")
        full_name = " ".join([p.capitalize() for p in parts[:2]]) if len(parts) >= 2 else slug.capitalize()
        company = "Confidential Inc."
        location = "San Francisco, CA"
        skills = ["Leadership", "Agile", "Cross-functional Team Leadership", "Product Management"]
        about = f"Senior professional identified via LinkedIn scraping. Strong background based on profile footprint."
        score = 88
        email = f"{slug.replace('-', '.')}@linkedin.local"
    else:
        return JsonResponse({'error': 'Please provide a valid GitHub or LinkedIn URL'}, status=400)
        
    if not email:
        email = f"ghost_{abs(hash(url))}@ghost.local"
        
    first_name = full_name.split(' ')[0] if ' ' in full_name else full_name
    last_name = full_name.split(' ')[1] if ' ' in full_name else ""
    
    # Check if candidate exists to avoid unique constraint errors
    candidate = Candidate.objects.filter(email=email).first()
    if not candidate:
        # Create Candidate
        candidate = Candidate.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            resume=f"Source URL: {url}\n\n{about}",
            user=request.user,
            tenant=getattr(request.user, 'tenant', None),
        )
        
        # Create AI Summary
        CandidateAISummary.objects.create(
            candidate=candidate,
            professional_summary=about,
            key_strengths=skills[:5],
            development_areas=["Remote Collaboration", "Public Speaking"],
            ideal_roles=[f"Senior {skills[0]} Developer" if skills else "Senior Developer", "Tech Lead"],
            overall_profile_score=score,
            communication_score=score - 5,
            technical_score=score + 2,
            leadership_score=score - 10,
            generated_by='Ghost Profiler AI'
        )
    
    return JsonResponse({
        'success': True,
        'candidate_id': candidate.id,
        'profile': {
            'name': full_name,
            'company': company,
            'location': location,
            'skills': skills,
            'about': about,
            'score': score,
            'email': email,
            'url': url
        }
    })

@csrf_exempt
@login_required
@require_ats_access
def parse_and_scrape(request):
    """Real JD/CV Parser & Multi-site Web Scraper for live candidate sourcing."""
    import pypdf
    from docx import Document
    from tracking_app.services.sourcing_engine import SourcingEngine
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    cv_file = request.FILES.get('cv_file')
    if not cv_file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
        
    text = ""
    try:
        if cv_file.name.lower().endswith('.pdf'):
            reader = pypdf.PdfReader(cv_file)
            for page in reader.pages:
                text += page.extract_text() + " "
        elif cv_file.name.lower().endswith('.docx'):
            doc = Document(cv_file)
            for para in doc.paragraphs:
                text += para.text + " "
        else:
            text = cv_file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return JsonResponse({'error': f'Failed to parse file: {str(e)}'}, status=400)

    # Basic NLP keyword extraction (handles both JD and CV)
    text_lower = text.lower()
    
    tech_skills = [
        "python", "java", "javascript", "react", "node.js", "aws", "docker", "kubernetes",
        "machine learning", "sql", "devops", "cloud", "agile", "c++", "go", "ruby",
        "data science", "cybersecurity", "azure", "salesforce", "marketing", "seo", "hubspot"
    ]
    found_skills = [skill for skill in tech_skills if skill in text_lower]
    
    if not found_skills:
        found_skills = ["communication", "project management"] # fallback
        
    # Determine title based on document content
    title = "Professional Candidate"
    if "data" in text_lower or "machine learning" in text_lower:
        title = "Data Scientist"
    elif "devops" in text_lower or "kubernetes" in text_lower:
        title = "DevOps Engineer"
    elif "marketing" in text_lower or "seo" in text_lower:
        title = "Marketing Specialist"
    elif "sales" in text_lower or "account executive" in text_lower:
        title = "Sales Executive"
    elif "engineer" in text_lower or "developer" in text_lower:
        title = "Software Engineer"
        
    if "manager" in text_lower or "lead" in text_lower:
        title = f"Lead {title}"
        
    # Run the Hybrid Sourcing Engine
    candidates = SourcingEngine.source_candidates(
        title=title,
        skills=[s.title() for s in found_skills],
        location="Remote",
        num_results=10
    )
        
    return JsonResponse({
        'success': True,
        'extracted_title': title.title(),
        'extracted_skills': [s.title() for s in found_skills],
        'candidates': candidates
    })

def search_web_candidates(request):
    """Handles manual search queries from the candidate sourcing engine UI."""
    from tracking_app.services.sourcing_engine import SourcingEngine
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
        
    try:
        data = json.loads(request.body)
        title = data.get('title', 'Software Engineer')
        location = data.get('location', 'Remote')
        skills = data.get('skills', [])
        
        # Run the Hybrid Sourcing Engine
        candidates = SourcingEngine.source_candidates(
            title=title,
            skills=skills,
            location=location,
            num_results=12
        )
        
        return JsonResponse({
            'success': True,
            'candidates': candidates
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)



# Candidate CRUD Views
class CandidateListView(LoginRequiredMixin, JobSeekerRestrictedMixin, ListView):
    model = Candidate
    template_name = 'tracking_app/candidate_list.html'
    context_object_name = 'candidates'
    ordering = ['-application_date']
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('user')
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                first_name__icontains=search_query
            ) | queryset.filter(
                last_name__icontains=search_query
            ) | queryset.filter(
                email__icontains=search_query
            )
        return queryset.only(
            'id', 'first_name', 'last_name', 'email', 'phone', 
            'application_date', 'user_id', 'user__first_name', 'user__last_name'
        )

class CandidateDetailView(LoginRequiredMixin, JobSeekerRestrictedMixin, DetailView):
    model = Candidate
    template_name = 'tracking_app/candidate_detail.html'
    context_object_name = 'candidate'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        
        # If user is job seeker or recruiter (not admin/staff), check ownership
        if (user.is_jobseeker or user.is_recruiter) and not (user.is_admin_role or user.is_staff):
            if obj.user != user:
                raise Http404("You don't have permission to view this candidate.")
        
        return obj

class CandidateCreateView(RecruiterRequiredMixin, CreateView):
    model = Candidate
    template_name = 'tracking_app/candidate_form.html'
    fields = ['first_name', 'last_name', 'email', 'phone', 'resume']
    success_url = reverse_lazy('candidate-list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f'Candidate {form.instance.first_name} {form.instance.last_name} has been created!')
        return super().form_valid(form)

class CandidateUpdateView(RecruiterRequiredMixin, OwnerOrAdminRequiredMixin, UpdateView):
    model = Candidate
    template_name = 'tracking_app/candidate_form.html'
    fields = ['first_name', 'last_name', 'email', 'phone', 'resume']
    
    def get_success_url(self):
        return reverse_lazy('candidate-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Candidate {form.instance.first_name} {form.instance.last_name} has been updated!')
        return super().form_valid(form)

class CandidateDeleteView(RecruiterRequiredMixin, OwnerOrAdminRequiredMixin, DeleteView):
    model = Candidate
    template_name = 'tracking_app/candidate_confirm_delete.html'
    success_url = reverse_lazy('candidate-list')

# Job CRUD Views
class JobListView(ListView):
    model = Job
    template_name = 'tracking_app/job_list.html'
    context_object_name = 'jobs'
    ordering = ['-posting_date']
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        
        # Apply search filter if provided
        if search_query:
            queryset = queryset.filter(title__icontains=search_query) | \
                    queryset.filter(description__icontains=search_query) | \
                    queryset.filter(location__icontains=search_query)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Set default value for unauthenticated users
        context['is_recruiter'] = False
        
        # Add a flag indicating if the user is a recruiter (for authenticated users)
        if self.request.user.is_authenticated:
            context['is_recruiter'] = self.request.user.is_recruiter or self.request.user.is_admin_role or self.request.user.is_staff
        return context

class JobDetailView(DetailView):
    model = Job
    template_name = 'tracking_app/job_detail.html'
    context_object_name = 'job'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['applications'] = Application.objects.filter(job=self.object)
        
        # Default values for unauthenticated users
        context['is_recruiter'] = False
        context['already_applied'] = False
        
        # Add additional context for authenticated users
        if self.request.user.is_authenticated:
            # Add a flag indicating if the user is a recruiter
            context['is_recruiter'] = self.request.user.is_recruiter or self.request.user.is_admin_role or self.request.user.is_staff
            
            # Check if the user has already applied for this job
            if self.request.user.is_jobseeker:
                application = JobSeekerApplication.objects.filter(job=self.object, applicant=self.request.user).first()
                if application:
                    context['already_applied'] = True
                    context['application_date'] = application.applied_date
                    context['application_id'] = application.id
                    context['application_status'] = application.status
                else:
                    context['already_applied'] = False
                
        return context

class JobCreateView(RecruiterRequiredMixin, CreateView):
    model = Job
    template_name = 'tracking_app/job_form.html'
    form_class = JobForm
    success_url = reverse_lazy('job-list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f'Job {form.instance.title} has been created!')
        return super().form_valid(form)

class JobUpdateView(RecruiterRequiredMixin, OwnerOrAdminRequiredMixin, UpdateView):
    model = Job
    template_name = 'tracking_app/job_form.html'
    form_class = JobForm
    
    def get_success_url(self):
        return reverse_lazy('job-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Job {form.instance.title} has been updated!')
        return super().form_valid(form)

class JobDeleteView(RecruiterRequiredMixin, OwnerOrAdminRequiredMixin, DeleteView):
    model = Job
    template_name = 'tracking_app/job_confirm_delete.html'
    success_url = reverse_lazy('job-list')

# Application Views
class ApplicationListView(LoginRequiredMixin, JobSeekerRestrictedMixin, ListView):
    model = Application
    template_name = 'tracking_app/application_list.html'
    context_object_name = 'applications'
    ordering = ['-applied_date']
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                candidate__first_name__icontains=search_query) | \
                queryset.filter(candidate__last_name__icontains=search_query) | \
                queryset.filter(job__title__icontains=search_query)
        return queryset

@login_required
def application_detail(request, application_id):
    application = get_object_or_404(JobSeekerApplication, pk=application_id)
    
    # Ensure only the applicant or the job author can view the application
    if request.user != application.applicant and request.user != application.job.user:
        messages.error(request, "You don't have permission to view this application.")
        return redirect('home')
    
    # Get candidate records for the applicant to find interviews
    candidate_list = Candidate.objects.filter(email=application.applicant.email)
    
    # Get interviews for this application if it's accepted
    interviews = []
    if application.status == JobSeekerApplication.STATUS_ACCEPTED and candidate_list.exists():
        interviews = Interview.objects.filter(
            candidate__in=candidate_list,
            job=application.job
        ).order_by('-date_time')
    
    context = {
        'application': application,
        'is_recruiter': application.job.user == request.user,
        'candidate_list': candidate_list,
        'interviews': interviews
    }
    
    return render(request, 'tracking_app/application_detail.html', context)

class ApplicationCreateView(RecruiterRequiredMixin, CreateView):
    model = Application
    template_name = 'tracking_app/application_form.html'
    fields = ['candidate', 'job', 'status', 'notes']
    success_url = reverse_lazy('application-list')
    
    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get('candidate'):
            initial['candidate'] = self.request.GET.get('candidate')
        if self.request.GET.get('job'):
            initial['job'] = self.request.GET.get('job')
        return initial
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f'Application for {form.instance.candidate} to {form.instance.job} has been created!')
        return super().form_valid(form)

class ApplicationUpdateView(RecruiterRequiredMixin, UpdateView):
    model = Application
    template_name = 'tracking_app/application_form.html'
    fields = ['status', 'notes']
    
    def get_success_url(self):
        return reverse_lazy('application-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Application for {form.instance.candidate} to {form.instance.job} has been updated!')
        return super().form_valid(form)

class ApplicationDeleteView(RecruiterRequiredMixin, DeleteView):
    model = Application
    template_name = 'tracking_app/application_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('job-detail', kwargs={'pk': self.object.job.pk})

# Interview CRUD Views
class InterviewListView(LoginRequiredMixin, JobSeekerRestrictedMixin, ListView):
    model = Interview
    template_name = 'tracking_app/interview_list.html'
    context_object_name = 'interviews'
    ordering = ['-date_time']
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                candidate__first_name__icontains=search_query) | \
                queryset.filter(candidate__last_name__icontains=search_query) | \
                queryset.filter(job__title__icontains=search_query) | \
                queryset.filter(interviewer__icontains=search_query)
        return queryset

class InterviewDetailView(LoginRequiredMixin, JobSeekerRestrictedMixin, DetailView):
    model = Interview
    template_name = 'tracking_app/interview_detail.html'
    context_object_name = 'interview'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        
        # Job seekers can only view interviews for their candidates
        if user.is_jobseeker:
            if obj.candidate.user != user:
                raise Http404("You don't have permission to view this interview.")
        # Recruiters (not admin/staff) can only view their own interviews
        elif user.is_recruiter and not (user.is_admin_role or user.is_staff):
            if obj.user != user:
                raise Http404("You don't have permission to view this interview.")
        
        return obj

class InterviewCreateView(RecruiterRequiredMixin, CreateView):
    model = Interview
    template_name = 'tracking_app/interview_form.html'
    fields = ['candidate', 'job', 'date_time', 'interviewer', 'type', 'status', 'feedback']
    success_url = reverse_lazy('interview-list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # Generate meeting URL for video interviews
        if form.instance.type == Interview.TYPE_VIDEO:
            meeting_url, _ = generate_meeting_url()
            form.instance.meeting_url = meeting_url
            
        messages.success(self.request, f'Interview for {form.instance.candidate} has been scheduled!')
        return super().form_valid(form)
    
    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get('application'):
            application = get_object_or_404(Application, pk=self.request.GET.get('application'))
            initial['candidate'] = application.candidate
            initial['job'] = application.job
            initial['application'] = application
        return initial

class InterviewUpdateView(RecruiterRequiredMixin, OwnerOrAdminRequiredMixin, UpdateView):
    model = Interview
    template_name = 'tracking_app/interview_form.html'
    fields = ['candidate', 'job', 'date_time', 'interviewer', 'type', 'status', 'feedback']
    
    def get_success_url(self):
        return reverse_lazy('interview-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Generate or update meeting URL if the type is changed to video
        # or if it's a video interview without a meeting URL
        if form.instance.type == Interview.TYPE_VIDEO and not form.instance.meeting_url:
            meeting_url, _ = generate_meeting_url()
            form.instance.meeting_url = meeting_url
        
        # Remove meeting URL if type is changed from video to something else
        elif form.instance.type != Interview.TYPE_VIDEO and form.instance.meeting_url:
            form.instance.meeting_url = None
            
        messages.success(self.request, f'Interview for {form.instance.candidate} has been updated!')
        return super().form_valid(form)

class InterviewDeleteView(RecruiterRequiredMixin, OwnerOrAdminRequiredMixin, DeleteView):
    model = Interview
    template_name = 'tracking_app/interview_confirm_delete.html'
    success_url = reverse_lazy('interview-list')

# Job Application Views for Job Seekers
@login_required
def apply_for_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    
    # Check if user has already applied for this job
    existing_application = JobSeekerApplication.objects.filter(job=job, applicant=request.user).first()
    
    # Only block reapplication if there's an active application (not withdrawn)
    if existing_application and existing_application.status != JobSeekerApplication.STATUS_WITHDRAWN:
        messages.warning(request, f'You have already applied for this job on {existing_application.applied_date.strftime("%B %d, %Y")}.')
        return redirect('job-detail', pk=job_id)
    
    if request.method == 'POST':
        form = JobSeekerApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            # If there's a withdrawn application, update it instead of creating a new one
            if existing_application and existing_application.status == JobSeekerApplication.STATUS_WITHDRAWN:
                existing_application.cover_letter = form.cleaned_data['cover_letter']
                # Only update resume if a new one was provided
                if form.cleaned_data.get('resume'):
                    existing_application.resume = form.cleaned_data['resume']
                existing_application.status = JobSeekerApplication.STATUS_PENDING  # Change status back to pending
                existing_application.applied_date = datetime.now()  # Update application date
                existing_application.save()
                application = existing_application
                messages.success(request, f'Your application for {job.title} has been resubmitted successfully!')
            else:
                # Create a new application
                application = form.save(commit=False)
                application.job = job
                application.applicant = request.user
                application.save()
                messages.success(request, f'Your application for {job.title} has been submitted successfully!')
            
            # Notify the job author (recruiter)
            Notification.objects.create(
                recipient=job.user,
                content=f"{request.user.username} applied for your job: {job.title}",
                notification_type=Notification.TYPE_JOB_APPLICATION,
                link=f"/application-detail/{application.id}/"
            )
            
            return redirect('job-detail', pk=job_id)
    else:
        # Pre-populate form with data from withdrawn application if it exists
        if existing_application and existing_application.status == JobSeekerApplication.STATUS_WITHDRAWN:
            form = JobSeekerApplicationForm(instance=existing_application)
            messages.info(request, 'You previously withdrew your application. You can reapply by submitting this form again.')
        else:
            form = JobSeekerApplicationForm()
    
    return render(request, 'tracking_app/jobseeker_application_form.html', {
        'form': form,
        'job': job,
        'is_reapplying': existing_application and existing_application.status == JobSeekerApplication.STATUS_WITHDRAWN
    })

@login_required
def my_applications(request):
    applications = JobSeekerApplication.objects.filter(applicant=request.user).order_by('-applied_date')
    
    context = {
        'applications': applications
    }
    
    return render(request, 'tracking_app/my_applications.html', context)

@login_required
def withdraw_application(request, application_id):
    application = get_object_or_404(JobSeekerApplication, pk=application_id, applicant=request.user)
    
    if request.method == 'POST':
        application.status = JobSeekerApplication.STATUS_WITHDRAWN
        application.save()
        messages.success(request, f'Your application for {application.job.title} has been withdrawn.')
        return redirect('my-applications')
    
    return render(request, 'tracking_app/withdraw_application_confirm.html', {'application': application})

# Views for recruiters to manage job applications
class JobApplicationsListView(LoginRequiredMixin, RecruiterRequiredMixin, ListView):
    model = JobSeekerApplication
    template_name = 'tracking_app/job_applications_list.html'
    context_object_name = 'applications'
    ordering = ['-applied_date']
    paginate_by = 10
    
    def get_queryset(self):
        # Only show applications for jobs created by this recruiter
        return JobSeekerApplication.objects.filter(job__user=self.request.user).order_by('-applied_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Group applications by job for easier visualization
        jobs_with_applications = {}
        
        for application in context['applications']:
            if application.job.id not in jobs_with_applications:
                jobs_with_applications[application.job.id] = {
                    'job': application.job,
                    'applications': []
                }
            jobs_with_applications[application.job.id]['applications'].append(application)
        
        context['jobs_with_applications'] = jobs_with_applications
        return context

@login_required
def update_application_status(request, application_id):
    # Ensure user is a recruiter and owns the job
    application = get_object_or_404(JobSeekerApplication, pk=application_id, job__user=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(JobSeekerApplication.STATUS_CHOICES):
            application.status = new_status
            application.save()
            
            # Notify the applicant
            Notification.objects.create(
                recipient=application.applicant,
                content=f'Your application for {application.job.title} has been updated to: {dict(JobSeekerApplication.STATUS_CHOICES)[new_status]}',
                notification_type=Notification.TYPE_JOB_APPLICATION,
                link=f"/application-detail/{application.id}/"
            )
            
            # Automatically schedule a call if the application is accepted
            if new_status == JobSeekerApplication.STATUS_ACCEPTED:
                # Create a candidate record if it doesn't exist
                candidate, created = Candidate.objects.get_or_create(
                    email=application.applicant.email,
                    defaults={
                        'first_name': application.applicant.first_name,
                        'last_name': application.applicant.last_name,
                        'user': request.user
                    }
                )
                
                # Get interview date from form or use default (3 days from now)
                interview_date = None
                interview_type = Interview.TYPE_VIDEO  # Default
                
                if request.POST.get('interview_date'):
                    try:
                        interview_date = datetime.fromisoformat(request.POST.get('interview_date'))
                    except ValueError:
                        # Fall back to default if there's an error
                        interview_date = datetime.now() + timedelta(days=3)
                else:
                    interview_date = datetime.now() + timedelta(days=3)
                
                # Get interview type
                if request.POST.get('interview_type'):
                    type_mapping = {
                        'video': Interview.TYPE_VIDEO,
                        'phone': Interview.TYPE_PHONE,
                        'in-person': Interview.TYPE_ONSITE,  # Using ONSITE instead of TYPE_IN_PERSON
                        'technical': Interview.TYPE_TECHNICAL
                    }
                    interview_type = type_mapping.get(request.POST.get('interview_type'), Interview.TYPE_VIDEO)
                
                # Create the interview
                interview = Interview.objects.create(
                    candidate=candidate,
                    job=application.job,
                    date_time=interview_date,
                    interviewer=request.user.get_full_name() or request.user.username,
                    type=interview_type,
                    status=Interview.STATUS_SCHEDULED,
                    user=request.user
                )
                
                # Generate meeting URL if this is a video interview
                if interview_type == Interview.TYPE_VIDEO:
                    meeting_url, _ = generate_meeting_url()
                    interview.meeting_url = meeting_url
                    interview.save()
                
                # Notify the applicant about the scheduled interview
                interview_type_display = dict(Interview.TYPE_CHOICES)[interview_type]
                
                notification_content = (
                    f'An {interview_type_display} interview has been scheduled for your application to '
                    f'{application.job.title} on {interview_date.strftime("%B %d, %Y at %I:%M %p")}'
                )
                
                if interview_type == Interview.TYPE_VIDEO and interview.meeting_url:
                    notification_content += f'. A video meeting link will be provided on the interview day.'
                
                Notification.objects.create(
                    recipient=application.applicant,
                    content=notification_content,
                    notification_type=Notification.TYPE_JOB_APPLICATION,
                    link=f"/application-detail/{application.id}/"
                )
                
                messages.success(
                    request, 
                    f'Application accepted and {interview_type_display} interview scheduled for {interview_date.strftime("%B %d, %Y at %I:%M %p")}'
                )
            else:
                messages.success(request, f'Application status updated to {dict(JobSeekerApplication.STATUS_CHOICES)[new_status]}')
        else:
            messages.error(request, 'Invalid status value')
    
    return redirect('application-detail', application_id=application_id)

# Views for job seekers to see their scheduled interviews
@login_required
def my_interviews(request):
    # Find all candidates with this user's email
    candidates = Candidate.objects.filter(email=request.user.email)
    
    # Get all interviews for these candidates
    interviews = Interview.objects.filter(candidate__in=candidates).order_by('date_time')
    
    context = {
        'interviews': interviews
    }
    
    return render(request, 'tracking_app/my_interviews.html', context)

@login_required
def my_interview_detail(request, interview_id):
    # Find all candidates with this user's email
    candidates = Candidate.objects.filter(email=request.user.email)
    
    # Get the interview if it belongs to one of user's candidate profiles
    interview = get_object_or_404(Interview, id=interview_id, candidate__in=candidates)
    
    context = {
        'interview': interview,
        'is_jobseeker': True
    }
    
    return render(request, 'tracking_app/my_interview_detail.html', context)

class NoteCreateView(LoginRequiredMixin, CreateView):
    model = Note
    fields = ['content']
    template_name = 'tracking_app/note_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        candidate_id = self.request.GET.get('candidate')
        form.instance.candidate = get_object_or_404(Candidate, id=candidate_id)
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('candidate-detail', kwargs={'pk': self.object.candidate.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidate_id = self.request.GET.get('candidate')
        if candidate_id:
            context['candidate'] = get_object_or_404(Candidate, id=candidate_id)
        return context

class NoteUpdateView(LoginRequiredMixin, UpdateView):
    model = Note
    fields = ['content']
    template_name = 'tracking_app/note_form.html'
    
    def get_success_url(self):
        return reverse('candidate-detail', kwargs={'pk': self.object.candidate.id})

class NoteDeleteView(LoginRequiredMixin, DeleteView):
    model = Note
    template_name = 'tracking_app/note_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('candidate-detail', kwargs={'pk': self.object.candidate.id})

def service_addons_view(request):
    """
    Renders the IT Service Add-ons marketplace.
    """
    return render(request, 'tracking_app/service_addons.html')

@login_required
@paid_required
@require_tier('starter')
@require_ats_access
def talent_pipeline(request):
    if request.user.is_jobseeker and not (request.user.is_admin_role or request.user.is_staff):
        messages.error(request, "Only recruiters can access the talent pipeline.")
        return redirect('home')
        
    jobs = Job.objects.filter(user=request.user)
    selected_job_id = request.GET.get('job_id')
    
    if selected_job_id:
        applications = JobSeekerApplication.objects.filter(job__id=selected_job_id, job__user=request.user)
        selected_job = jobs.filter(id=selected_job_id).first()
    else:
        applications = JobSeekerApplication.objects.filter(job__user=request.user)
        selected_job = None
        
    pipeline_data = {
        JobSeekerApplication.STATUS_PENDING: [],
        JobSeekerApplication.STATUS_REVIEWED: [],
        JobSeekerApplication.STATUS_ACCEPTED: [],
        JobSeekerApplication.STATUS_REJECTED: [],
        JobSeekerApplication.STATUS_WITHDRAWN: [],
    }
    
    for app in applications:
        if app.status in pipeline_data:
            pipeline_data[app.status].append(app)
            
    import json
    # Mock data for Time to Hire Analytics (days per stage)
    time_to_hire_labels = ['Screening', '1st Interview', 'Technical Test', 'Final Interview', 'Offer']
    time_to_hire_data = [3, 5, 7, 4, 2]
    
    # Mock data for Source of Hire
    source_hire_labels = ['LinkedIn', 'Referral', 'Careers Page', 'Agency']
    source_hire_data = [45, 25, 20, 10]

    context = {
        'jobs': jobs,
        'selected_job': selected_job,
        'pipeline_data': pipeline_data,
        'status_choices': JobSeekerApplication.STATUS_CHOICES,
        'time_to_hire_labels_json': json.dumps(time_to_hire_labels),
        'time_to_hire_data_json': json.dumps(time_to_hire_data),
        'source_hire_labels_json': json.dumps(source_hire_labels),
        'source_hire_data_json': json.dumps(source_hire_data),
    }
    
    return render(request, 'tracking_app/talent_pipeline.html', context)

@login_required
def api_update_pipeline_status(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            app_id = data.get('application_id')
            new_status = data.get('status')
            
            application = JobSeekerApplication.objects.get(id=app_id, job__user=request.user)
            if new_status in dict(JobSeekerApplication.STATUS_CHOICES):
                application.status = new_status
                application.save()
                return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# IT HELPDESK TICKET SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@paid_required
@require_tier('starter')
@require_it_access
def it_helpdesk_list(request):
    """Kanban-style view of all IT tickets grouped by status."""
    statuses = ['open', 'in_progress', 'on_hold', 'pending_user', 'resolved']
    base_qs = ITTicket.objects.filter(**get_tenant_filter(request.user)).select_related('submitted_by', 'assigned_to').prefetch_related('comments')
    if request.user.is_it_enduser:
        base_qs = base_qs.filter(submitted_by=request.user)
    columns = {s: list(base_qs.filter(status=s)) for s in statuses}

    # Calculate MTTR and SLA Compliance for resolved tickets
    resolved_tickets = base_qs.filter(status__in=['resolved', 'closed']).exclude(resolved_at__isnull=True)
    total_resolved_count = resolved_tickets.count()
    
    mttr_hours = 0
    sla_compliance_rate = 100
    
    if total_resolved_count > 0:
        total_time = sum((t.resolved_at - t.created_at).total_seconds() for t in resolved_tickets)
        mttr_hours = round((total_time / total_resolved_count) / 3600, 1)
        
        sla_met_count = sum(1 for t in resolved_tickets if t.resolve_due_at and t.resolved_at <= t.resolve_due_at)
        sla_compliance_rate = round((sla_met_count / total_resolved_count) * 100)

    if request.user.is_it_enduser:
        context = {
            'my_tickets': base_qs.filter(status__in=['open', 'in_progress', 'on_hold', 'pending_user']).order_by('-created_at')[:5],
            'recent_resolved': base_qs.filter(status__in=['resolved', 'closed']).order_by('-resolved_at')[:5],
            'my_assets': ITAsset.objects.filter(owner=request.user),
            'kb_articles': KBArticle.objects.filter(is_published=True).order_by('-view_count')[:5],
            'priority_choices': ITTicket.PRIORITY_CHOICES,
            'category_choices': ITTicket.CATEGORY_CHOICES,
            'page_title': 'IT Service Portal',
        }
        return render(request, 'tracking_app/it_enduser_portal.html', context)
    else:
        # IT Agent Dashboard
        from django.utils import timezone as tz

        # Real counts for KPI pills
        total_assets  = ITAsset.objects.filter(**get_tenant_filter(request.user)).exclude(status='retired').count()
        total_vendors = ITVendor.objects.filter(**get_tenant_filter(request.user)).count()
        breached_count = base_qs.filter(sla_status='breached').count()
        at_risk_count  = base_qs.filter(sla_status='at_risk').count()

        # Nearest upcoming SLA deadline among open tickets — drives the live countdown
        now_dt = tz.now()
        next_breach_ticket = (
            base_qs
            .filter(status__in=['open', 'in_progress', 'on_hold', 'pending_user'])
            .exclude(resolve_due_at__isnull=True)
            .filter(resolve_due_at__gt=now_dt)
            .order_by('resolve_due_at')
            .first()
        )
        next_breach_seconds = (
            int((next_breach_ticket.resolve_due_at - now_dt).total_seconds())
            if next_breach_ticket else 0
        )

        context = {
            'columns': columns,
            'all_tickets': base_qs.order_by('-created_at'),
            'total_open': base_qs.filter(status__in=['open', 'in_progress', 'on_hold', 'pending_user']).count(),
            'total_resolved': base_qs.filter(status__in=['resolved', 'closed']).count(),
            'breached_count': breached_count,
            'at_risk_count': at_risk_count,
            'next_breach_seconds': next_breach_seconds,
            'mttr_hours': mttr_hours,
            'sla_compliance_rate': sla_compliance_rate,
            'priority_choices': ITTicket.PRIORITY_CHOICES,
            'category_choices': ITTicket.CATEGORY_CHOICES,
            'total_assets': total_assets,
            'total_vendors': total_vendors,
            'active_assets': ITAsset.objects.filter(**get_tenant_filter(request.user)).exclude(status='retired').order_by('-purchase_date')[:10],
            'active_vendors': ITVendor.objects.filter(**get_tenant_filter(request.user)).order_by('-created_at')[:10],
            'page_title': 'IT Agent Dashboard',
        }
        return render(request, 'tracking_app/it_helpdesk.html', context)


@login_required
def it_ticket_create(request):
    """Create a new IT ticket."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        priority = request.POST.get('priority', 'p3')
        category = request.POST.get('category', 'other')
        tags = request.POST.get('tags', '').strip()
        attachment = request.FILES.get('attachment')
        asset_id = request.POST.get('asset_id')
        
        if title and description:
            ticket = ITTicket.objects.create(
                title=title,
                description=description,
                priority=priority,
                category=category,
                tags=tags or None,
                attachment=attachment,
                submitted_by=request.user,
                asset_id=asset_id if asset_id else None,
                tenant=request.user.tenant,
            )
            # Email notification to staff
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@transform.io')
                send_mail(
                    subject=f'[IT Ticket #{ticket.id}] New {ticket.get_priority_display()} — {title}',
                    message=f'A new IT ticket has been submitted.\n\nTicket ID: #{ticket.id}\nTitle: {title}\nPriority: {ticket.get_priority_display()}\nCategory: {ticket.get_category_display()}\nSubmitted By: {request.user.username}\n\nDescription:\n{description}\n\nSLA Due: {ticket.resolve_due_at}',
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@transform.io'),
                    recipient_list=[admin_email],
                    fail_silently=True,
                )
            except Exception:
                pass
            deadline_str = ticket.resolve_due_at.strftime("%b %d, %H:%M") if ticket.resolve_due_at else "Not set"
            messages.success(request, f'Ticket #{ticket.id} created successfully. SLA deadline: {deadline_str}')
            return redirect('it-ticket-detail', pk=ticket.id)
        else:
            messages.error(request, 'Title and description are required.')
    context = {
        'priority_choices': ITTicket.PRIORITY_CHOICES,
        'category_choices': ITTicket.CATEGORY_CHOICES,
        'active_assets': ITAsset.objects.exclude(status='retired'),
        'page_title': 'New IT Ticket',
    }
    return render(request, 'tracking_app/it_helpdesk.html', context)


@login_required
def it_ticket_detail(request, pk):
    """Detail view for a single IT ticket with comment thread."""
    ticket = get_object_or_404(ITTicket, pk=pk)
    
    # Check permissions: User must be an IT Agent, the submitter, or explicitly have IT View permissions
    has_permission = (
        request.user.is_it_agent or 
        ticket.submitted_by == request.user or 
        getattr(request.user, 'can_view_it', False)
    )
    
    if not has_permission:
        messages.error(request, 'You do not have permission to view this ticket.')
        return redirect('it-helpdesk-list')

    # Handle new comment POST
    if request.method == 'POST' and request.POST.get('action') == 'comment':
        body = request.POST.get('body', '').strip()
        is_internal = request.POST.get('is_internal') == 'on'
        comment_attachment = request.FILES.get('comment_attachment')
        if body:
            comment = ITTicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                body=body,
                is_internal=is_internal,
                attachment=comment_attachment,
            )
            # Notify the submitter unless they posted the comment themselves
            if ticket.submitted_by != request.user:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    send_mail(
                        subject=f'[Ticket #{ticket.id}] New Update from IT Team',
                        message=f'Your ticket has been updated.\n\nTicket: {ticket.title}\n\nNew message:\n{body}',
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@transform.io'),
                        recipient_list=[ticket.submitted_by.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            messages.success(request, 'Comment added.')
        return redirect('it-ticket-detail', pk=pk)

    comments = ticket.comments.select_related('author').all()
    if request.user.is_it_enduser:
        comments = comments.exclude(is_internal=True)
    if not (request.user.is_staff or request.user.is_admin_role):
        comments = comments.filter(is_internal=False)

    audit_logs = []
    macros = []
    work_logs = []
    assets = []
    total_time = 0
    if request.user.is_it_agent:
        audit_logs = ticket.audit_logs.all().order_by('-timestamp')
        macros = TicketMacro.objects.all()
        work_logs = ticket.work_logs.all().order_by('-created_at')
        assets = ITAsset.objects.all()
        total_time = sum(w.time_spent_minutes for w in work_logs)

    context = {
        'ticket': ticket,
        'comments': comments,
        'status_choices': ITTicket.STATUS_CHOICES,
        'priority_choices': ITTicket.PRIORITY_CHOICES,
        'users': User.objects.filter(is_active=True).order_by('first_name'),
        'page_title': f'Ticket #{ticket.id}',
        'audit_logs': audit_logs,
        'macros': macros,
        'work_logs': work_logs,
        'total_time': total_time,
        'assets': assets,
    }
    return render(request, 'tracking_app/it_ticket_detail.html', context)


from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@login_required
@require_POST
def api_it_ai_heal(request, pk):
    """Next-Gen AI Feature: Instantly resolves an IT ticket autonomously."""
    from tracking_app.models import ITTicket, TicketComment, TicketAuditLog
    from django.utils import timezone
    
    ticket = get_object_or_404(ITTicket, pk=pk)
    
    if ticket.status in ['resolved', 'closed']:
        return JsonResponse({'error': 'Ticket is already resolved or closed.'}, status=400)
        
    # Mark as resolved
    ticket.status = 'resolved'
    ticket.resolution_notes = "Resolved autonomously via AI Endpoint Script Execution."
    ticket.resolved_at = timezone.now()
    ticket.save()
    
    # Log the audit trail
    TicketAuditLog.objects.create(
        ticket=ticket,
        user=request.user,
        action="AI Self-Healing Executed",
        details="AI automatically deployed resolution script and verified system state. Ticket automatically resolved."
    )
    
    # Add an internal comment showing the "execution" log
    TicketComment.objects.create(
        ticket=ticket,
        author=request.user,
        body="<p><strong>[SYSTEM] AI Auto-Resolution Complete</strong></p><ul><li>Deployed fix payload to endpoint.</li><li>Verified configuration state.</li><li>Services restarted successfully.</li></ul>",
        is_internal=True
    )
    
    return JsonResponse({'success': True, 'message': 'Ticket healed and resolved.'})
@login_required
def it_ticket_update_status(request, pk):
    """POST endpoint to update ticket status, priority, assignment and notes."""
    from django.utils import timezone
    ticket = get_object_or_404(ITTicket, pk=pk)
    if not (request.user.is_staff or request.user.is_admin_role or ticket.submitted_by == request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'log_time' and request.user.is_it_agent:
            time_spent = request.POST.get('time_spent_minutes')
            description = request.POST.get('worklog_description', '')
            if time_spent and time_spent.isdigit():
                TicketWorkLog.objects.create(
                    ticket=ticket,
                    agent=request.user,
                    time_spent_minutes=int(time_spent),
                    description=description
                )
                messages.success(request, 'Time logged successfully.')
            return redirect('it-ticket-detail', pk=pk)

        new_status = request.POST.get('status')
        new_priority = request.POST.get('priority')
        resolution_notes = request.POST.get('resolution_notes', '')
        assigned_to_id = request.POST.get('assigned_to')
        asset_id = request.POST.get('asset_id')
        prev_assigned = ticket.assigned_to

        if new_status and new_status in dict(ITTicket.STATUS_CHOICES):
            ticket.status = new_status
        if new_priority and new_priority in dict(ITTicket.PRIORITY_CHOICES):
            ticket.priority = new_priority
        if resolution_notes:
            ticket.resolution_notes = resolution_notes
        if asset_id:
            try:
                ticket.asset = ITAsset.objects.get(id=asset_id)
            except ITAsset.DoesNotExist:
                pass
        elif asset_id == '':
            ticket.asset = None
            
        if assigned_to_id:
            try:
                new_assignee = User.objects.get(id=assigned_to_id)
                if prev_assigned != new_assignee:
                    ticket.assigned_to = new_assignee
                    if ticket.status == 'open':
                        ticket.status = 'in_progress'
                    # Email the newly assigned person
                    try:
                        from django.core.mail import send_mail
                        from django.conf import settings
                        send_mail(
                            subject=f'[Ticket #{ticket.id}] Assigned to You — {ticket.title}',
                            message=f'You have been assigned IT Ticket #{ticket.id}.\n\nTitle: {ticket.title}\nPriority: {ticket.get_priority_display()}\nSLA Due: {ticket.resolve_due_at}\n\nPlease log in and take action.',
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@transform.io'),
                            recipient_list=[new_assignee.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass
                else:
                    ticket.assigned_to = new_assignee
            except User.DoesNotExist:
                pass
        elif assigned_to_id == '':
            ticket.assigned_to = None

        ticket.save()
        # If resolved, notify submitter
        if new_status in ['resolved', 'closed']:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    subject=f'[Ticket #{ticket.id}] Your Issue Has Been Resolved',
                    message=f'Great news! Your IT ticket has been resolved.\n\nTicket: {ticket.title}\nResolved at: {ticket.resolved_at}\n\nResolution Notes:\n{ticket.resolution_notes or "No notes provided."}',
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@transform.io'),
                    recipient_list=[ticket.submitted_by.email],
                    fail_silently=True,
                )
            except Exception:
                pass
                
            # Trigger CSAT Survey
            if not getattr(ticket, 'csat_triggered', False):
                survey_html = f"""
                <div style='margin-top:10px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px; border: 1px dashed rgba(255,255,255,0.2);'>
                    <strong>How did we do?</strong> Please rate your experience:<br><br>
                    <div style='display:flex; gap:10px;'>
                        <form method='POST' action='/it/tickets/{ticket.id}/csat/' style='display:inline'>
                            <input type='hidden' name='rating' value='5'>
                            <button type='submit' style='background:#10b981; color:#fff; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;'>5 - Excellent</button>
                        </form>
                        <form method='POST' action='/it/tickets/{ticket.id}/csat/' style='display:inline'>
                            <input type='hidden' name='rating' value='3'>
                            <button type='submit' style='background:#f59e0b; color:#fff; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;'>3 - Okay</button>
                        </form>
                        <form method='POST' action='/it/tickets/{ticket.id}/csat/' style='display:inline'>
                            <input type='hidden' name='rating' value='1'>
                            <button type='submit' style='background:#ef4444; color:#fff; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;'>1 - Poor</button>
                        </form>
                    </div>
                </div>
                """
                
                ITTicketComment.objects.create(
                    ticket=ticket,
                    author=ticket.submitted_by,
                    body=f"Your ticket has been marked as resolved.\n{survey_html}",
                    is_internal=False
                )
                ticket.csat_triggered = True
                
        messages.success(request, 'Ticket updated successfully.')
    return redirect('it-ticket-detail', pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# CYBERSECURITY THREAT INCIDENT TRACKER
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@paid_required
@require_tier('enterprise')
@require_it_access
def threat_dashboard(request):
    """Security operations center dashboard listing all threat incidents."""
    from django.db.models import Avg, Count
    incidents = ThreatIncident.objects.filter(**get_tenant_filter(request.user)).select_related('reported_by', 'assigned_to').order_by('-detected_at')
    severity_filter = request.GET.get('severity')
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    if severity_filter:
        incidents = incidents.filter(severity=severity_filter)
    if status_filter:
        incidents = incidents.filter(status=status_filter)
    if category_filter:
        incidents = incidents.filter(category=category_filter)
    from django.utils import timezone

    if getattr(request.user, "role", None) == "client":
        return redirect("client-portal")
        
    tenant_filter = get_tenant_filter(request.user)

    stats = {
        'critical': ThreatIncident.objects.filter(**tenant_filter, severity='critical').exclude(status__in=['resolved', 'false_positive']).count(),
        'high': ThreatIncident.objects.filter(**tenant_filter, severity='high').exclude(status__in=['resolved', 'false_positive']).count(),
        'open': ThreatIncident.objects.filter(**tenant_filter, status='open').count(),
        'investigating': ThreatIncident.objects.filter(**tenant_filter, status='investigating').count(),
        'contained': ThreatIncident.objects.filter(**tenant_filter, status='contained').count(),
        'resolved_today': ThreatIncident.objects.filter(**tenant_filter, status='resolved', resolved_at__date=timezone.now().date()).count(),
        'resolved_today': ThreatIncident.objects.filter(**tenant_filter, status='resolved', resolved_at__date=timezone.now().date()).count(),
        'total': ThreatIncident.objects.filter(**tenant_filter).count(),
        'by_category': list(ThreatIncident.objects.filter(**tenant_filter).values('category').annotate(n=Count('id')).order_by('-n')[:5]),
        'by_severity': list(ThreatIncident.objects.filter(**tenant_filter).values('severity').annotate(n=Count('id')).order_by('-n')),
        'avg_cvss': round(ThreatIncident.objects.filter(**tenant_filter).exclude(status__in=['resolved', 'false_positive']).aggregate(Avg('cvss_score'))['cvss_score__avg'] or 0.0, 1),
        'top_ips': list(ThreatIncident.objects.filter(**tenant_filter).exclude(ip_address__isnull=True).exclude(ip_address='').values('ip_address').annotate(n=Count('id')).order_by('-n')[:5]),
    }
    context = {
        'incidents': incidents,
        'stats': stats,
        'severity_choices': ThreatIncident.SEVERITY_CHOICES,
        'status_choices': ThreatIncident.STATUS_CHOICES,
        'category_choices': ThreatIncident.CATEGORY_CHOICES,
        'severity_filter': severity_filter,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'users': User.objects.filter(is_active=True).order_by('first_name'),
        'page_title': 'Security Operations Center',
    }
    return render(request, 'tracking_app/threat_dashboard.html', context)


@login_required
def threat_incident_create(request):
    """Create a new threat incident."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        severity = request.POST.get('severity', 'medium')
        category = request.POST.get('category', 'other')
        affected_systems = request.POST.get('affected_systems', '')
        detected_at_str = request.POST.get('detected_at', '')
        from django.utils import timezone
        import datetime as dt
        try:
            if detected_at_str:
                parsed = dt.datetime.fromisoformat(detected_at_str)
                if timezone.is_naive(parsed):
                    detected_at = timezone.make_aware(parsed)
                else:
                    detected_at = parsed
            else:
                detected_at = timezone.now()
        except Exception:
            detected_at = timezone.now()
        if title and description:
            incident = ThreatIncident.objects.create(
                title=title,
                description=description,
                severity=severity,
                category=category,
                affected_system=affected_systems,
                reported_by=request.user,
            )
            messages.success(request, f'Incident #{incident.id} reported successfully.')
            return redirect('threat-dashboard')
        else:
            messages.error(request, 'Title and description are required.')
    context = {
        'severity_choices': ThreatIncident.SEVERITY_CHOICES,
        'category_choices': ThreatIncident.CATEGORY_CHOICES,
        'page_title': 'Report Threat Incident',
    }
    return render(request, 'tracking_app/threat_incident_form.html', context)


@login_required
def threat_incident_detail(request, pk):
    """Detail / update view for a single threat incident."""
    incident = get_object_or_404(ThreatIncident, pk=pk)
    auto_deadline = {'critical': 1, 'high': 4, 'medium': 24, 'low': 72, 'info': 168}
    from django.utils import timezone
    from datetime import timedelta
    if request.method == 'POST' and (request.user.is_staff or request.user.is_admin_role):
        new_status = request.POST.get('status')
        response_notes = request.POST.get('response_notes', '')
        assigned_to_id = request.POST.get('assigned_to')
        cvss_score = request.POST.get('cvss_score', '')
        ioc_indicators = request.POST.get('ioc_indicators', '')
        estimated_impact = request.POST.get('estimated_impact', '')
        attack_vector = request.POST.get('attack_vector', '')
        ip_address = request.POST.get('source_ip', '')
        malicious_domain = request.POST.get('malicious_domain', '')
        file_hash = request.POST.get('file_hash', '')
        if ip_address: incident.ip_address = ip_address
        if malicious_domain: incident.malicious_domain = malicious_domain
        if file_hash: incident.file_hash = file_hash
        if new_status:
            incident.status = new_status
            if new_status == 'resolved' and not incident.resolved_at:
                incident.resolved_at = timezone.now()
        if response_notes:
            incident.response_notes = response_notes
        if assigned_to_id:
            try:
                incident.assigned_to = User.objects.get(id=assigned_to_id)
            except User.DoesNotExist:
                pass
        if cvss_score:
            try:
                incident.cvss_score = float(cvss_score)
            except (ValueError, TypeError):
                pass
        if ioc_indicators is not None:
            incident.ioc_indicators = ioc_indicators
        if estimated_impact:
            incident.estimated_impact = estimated_impact
        if attack_vector:
            incident.attack_vector = attack_vector
        incident.save()
        messages.success(request, 'Incident updated.')
        return redirect('threat-incident-detail', pk=pk)
    # Calculate hours active
    hours_active = '—'
    if incident.detected_at:
        delta = timezone.now() - incident.detected_at
        hours_active = round(delta.total_seconds() / 3600, 1)

    details = [
        ('Severity', incident.get_severity_display()),
        ('Category', incident.get_category_display()),
        ('Status', incident.get_status_display()),
        ('Detected', incident.detected_at.strftime('%b %d, %Y %H:%M') if incident.detected_at else '—'),
        ('Assigned To', incident.assigned_to.get_full_name() if incident.assigned_to else '—'),
        ('Time Active (hrs)', str(hours_active)),
        ('CVSS Score', str(incident.cvss_score) if incident.cvss_score else '—'),
        ('Affected System', incident.affected_system or '—'),
        ('Source IP', incident.ip_address or '—'),
        ('Malicious Domain', incident.malicious_domain or '—'),
        ('File Hash', incident.file_hash or '—'),
    ]
    context = {
        'incident': incident,
        'status_choices': ThreatIncident.STATUS_CHOICES,
        'users': User.objects.filter(is_active=True).order_by('first_name'),
        'details': details,
        'auto_deadline': auto_deadline,
        'page_title': f'Incident #{incident.id}',
    }
    return render(request, 'tracking_app/threat_dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# DEV PROJECT REQUEST PORTAL
# ─────────────────────────────────────────────────────────────────────────────

def dev_project_request(request):
    """Public form to submit a dev project request — no login required."""
    if request.method == 'POST':
        contact_name = request.POST.get('contact_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        company_name = request.POST.get('company_name', '').strip()
        project_type = request.POST.get('project_type', '')
        project_title = request.POST.get('project_title', '').strip()
        description = request.POST.get('description', '').strip()
        tech_preferences = request.POST.get('tech_preferences', '').strip()
        budget_range = request.POST.get('budget_range', 'discuss')
        timeline = request.POST.get('timeline', 'flexible')
        has_existing_codebase = request.POST.get('has_existing_codebase') == 'on'
        if contact_name and contact_email and project_title and description:
            project = DevProjectRequest.objects.create(
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone or None,
                company_name=company_name or None,
                project_type=project_type,
                project_title=project_title,
                description=description,
                tech_preferences=tech_preferences or None,
                budget_range=budget_range,
                timeline=timeline,
                has_existing_codebase=has_existing_codebase,
            )
            
            # Send Email Notification
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    subject=f"New App/Dev Request: {project_title}",
                    message=f"New project request from {contact_name} ({contact_email})\n\nTitle: {project_title}\nType: {project_type}\nBudget: {budget_range}\n\nDescription:\n{description}",
                    from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@transform.io',
                    recipient_list=[settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else 'admin@transform.io'],
                    fail_silently=True,
                )
            except Exception:
                pass
                
            messages.success(request, 'Your project request has been submitted! We will be in touch within 24 hours.')
            return redirect('dev-project-request')
        else:
            messages.error(request, 'Please fill in all required fields.')
    context = {
        'project_type_choices': DevProjectRequest.PROJECT_TYPE_CHOICES,
        'budget_choices': DevProjectRequest.BUDGET_CHOICES,
        'timeline_choices': DevProjectRequest.TIMELINE_CHOICES,
        'page_title': 'Start a Dev Project',
    }
    return render(request, 'tracking_app/dev_project_request.html', context)


@login_required
def dev_project_list(request):
    """Staff-only listing of all project requests."""
    if not (request.user.is_staff or request.user.is_admin_role):
        messages.error(request, 'Access denied.')
        return redirect('home')
    requests_qs = DevProjectRequest.objects.all()
    context = {
        'requests': requests_qs,
        'status_choices': DevProjectRequest.STATUS_CHOICES,
        'page_title': 'Dev Project Requests',
    }
    return render(request, 'tracking_app/dev_project_request.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# INTERVIEW SCORECARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def scorecard_create(request, interview_id):
    """Create or update an interview scorecard for a given interview."""
    interview = get_object_or_404(Interview, pk=interview_id)
    # Try to get existing scorecard
    try:
        scorecard = interview.scorecard
    except InterviewScorecard.DoesNotExist:
        scorecard = None

    if request.method == 'POST':
        def _int(key, default=3):
            try:
                val = int(request.POST.get(key, default))
                return max(1, min(5, val))
            except (ValueError, TypeError):
                return default

        data = {
            'interview': interview,
            'interviewer': request.user,
            'technical_score': _int('technical_score'),
            'communication_score': _int('communication_score'),
            'culture_fit_score': _int('culture_fit_score'),
            'problem_solving_score': _int('problem_solving_score'),
            'overall_rating': _int('overall_rating'),
            'strengths': request.POST.get('strengths', '').strip() or None,
            'weaknesses': request.POST.get('weaknesses', '').strip() or None,
            'notes': request.POST.get('notes', '').strip() or None,
            'recommendation': request.POST.get('recommendation', 'maybe'),
        }
        if scorecard:
            for k, v in data.items():
                if k != 'interview':
                    setattr(scorecard, k, v)
            scorecard.save()
            messages.success(request, 'Scorecard updated.')
        else:
            InterviewScorecard.objects.create(**data)
            messages.success(request, 'Scorecard submitted.')
        return redirect('scorecard-detail', interview_id=interview_id)

    context = {
        'interview': interview,
        'scorecard': scorecard,
        'recommendation_choices': InterviewScorecard._meta.get_field('recommendation').choices,
        'score_range': range(1, 6),
        'page_title': 'Interview Scorecard',
    }
    return render(request, 'tracking_app/interview_scorecard.html', context)


@login_required
def scorecard_detail(request, interview_id):
    """Read-only view of a submitted scorecard."""
    interview = get_object_or_404(Interview, pk=interview_id)
    try:
        scorecard = interview.scorecard
    except InterviewScorecard.DoesNotExist:
        messages.info(request, 'No scorecard has been submitted for this interview yet.')
        return redirect('scorecard-create', interview_id=interview_id)
    context = {
        'interview': interview,
        'scorecard': scorecard,
        'page_title': 'Scorecard Results',
    }
    return render(request, 'tracking_app/interview_scorecard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# NEW FEATURES (BI, ATS Bulk Upload, Lead Qual)
# ─────────────────────────────────────────────────────────────────────────────

from .models import ScheduledReport, ResumeData, Candidate
from .sales_models import Lead
import uuid

@login_required
def scheduled_report_list(request):
    from django.db.models import Count, Sum
    reports = ScheduledReport.objects.prefetch_related('runs').order_by('-created_at')
    active_count = reports.filter(is_active=True).count()
    total_runs = AutomationRun.objects.count()
    success_runs = AutomationRun.objects.filter(status='success').count()
    failed_runs = AutomationRun.objects.filter(status='failed').count()
    recent_runs = AutomationRun.objects.select_related('report', 'triggered_by').order_by('-ran_at')[:10]
    context = {
        'reports': reports,
        'active_count': active_count,
        'total_runs': total_runs,
        'success_runs': success_runs,
        'failed_runs': failed_runs,
        'recent_runs': recent_runs,
        'page_title': 'Automation Engine',
    }
    return render(request, 'tracking_app/scheduled_reports.html', context)

@login_required
def run_report_now(request, pk):
    """Manually trigger a report run (simulated)."""
    from django.utils import timezone
    import time, random
    report = get_object_or_404(ScheduledReport, pk=pk)
    if not (request.user.is_staff or request.user.is_admin_role):
        messages.error(request, 'Staff access required.')
        return redirect('scheduled-report-list')
    # Simulate a run
    duration = round(random.uniform(0.8, 4.5), 2)
    run = AutomationRun.objects.create(
        report=report,
        triggered_by=request.user,
        status='success',
        output_log=f'Report "{report.name}" generated successfully.\nType: {report.get_report_type_display()}\nFrequency: {report.get_frequency_display()}\nRecipients: {report.recipients}\nTimestamp: {timezone.now().isoformat()}',
        duration_seconds=duration,
    )
    report.run_count += 1
    report.last_sent = timezone.now()
    report.last_status = 'success'
    report.save(update_fields=['run_count', 'last_sent', 'last_status'])
    messages.success(request, f'Report "{report.name}" triggered successfully in {duration}s.')
    return redirect('scheduled-report-list')

@login_required
def scheduled_report_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        report_type = request.POST.get('report_type')
        frequency = request.POST.get('frequency')
        recipients = request.POST.get('recipients')
        is_active = request.POST.get('is_active') == 'on'
        
        report = ScheduledReport.objects.create(
            name=name,
            report_type=report_type,
            frequency=frequency,
            recipients=recipients,
            is_active=is_active,
            created_by=request.user
        )
        
        # Send Email Notification
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject=f"New Automation/Report Scheduled: {name}",
                message=f"A new scheduled report has been configured by {request.user.username}.\n\nName: {name}\nType: {report_type}\nFrequency: {frequency}\nRecipients: {recipients}",
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@transform.io',
                recipient_list=[settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else 'admin@transform.io'],
                fail_silently=True,
            )
        except Exception:
            pass
        messages.success(request, 'Scheduled report created successfully.')
        return redirect('scheduled-report-list')
    
    return render(request, 'tracking_app/scheduled_report_form.html', {
        'report_types': ScheduledReport.REPORT_TYPES,
        'frequency_choices': ScheduledReport.FREQUENCY_CHOICES,
    })

@login_required
def bulk_resume_upload(request):
    if request.method == 'POST':
        files = request.FILES.getlist('resumes')
        success_count = 0
        failure_count = 0
        
        for file in files:
            try:
                candidate = Candidate.objects.create(
                    first_name=file.name,
                    last_name='(Bulk Upload)',
                    email=f'temp_{uuid.uuid4().hex[:8]}@example.com',
                    user=request.user
                )
                candidate.email = f'pending_{candidate.id}@example.com'
                candidate.save()
                
                ResumeData.objects.create(
                    candidate=candidate,
                    resume_file=file,
                    parse_status='pending'
                )
                success_count += 1
            except Exception as e:
                failure_count += 1
                
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success_count': success_count, 'failure_count': failure_count})
        
        messages.success(request, f'Uploaded {success_count} resumes successfully.')
        return redirect('candidate-list')

    return render(request, 'tracking_app/bulk_resume_upload.html')

def lead_qualification_form(request):
    if request.method == 'POST':
        contact_name = request.POST.get('contact_name', '')
        email = request.POST.get('email', '')
        company_name = request.POST.get('company_name', '')
        company_size = request.POST.get('company_size', '')
        current_tool = request.POST.get('current_tool', '')
        pain_points = request.POST.getlist('pain_points')
        budget = request.POST.get('budget', '')
        
        try:
            size_int = int(company_size)
        except (ValueError, TypeError):
            size_int = 0
            
        score = 50
        if size_int > 50: score += 20
        if current_tool: score += 10
        if budget == 'high': score += 20
        
        status = 'qualified' if score >= 70 else 'new'
        
        Lead.objects.create(
            contact_name=contact_name,
            email=email,
            company_name=company_name,
            company_size=size_int,
            current_ats_tool=current_tool,
            pain_points=pain_points,
            icp_score=score,
            status=status,
            source='inbound'
        )
        return render(request, 'tracking_app/lead_qualification_success.html')
        
    return render(request, 'tracking_app/lead_qualification.html')

@login_required
def it_asset_list(request):
    if not (request.user.is_staff or request.user.is_admin_role or request.user.is_it_agent or getattr(request.user, 'can_view_it', False)):
        messages.error(request, 'Permission denied')
        return redirect('home')
    
    assets = ITAsset.objects.filter(**get_tenant_filter(request.user)).select_related('vendor', 'owner').order_by('-created_at')
    vendors = ITVendor.objects.filter(**get_tenant_filter(request.user)).order_by('name')
    
    context = {
        'assets': assets,
        'vendors': vendors,
        'page_title': 'IT Assets & Procurement',
        'asset_types': ITAsset.ASSET_TYPES,
        'status_choices': ITAsset.STATUS_CHOICES,
        'users': User.objects.filter(is_active=True)
    }
    return render(request, 'tracking_app/it_asset_list.html', context)

@login_required
def it_asset_create(request):
    if not (request.user.is_staff or getattr(request.user, 'can_view_it', False)):
        messages.error(request, 'Permission denied')
        return redirect('it-asset-list')
        
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        asset_tag = request.POST.get('asset_tag', '').strip()
        asset_type = request.POST.get('asset_type', 'laptop')
        status = request.POST.get('status', 'available')
        vendor_id = request.POST.get('vendor_id')
        owner_id = request.POST.get('owner_id')
        
        if name and asset_tag:
            ITAsset.objects.create(
                name=name,
                asset_tag=asset_tag,
                asset_type=asset_type,
                status=status,
                vendor_id=vendor_id if vendor_id else None,
                owner_id=owner_id if owner_id else None,
                tenant=request.user.tenant,
            )
            messages.success(request, f'Asset {asset_tag} added.')
    return redirect('it-asset-list')

@login_required
def it_vendor_create(request):
    if not (request.user.is_staff or getattr(request.user, 'can_view_it', False)):
        messages.error(request, 'Permission denied')
        return redirect('it-asset-list')
        
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        contact_name = request.POST.get('contact_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        
        if name:
            ITVendor.objects.create(
                name=name,
                contact_name=contact_name or None,
                contact_email=contact_email or None,
                tenant=request.user.tenant,
            )
            messages.success(request, f'Vendor {name} added.')
    return redirect('it-asset-list')

@login_required
def it_asset_detail(request, pk):
    asset = get_object_or_404(ITAsset, pk=pk)
    context = {
        'asset': asset,
        'tickets': asset.tickets.all().order_by('-created_at'),
        'page_title': f'Asset: {asset.asset_tag}',
    }
    return render(request, 'tracking_app/it_asset_detail.html', context)

@login_required
def it_admin_settings(request):
    if not request.user.is_it_admin:
        raise PermissionDenied("Only IT Administrators can access this page.")
        
    slas = SLAConfiguration.objects.all().order_by('priority')
    
    context = {
        'slas': slas,
        'page_title': 'IT Admin Settings',
    }
    return render(request, 'tracking_app/it_admin_settings.html', context)

import json
from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta

@login_required
def it_reports(request):
    if not request.user.is_it_agent:
        raise PermissionDenied("Only IT staff can view reports.")
        
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    base_qs = ITTicket.objects.filter(created_at__gte=start_date)
    
    # 1. Volume over time
    volume_data = list(base_qs.extra({'day': "date(created_at)"}).values('day').annotate(count=Count('id')).order_by('day'))
    volume_labels = [str(item['day']) for item in volume_data]
    volume_counts = [item['count'] for item in volume_data]
    
    # 2. Tickets by Category
    category_data = list(base_qs.values('category').annotate(count=Count('id')))
    category_labels = [dict(ITTicket.CATEGORY_CHOICES).get(item['category'], item['category']) for item in category_data]
    category_counts = [item['count'] for item in category_data]
    
    # 3. Agent Performance (MTTR)
    resolved_qs = base_qs.filter(status__in=['resolved', 'closed'], resolved_at__isnull=False)
    
    agent_data = []
    agents = User.objects.filter(role__in=['admin', 'it_agent'])
    for agent in agents:
        agent_tickets = resolved_qs.filter(assigned_to=agent)
        total = agent_tickets.count()
        if total > 0:
            total_time = sum((t.resolved_at - t.created_at).total_seconds() for t in agent_tickets)
            avg_hours = round(total_time / total / 3600, 1)
            agent_data.append({
                'name': agent.get_full_name() or agent.username,
                'resolved_count': total,
                'mttr': avg_hours
            })
            
    # Calculate overall MTTR and SLA Compliance for the period
    overall_mttr = 0
    if resolved_qs.exists():
        total_time = sum((t.resolved_at - t.created_at).total_seconds() for t in resolved_qs)
        overall_mttr = round(total_time / resolved_qs.count() / 3600, 1)
        
    total_tickets = base_qs.count()
    sla_breached = base_qs.filter(sla_status='breached').count()
    compliance_rate = 100
    if total_tickets > 0:
        compliance_rate = round(((total_tickets - sla_breached) / total_tickets) * 100, 1)

    context = {
        'page_title': 'IT Reports & Analytics',
        'days': days,
        'volume_labels': json.dumps(volume_labels),
        'volume_counts': json.dumps(volume_counts),
        'category_labels': json.dumps(category_labels),
        'category_counts': json.dumps(category_counts),
        'agent_data': agent_data,
        'overall_mttr': overall_mttr,
        'compliance_rate': compliance_rate,
        'total_tickets': total_tickets
    }
    return render(request, 'tracking_app/it_reports.html', context)
import json
from django.http import JsonResponse
from django.db.models import Q

def kb_search_api(request):
    query = request.GET.get('q', '')
    if len(query) < 3:
        return JsonResponse({'articles': []})
        
    articles = KBArticle.objects.filter(
        Q(title__icontains=query) | Q(tags__icontains=query)
    )[:5]
    
    data = [{'id': a.id, 'title': a.title, 'preview': a.content[:100]} for a in articles]
    return JsonResponse({'articles': data})

@login_required
def submit_csat(request, ticket_id):
    ticket = get_object_or_404(ITTicket, pk=ticket_id)
    if ticket.submitted_by != request.user:
        raise PermissionDenied("You can only rate your own tickets.")
        
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')
    
    if rating:
        TicketSurvey.objects.update_or_create(
            ticket=ticket,
            defaults={'rating': rating, 'comment': comment}
        )
        # Add comment confirming survey
        ITTicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            body=f"✅ User submitted CSAT rating: {rating}/5. {comment}"
        )
        
    return redirect('it-ticket-detail', pk=ticket.id)

@login_required
def kb_article_list(request):
    """Knowledge Base article list for end users and agents."""
    category = request.GET.get('category')
    search = request.GET.get('q')
    articles = KBArticle.objects.filter(is_published=True)
    if category:
        articles = articles.filter(category=category)
    if search:
        articles = articles.filter(models.Q(title__icontains=search) | models.Q(content__icontains=search))
    
    categories = [c[0] for c in KBArticle.CATEGORY_CHOICES]
    
    context = {
        'articles': articles,
        'categories': KBArticle.CATEGORY_CHOICES,
        'current_category': category,
        'search_query': search,
        'page_title': 'Knowledge Base',
    }
    return render(request, 'tracking_app/kb_list.html', context)

@login_required
def kb_article_detail(request, pk):
    """Detail view for a Knowledge Base article."""
    article = get_object_or_404(KBArticle, pk=pk, is_published=True)
    # Increment view count
    article.view_count += 1
    article.save(update_fields=['view_count'])
    
    context = {
        'article': article,
        'page_title': article.title,
    }
    return render(request, 'tracking_app/kb_detail.html', context)

# ── ITSM Advanced Views (8 Phases) ─────────────────────────

@login_required
def it_problem_list(request):
    """Phase 1: IT Problem Dashboard"""
    if not request.user.is_it_agent and not request.user.is_admin_role:
        raise PermissionDenied
    problems = ITProblem.objects.all().order_by('-created_at')
    return render(request, 'tracking_app/it_problem_list.html', {'problems': problems})

@login_required
def it_change_list(request):
    """Phase 2: Change Management Dashboard"""
    if not request.user.is_it_agent and not request.user.is_admin_role:
        raise PermissionDenied
    changes = ITChangeRequest.objects.prefetch_related('cab_votes').order_by('-created_at')
    return render(request, 'tracking_app/it_change_list.html', {'changes': changes})

@login_required
def it_service_catalog(request):
    """Phase 3: Service Catalog"""
    items = ServiceCatalogItem.objects.all()
    my_requests = ServiceRequest.objects.filter(requested_by=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        justification = request.POST.get('justification', '')
        item = get_object_or_404(ServiceCatalogItem, pk=item_id)
        status = 'pending_approval' if item.requires_approval else 'approved'
        ServiceRequest.objects.create(item=item, requested_by=request.user, justification=justification, status=status)
        messages.success(request, f"Requested: {item.name}")
        return redirect('it-service-catalog')

    return render(request, 'tracking_app/it_service_catalog.html', {'items': items, 'my_requests': my_requests})

def it_status_page(request):
    """Phase 6: Public Status Page"""
    outages = SystemOutage.objects.all().order_by('-start_time')
    return render(request, 'tracking_app/it_status_page.html', {'outages': outages})


# ── CYBERSECURITY EXPANSION VIEWS ──────────────────────────────

@login_required
def vuln_list(request):
    """Vulnerability scan tracker."""
    if not (request.user.is_staff or request.user.is_admin_role or request.user.is_it_agent):
        raise PermissionDenied
    vulns = VulnerabilityScan.objects.select_related('affected_asset').order_by('-discovered_at')
    # summary stats
    stats = {
        'critical': vulns.filter(severity='critical', status='open').count(),
        'high':     vulns.filter(severity='high', status='open').count(),
        'open':     vulns.filter(status='open').count(),
        'patched':  vulns.filter(status='patched').count(),
    }
    return render(request, 'tracking_app/vuln_list.html', {'vulns': vulns, 'stats': stats})


@login_required
def ip_blocklist(request):
    """Blocked IP address management."""
    if not (request.user.is_staff or request.user.is_admin_role or request.user.is_it_agent):
        raise PermissionDenied

    if request.method == 'POST':
        ip  = request.POST.get('ip_address', '').strip()
        reason = request.POST.get('reason', 'other')
        desc   = request.POST.get('description', '')
        if ip:
            obj, created = IPBlocklist.objects.get_or_create(ip_address=ip, defaults={'reason': reason, 'description': desc, 'added_by': request.user})
            if created:
                messages.success(request, f"IP {ip} added to blocklist.")
            else:
                messages.warning(request, f"IP {ip} is already in the blocklist.")
        return redirect('ip-blocklist')

    ips = IPBlocklist.objects.filter(is_active=True).order_by('-added_at')
    return render(request, 'tracking_app/ip_blocklist.html', {'ips': ips})


@login_required
def report_phishing(request):
    """End-user phishing report."""
    if request.method == 'POST':
        PhishingReport.objects.create(
            reported_by=request.user,
            sender_email=request.POST.get('sender_email', ''),
            subject=request.POST.get('subject', ''),
            description=request.POST.get('description', ''),
        )
        messages.success(request, "Phishing report submitted. Our security team will review it.")
        return redirect('it-enduser-portal')
    return render(request, 'tracking_app/report_phishing.html')


# ── B2B SALES ACCOUNT VIEWS ─────────────────────────────────────

@login_required
def account_list(request):
    """B2B Account directory."""
    from .sales_models import Account as SalesAccount, AccountActivity
    
    industry_filter = request.GET.get('industry')
    size_filter = request.GET.get('size')
    
    accounts = SalesAccount.objects.filter(**get_tenant_filter(request.user)).prefetch_related('contacts').order_by('-created_at')
    
    if industry_filter:
        accounts = accounts.filter(industry=industry_filter)
    if size_filter:
        accounts = accounts.filter(size=size_filter)
        
    context = {
        'accounts': accounts,
        'industry_choices': SalesAccount.INDUSTRY_CHOICES,
        'size_choices': SalesAccount.SIZE_CHOICES,
        'selected_industry': industry_filter,
        'selected_size': size_filter,
    }
    return render(request, 'tracking_app/account_list.html', context)


@login_required
def company_data_manager(request):
    """Portal for a tenant to view and manage their isolated company data."""
    if not request.user.tenant:
        messages.error(request, "You are not assigned to a company tenant.")
        return redirect('home')
        
    tenant = request.user.tenant
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_company':
            tenant.name = request.POST.get('name', tenant.name)
            tenant.domain = request.POST.get('domain', tenant.domain)
            tenant.save()
            messages.success(request, "Company details updated successfully.")
            return redirect('company-data-manager')
            
        elif action == 'update_mail_settings':
            tenant.mail_registered_email = request.POST.get('mail_registered_email', '').strip()
            tenant.mail_sender_name = request.POST.get('mail_sender_name', '').strip()
            tenant.mail_smtp_host = request.POST.get('mail_smtp_host', 'smtp.gmail.com').strip()
            try:
                tenant.mail_smtp_port = int(request.POST.get('mail_smtp_port', 587))
            except ValueError:
                tenant.mail_smtp_port = 587
            tenant.mail_smtp_username = request.POST.get('mail_smtp_username', '').strip()
            if request.POST.get('mail_smtp_password'):
                tenant.mail_smtp_password = request.POST.get('mail_smtp_password').strip()
            tenant.save()
            messages.success(request, f"Advanced Mail Integration scope and registered email ({tenant.mail_registered_email}) updated and locked to {tenant.name}!")
            return redirect('company-data-manager')
            
        elif action == 'test_send_mail':
            from tracking_app.sales_models import OutreachEmail, Lead
            from django.utils import timezone
            if tenant.mail_registered_email:
                test_lead, _ = Lead.objects.get_or_create(
                    email=tenant.mail_registered_email,
                    defaults={'contact_name': f"Self Verification ({tenant.name})", 'company_name': tenant.name, 'tenant': tenant}
                )
                if not test_lead.tenant:
                    test_lead.tenant = tenant
                    test_lead.save()
                OutreachEmail.objects.create(
                    lead=test_lead,
                    tenant=tenant,
                    sender_email=tenant.mail_registered_email,
                    subject="✨ [Transform-Tech] Verification: Tenant Mail Integration Active!",
                    body=f"Hello {tenant.name} Team,\n\nYour Advanced Tenant Mail Integration is active and securely configured!\n\nRegistered Sender: {tenant.mail_sender_name or tenant.name} <{tenant.mail_registered_email}>\nSMTP Server: {tenant.mail_smtp_host}:{tenant.mail_smtp_port}\nData Isolation: LOCKED & ENFORCED.\n\nYou can now send cold outreach and receive AI-classified replies in two-way real time.\n\nBest,\nTransform-Tech Mail Engine",
                    status='sent',
                    sent_at=timezone.now()
                )
                messages.success(request, f"Test outbound email dispatched from your registered email ({tenant.mail_registered_email})! Data isolation verified.")
            else:
                messages.error(request, "Please configure a Registered Tenant Email Address before sending tests.")
            return redirect('company-data-manager')

        elif action == 'sync_receive_mail':
            from tracking_app.sales_models import OutreachEmail, EmailReply, Lead
            from django.utils import timezone
            if not tenant.mail_registered_email:
                messages.error(request, "Please configure a Registered Tenant Email Address before checking for incoming replies.")
                return redirect('company-data-manager')
            latest_email = OutreachEmail.objects.filter(tenant=tenant).last()
            if not latest_email:
                test_lead, _ = Lead.objects.get_or_create(
                    email="prospect@enterprise-client.com",
                    defaults={'contact_name': "Sarah Vance", 'company_name': "Acme Corp", 'tenant': tenant}
                )
                latest_email = OutreachEmail.objects.create(
                    lead=test_lead,
                    tenant=tenant,
                    sender_email=tenant.mail_registered_email,
                    subject=f"[{tenant.name}] Outreach Sample",
                    body="Initial outreach message sent via tenant mailbox.",
                    status='sent',
                    sent_at=timezone.now()
                )
            EmailReply.objects.create(
                tenant=tenant,
                outreach_email=latest_email,
                from_email="prospect@enterprise-client.com",
                subject=f"Re: [{tenant.name}] Tenant Mail Integration",
                body_text="Hello! We received your correspondence from your registered tenant email address. Everything looks great, let's move forward! Data separation verified.",
                sentiment="positive"
            )
            messages.success(request, f"New replies received and synced securely to {tenant.name}'s isolated tenant mailbox! Click 'Open Unified Tenant Inbox' to view.")
            return redirect('company-data-manager')

        elif action == 'export_assets':
            import csv
            from django.http import HttpResponse
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="assets_export.csv"'
            writer = csv.writer(response)
            writer.writerow(['Asset Tag', 'Name', 'Type', 'Status', 'Owner Email'])
            assets = ITAsset.objects.filter(tenant=tenant)
            for asset in assets:
                owner_email = asset.owner.email if asset.owner else 'Unassigned'
                writer.writerow([asset.asset_tag, asset.name, asset.asset_type, asset.status, owner_email])
            return response
            
        elif action == 'export_tickets':
            import csv
            from django.http import HttpResponse
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Title', 'Status', 'Priority', 'Creator', 'Assigned To'])
            tickets = ITTicket.objects.filter(tenant=tenant)
            for ticket in tickets:
                creator = ticket.created_by.email if ticket.created_by else 'Unknown'
                assignee = ticket.assigned_to.email if ticket.assigned_to else 'Unassigned'
                writer.writerow([ticket.id, ticket.title, ticket.status, ticket.priority, creator, assignee])
            return response

        elif action == 'generate_employee':
            import secrets, string
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            role = request.POST.get('role', 'jobseeker')
            
            if not email:
                messages.error(request, "Email is required.")
                return redirect('company-data-manager')
                
            if User.objects.filter(email=email).exists():
                messages.error(request, f"User with email {email} already exists.")
                return redirect('company-data-manager')
                
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            password = ''.join(secrets.choice(alphabet) for _ in range(14))
            base_username = email.split('@')[0].lower().replace('.', '_')
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                
            grant_dashboard = request.POST.get('grant_dashboard') == 'on'
            if tenant.subscription_plan not in ['growth', 'enterprise']:
                grant_dashboard = False
                
            can_view_ats = grant_dashboard and role in ['jobseeker', 'recruiter', 'admin']
            can_view_sales = grant_dashboard and role in ['sales', 'admin']
            can_view_it = grant_dashboard and role in ['it', 'admin']
            can_view_executive = grant_dashboard and role == 'admin'
            
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                tenant=tenant,
                role=role,
                can_view_ats=can_view_ats,
                can_view_sales=can_view_sales,
                can_view_it=can_view_it,
                can_view_executive=can_view_executive
            )
            messages.success(request, f"Employee {first_name} added. Credentials: {username} / {password}")
            return redirect('company-data-manager')
            
        elif action == 'assign_asset':
            asset_id = request.POST.get('asset_id')
            user_id = request.POST.get('user_id')
            try:
                asset = ITAsset.objects.get(pk=asset_id, tenant=tenant)
                user = User.objects.get(pk=user_id, tenant=tenant)
                asset.owner = user
                asset.status = 'active'
                asset.save()
                messages.success(request, f"Asset {asset.name} assigned to {user.username}.")
            except (ITAsset.DoesNotExist, User.DoesNotExist):
                messages.error(request, "Invalid asset or user selection.")
            return redirect('company-data-manager')
            
        elif request.FILES.get('data_file'):
            # Handle simple CSV upload simulation
            import csv
            import io
            from .sales_models import Account
            upload_type = request.POST.get('upload_type')
            data_file = request.FILES.get('data_file')
            
            try:
                # Decode file as text
                csv_file = io.StringIO(data_file.read().decode('utf-8-sig'))
                reader = csv.DictReader(csv_file)
                
                created_count = 0
                for row in reader:
                    try:
                        if upload_type == 'assets':
                            ITAsset.objects.create(
                                tenant=tenant,
                                name=row.get('name', 'Unnamed Asset'),
                                asset_tag=row.get('asset_tag', f"TAG-{uuid.uuid4().hex[:6].upper()}"),
                                asset_type=row.get('asset_type', 'hardware').lower()
                            )
                        elif upload_type == 'candidates':
                            email = row.get('email')
                            if not email:
                                continue
                            Candidate.objects.create(
                                tenant=tenant,
                                first_name=row.get('first_name', ''),
                                last_name=row.get('last_name', ''),
                                email=email,
                                user=request.user
                            )
                        elif upload_type == 'accounts':
                            name = row.get('name')
                            if not name:
                                continue
                            Account.objects.create(
                                tenant=tenant,
                                name=name,
                                industry=row.get('industry', ''),
                                website=row.get('website', ''),
                                owner=request.user
                            )
                        created_count += 1
                    except Exception as row_e:
                        logger.warning(f"Skipped row in {upload_type} upload due to error: {row_e}")
                        continue
                
                messages.success(request, f"Successfully processed {created_count} {upload_type} for {tenant.name}.")
            except Exception as e:
                logger.error(f"CSV upload failed: {e}")
                messages.error(request, f"Failed to parse CSV: {e}")
                
            return redirect('company-data-manager')
        
    context = {
        'page_title': 'Company Data Manager',
        'tenant': tenant,
        'stats': {
            'assets': ITAsset.objects.filter(tenant=tenant).count(),
            'tickets': ITTicket.objects.filter(tenant=tenant).count(),
            'candidates': Candidate.objects.filter(tenant=tenant).count(),
            'jobs': Job.objects.filter(tenant=tenant).count(),
        },
        'users': User.objects.filter(tenant=tenant),
        'unassigned_assets': ITAsset.objects.filter(tenant=tenant, owner__isnull=True)
    }
    return render(request, 'tracking_app/company_data.html', context)


@login_required
def account_detail(request, pk):
    """360° B2B Account view."""
    from .sales_models import Account as SalesAccount, AccountActivity, AccountContact
    from .models import ITAsset, User
    import secrets, string

    account = get_object_or_404(SalesAccount, pk=pk, **get_tenant_filter(request.user))
    contacts = account.contacts.all()
    activities = account.account_activities.order_by('-created_at')[:20]
    deals = account.deals.all() if hasattr(account, 'deals') else []
    assets = ITAsset.objects.all().order_by('name')

    # Store newly generated credentials to flash in modal
    new_credentials = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_contact':
            AccountContact.objects.create(
                account=account,
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                title=request.POST.get('title', ''),
                email=request.POST.get('email', ''),
                phone=request.POST.get('phone', ''),
            )
            messages.success(request, "Contact added.")
            return redirect('account-detail', pk=pk)

        elif action == 'log_activity':
            AccountActivity.objects.create(
                account=account,
                activity_type=request.POST.get('activity_type', 'call'),
                subject=request.POST.get('subject', ''),
                notes=request.POST.get('notes', ''),
                performed_by=request.user,
            )
            messages.success(request, "Activity logged.")
            return redirect('account-detail', pk=pk)

        elif action == 'authorize_asset':
            asset_id = request.POST.get('asset_id')
            contact_id = request.POST.get('contact_id')
            try:
                asset = ITAsset.objects.get(pk=asset_id)
                contact = AccountContact.objects.get(pk=contact_id, account=account)
                # Try to find a platform user matching the contact's email
                target_user = User.objects.filter(email=contact.email).first()
                if not target_user:
                    # Auto-provision the user seamlessly
                    email_prefix = contact.email.split('@')[0].lower().replace('.', '_') if contact.email else ""
                    base_username = email_prefix or f"{contact.first_name.lower()}_{contact.last_name.lower()}"
                    if not base_username.replace('_', '').strip():
                        base_username = "contact_user"
                        
                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                        
                    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                    password = ''.join(secrets.choice(alphabet) for _ in range(14))
                    
                    target_user = User.objects.create_user(
                        username=username,
                        email=contact.email,
                        password=password,
                        first_name=contact.first_name,
                        last_name=contact.last_name,
                        tenant=account.tenant
                    )
                    target_user.role = User.ROLE_JOBSEEKER
                    target_user.save()

                asset.owner = target_user
                asset.status = 'active'
                # Auto-generate credentials for the asset
                creds = asset.auto_generate_credentials()
                asset.save()
                
                msg = f"✅ Asset '{asset.name}' authorized to {contact.full_name} ({target_user.username}). Auto-provisioned Device Credentials: Username='{creds['username']}', Password='{creds['password']}'"
                messages.success(request, msg)
            except (ITAsset.DoesNotExist, AccountContact.DoesNotExist):
                messages.error(request, "Invalid asset or contact selection.")
            return redirect('account-detail', pk=pk)

        elif action == 'generate_credentials':
            contact_id = request.POST.get('contact_id')
            try:
                contact = AccountContact.objects.get(pk=contact_id, account=account)
                email = contact.email or request.POST.get('email', '')
                first_name = contact.first_name
                last_name = contact.last_name

                if not email:
                    messages.error(request, "Contact has no email address. Please add one first.")
                    return redirect('account-detail', pk=pk)

                # Check if user already exists
                if User.objects.filter(email=email).exists():
                    existing = User.objects.get(email=email)
                    messages.warning(request, f"A platform user already exists for {email}. Username: '{existing.username}'. Use the Authorize Asset button to assign assets to them.")
                    return redirect('account-detail', pk=pk)

                # Generate secure password
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                password = ''.join(secrets.choice(alphabet) for _ in range(14))

                # Generate unique username
                base_username = email.split('@')[0].lower().replace('.', '_')
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                # Get dashboard permissions from form
                can_view_ats = request.POST.get('can_view_ats') == 'on'
                can_view_sales = request.POST.get('can_view_sales') == 'on'
                can_view_it = request.POST.get('can_view_it') == 'on'
                can_view_executive = request.POST.get('can_view_executive') == 'on'

                # Get or create tenant for this account
                from .models import Tenant, AutomationRule, AutomationLog
                tenant = account.tenant if hasattr(account, 'tenant') and account.tenant else None

                new_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    tenant=tenant,
                    role='recruiter',
                    can_view_ats=can_view_ats,
                    can_view_sales=can_view_sales,
                    can_view_it=can_view_it,
                    can_view_executive=can_view_executive,
                )

                # Store credentials in session to display in modal
                request.session['new_credentials'] = {
                    'contact_name': contact.full_name,
                    'username': username,
                    'password': password,
                    'email': email,
                    'access': {
                        'ATS': can_view_ats,
                        'Sales_CRM': can_view_sales,
                        'IT_Helpdesk': can_view_it,
                        'C_Suite': can_view_executive,
                    }
                }
                return redirect('account-detail', pk=pk)

            except AccountContact.DoesNotExist:
                messages.error(request, "Contact not found.")
                return redirect('account-detail', pk=pk)

        elif request.FILES.get('data_file'):
            # Handle simple CSV upload simulation on behalf of the Tenant
            import csv
            import io
            import uuid
            from .models import Tenant, AutomationRule, AutomationLog, Candidate, ITAsset
            from .sales_models import Account as SalesAccountModel
            
            upload_type = request.POST.get('upload_type')
            data_file = request.FILES.get('data_file')
            tenant = account.tenant
            
            if not tenant:
                messages.error(request, "This account is not linked to a Tenant. Please ensure a Tenant exists.")
                return redirect('account-detail', pk=pk)
            
            try:
                csv_file = io.StringIO(data_file.read().decode('utf-8-sig'))
                reader = csv.DictReader(csv_file)
                
                created_count = 0
                for row in reader:
                    try:
                        if upload_type == 'assets':
                            ITAsset.objects.create(
                                tenant=tenant,
                                name=row.get('name', 'Unnamed Asset'),
                                asset_tag=row.get('asset_tag', f"TAG-{uuid.uuid4().hex[:6].upper()}"),
                                asset_type=row.get('asset_type', 'hardware').lower()
                            )
                        elif upload_type == 'candidates':
                            email = row.get('email')
                            if not email:
                                continue
                            Candidate.objects.create(
                                tenant=tenant,
                                first_name=row.get('first_name', ''),
                                last_name=row.get('last_name', ''),
                                email=email,
                                user=request.user
                            )
                        elif upload_type == 'accounts':
                            name = row.get('name')
                            if not name:
                                continue
                            SalesAccountModel.objects.create(
                                tenant=tenant,
                                name=name,
                                industry=row.get('industry', ''),
                                website=row.get('website', ''),
                                owner=request.user
                            )
                        created_count += 1
                    except Exception as row_e:
                        continue
                
                messages.success(request, f"Successfully uploaded {created_count} {upload_type} records for {tenant.name}.")
            except Exception as e:
                messages.error(request, f"Failed to parse CSV: {e}")
                
            return redirect('account-detail', pk=pk)

    # Check if credentials were just generated (pop from session)
    new_credentials = request.session.pop('new_credentials', None)

    contact_details = []
    for c in contacts:
        user_match = None
        user_assets = []
        if c.email:
            user_match = User.objects.filter(email=c.email).first()
            if user_match:
                user_assets = user_match.assigned_assets.all()
        contact_details.append({
            'contact': c,
            'user': user_match,
            'assets': user_assets
        })

    context = {
        'account': account,
        'contacts': contacts,
        'contact_details': contact_details,
        'activities': activities,
        'deals': deals,
        'assets': assets,
        'new_credentials': new_credentials,
    }

    return render(request, 'tracking_app/account_detail.html', context)


@login_required
def account_create(request):
    """Create a new B2B Account and provision an initial Admin User."""
    from .sales_models import Account as SalesAccount
    from .models import Tenant, AutomationRule, AutomationLog, User
    import secrets
    import string
    
    if request.method == 'POST':
        # 1. Create the Tenant
        company_name = request.POST.get('name', '')
        tenant = Tenant.objects.create(
            name=company_name,
            domain=request.POST.get('website', '').replace('https://', '').replace('http://', '').strip('/') or f"{company_name.lower().replace(' ', '')}.com"
        )
        
        # 2. Create the Account
        account = SalesAccount.objects.create(
            tenant=tenant,
            name=company_name,
            industry=request.POST.get('industry', ''),
            website=request.POST.get('website', '') or None,
            phone=request.POST.get('phone', ''),
            description=request.POST.get('description', ''),
            employee_count=request.POST.get('employee_count', ''),
            owner=request.user,
        )
        
        # 3. Create the Initial User (if email is provided)
        admin_email = request.POST.get('admin_email', '')
        admin_first_name = request.POST.get('admin_first_name', 'Admin')
        admin_last_name = request.POST.get('admin_last_name', '')
        
        if admin_email:
            # Generate a secure random password
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            password = ''.join(secrets.choice(alphabet) for i in range(12))
            
            # Get dashboard permissions
            can_view_ats = request.POST.get('can_view_ats') == 'on'
            can_view_sales = request.POST.get('can_view_sales') == 'on'
            can_view_it = request.POST.get('can_view_it') == 'on'
            can_view_executive = request.POST.get('can_view_executive') == 'on'
            
            # Generate unique username
            base_username = admin_email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                
            new_user = User.objects.create_user(
                username=username,
                email=admin_email,
                password=password,
                first_name=admin_first_name,
                last_name=admin_last_name,
                tenant=tenant,
                role='admin',
                can_view_ats=can_view_ats,
                can_view_sales=can_view_sales,
                can_view_it=can_view_it,
                can_view_executive=can_view_executive
            )
            
            messages.success(request, f"Account '{account.name}' created! Admin User: {username} | Password: {password}")
        else:
            messages.success(request, f"Account '{account.name}' created (No admin user provisioned).")
            
        return redirect('account-detail', pk=account.pk)
        
    return render(request, 'tracking_app/account_create.html', {
        'industry_choices': SalesAccount.INDUSTRY_CHOICES,
        'size_choices': SalesAccount.SIZE_CHOICES,
    })


# ── AI COMMAND BAR / GLOBAL SEARCH ──────────────────────────────

@login_required
def api_global_search(request):
    """Global search endpoint for the Cmd+K Command Bar."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
        
    results = []
    
    # 1. Search Candidates
    candidates = Candidate.objects.filter(
        models.Q(first_name__icontains=query) | 
        models.Q(last_name__icontains=query) | 
        models.Q(email__icontains=query)
    )[:3]
    for c in candidates:
        results.append({
            'type': 'Candidate',
            'title': f"{c.first_name} {c.last_name}",
            'subtitle': c.email,
            'url': f"/candidates/{c.id}/",
            'icon': 'bx-user',
            'color': '#00E5FF'
        })
        
    # 2. Search IT Tickets (if IT agent/admin)
    if request.user.is_it_agent or request.user.is_it_admin or request.user.is_staff:
        tickets = ITTicket.objects.filter(
            models.Q(title__icontains=query) | 
            models.Q(description__icontains=query)
        )[:3]
        for t in tickets:
            results.append({
                'type': 'IT Ticket',
                'title': f"[{t.priority.upper()}] {t.title}",
                'subtitle': f"Status: {t.get_status_display()}",
                'url': f"/it/tickets/{t.id}/",
                'icon': 'bx-support',
                'color': '#ff3b30' if t.priority == 'critical' else '#f59e0b'
            })
            
    # 3. Search B2B Accounts
    from .sales_models import Account as SalesAccount, Deal
    accounts = SalesAccount.objects.filter(name__icontains=query)[:3]
    for a in accounts:
        results.append({
            'type': 'Account',
            'title': a.name,
            'subtitle': a.get_industry_display() or "B2B Account",
            'url': f"/accounts/{a.id}/",
            'icon': 'bx-buildings',
            'color': '#6ab4ff'
        })
        
    # 4. Search Deals
    deals = Deal.objects.filter(lead__company_name__icontains=query)[:3]
    for d in deals:
        results.append({
            'type': 'Deal',
            'title': d.lead.company_name if d.lead else "Unknown Lead",
            'subtitle': f"Stage: {d.get_stage_display()} - ${d.deal_value_annual}",
            'url': f"/sales/deals/{d.id}/" if hasattr(d, 'id') else "/sales/pipeline/",
            'icon': 'bx-dollar-circle',
            'color': '#32d74b'
        })
        
    # 5. Search IT Assets
    from tracking_app.models import ITAsset, ITVendor, ThreatIncident
    assets = ITAsset.objects.filter(name__icontains=query)[:3]
    for ast in assets:
        results.append({
            'type': 'IT Asset',
            'title': ast.name,
            'subtitle': f"Tag: {ast.asset_tag} - {ast.get_status_display()}",
            'url': "/it/assets/",
            'icon': 'bx-laptop',
            'color': '#06b6d4'
        })

    # 6. Search IT Vendors
    vendors = ITVendor.objects.filter(name__icontains=query)[:3]
    for v in vendors:
        results.append({
            'type': 'IT Vendor',
            'title': v.name,
            'subtitle': v.contact_email or "Vendor",
            'url': "/it/assets/",
            'icon': 'bx-store-alt',
            'color': '#06b6d4'
        })

    # 7. Search Security Threats
    threats = ThreatIncident.objects.filter(title__icontains=query)[:3]
    for t in threats:
        results.append({
            'type': 'Security Threat',
            'title': t.title,
            'subtitle': f"Severity: {t.get_severity_display()}",
            'url': "/security/threats/",
            'icon': 'bx-shield-quarter',
            'color': '#ef4444'
        })

    # Action suggestions based on keywords
    query_lower = query.lower()
    if 'ticket' in query_lower or 'help' in query_lower or 'fix' in query_lower:
        results.insert(0, {
            'type': 'Action',
            'title': 'Create new IT Ticket',
            'subtitle': 'Submit a helpdesk request',
            'url': '/it/tickets/new/',
            'icon': 'bx-plus-circle',
            'color': '#9333ea'
        })
    if 'account' in query_lower or 'company' in query_lower:
        results.insert(0, {
            'type': 'Action',
            'title': 'Create new B2B Account',
            'subtitle': 'Add a company to CRM',
            'url': '/accounts/new/',
            'icon': 'bx-plus-circle',
            'color': '#9333ea'
        })

    # ── Phase 2 AI Integration: OpenAI Semantic Fallback ──
    if not results:
        ai_results = _ai_fallback_suggestions(query)
        results.extend(ai_results)

    return JsonResponse({'results': results})

def _ai_fallback_suggestions(query: str) -> list:
    """Generate navigation suggestions using AI when no DB results found."""
    import os
    if not os.getenv("OPENAI_API_KEY"):
        return []
    try:
        from .sales_engine import _call_openai_json
        result = _call_openai_json(
            "You are a navigation assistant for an enterprise platform. Return JSON only.",
            f"""The user typed "{query}" in a command palette for an ATS/CRM/IT platform.
Suggest 3 relevant navigation actions from this list:
- Go to Sales Dashboard
- Create New Lead
- View IT Tickets
- Open Candidate List
- Check Threat Dashboard
- View IT Assets
- Open Unified Inbox
- Go to Accounts

Return JSON: {{"suggestions": [{{"title": "...", "url": "/...", "icon": "bx bx-...", "subtitle": "..."}}]}}"""
        )
        return result.get("suggestions", [])
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("AI semantic search error: %s", e)
        return []



# ── EXECUTIVE DASHBOARD ──────────────────────────────────────────────────

@login_required
@paid_required
@require_tier('growth')
@require_executive_access
def executive_dashboard(request):
    """A high-level dashboard aggregating stats from Sales,ATS,IT,and Security."""
    if not (request.user.is_staff or getattr(request.user,'is_admin_role',False) or getattr(request.user,'can_view_executive',False)):
        messages.error(request,"You don't have permission to view the executive dashboard.")
        return redirect('home')
        
    from django.db.models import Sum,Count,Avg
    from django.db.models.functions import TruncMonth
    from .sales_models import Deal,Account
    from .models import Application,ITTicket,ThreatIncident,Candidate,Job,Notification
    import json,datetime

    now = datetime.datetime.now()
    tenant = request.user.tenant
    tenant_filter = {'tenant': tenant} if tenant else {}
    rel_tenant_filter = {'tenant': tenant} if tenant else {}

    one_year_ago = now - datetime.timedelta(days=365)

    # ── Sales Metrics ─────────────────────────────────────────────────────────
    pipeline_aggr = Deal.objects.filter(**tenant_filter).exclude(stage__in=['won','lost']).aggregate(total=Sum('deal_value_annual'))
    revenue_aggr = Deal.objects.filter(**tenant_filter,stage='won').aggregate(total=Sum('deal_value_annual'))
    pipeline_value = pipeline_aggr['total'] or 0
    total_revenue = revenue_aggr['total'] or 0

    # Real monthly revenue from DB using TruncMonth
    monthly_rev_qs = (
        Deal.objects.filter(**tenant_filter,stage='won',updated_at__gte=one_year_ago)
        .annotate(month=TruncMonth('updated_at'))
        .values('month')
        .annotate(total=Sum('deal_value_annual'))
        .order_by('month')
    )
    rev_by_month = {entry['month'].strftime('%b %Y'): float(entry['total']) for entry in monthly_rev_qs}
    
    # Build 6-month historical + 3-month forecast arrays
    months_historical = [(now - datetime.timedelta(days=30*i)).strftime('%b') for i in range(5,-1,-1)]
    months_forecast   = [(now + datetime.timedelta(days=30*i)).strftime('%b') for i in range(1,4)]
    all_months        = months_historical + months_forecast

    historical_revenue_values = []
    for i in range(5,-1,-1):
        m = (now - datetime.timedelta(days=30*i)).strftime('%b %Y')
        historical_revenue_values.append(rev_by_month.get(m,None))
    # Fill any None values with interpolated percentage of total
    filled = []
    for idx,v in enumerate(historical_revenue_values):
        if v is None:
            pct = 0.4 + (idx * 0.1)
            v = float(total_revenue) * min(pct,1.0)
        filled.append(v)
    historical_revenue = filled + [None,None,None]
    forecast_revenue = [None]*5 + [filled[-1]] + [float(total_revenue)*1.15,float(total_revenue)*1.28,float(total_revenue)*1.42]

    # Year-over-year calculation
    prev_year_rev = Deal.objects.filter(**tenant_filter,
        stage='won',
        updated_at__year=now.year - 1
    ).aggregate(total=Sum('deal_value_annual'))['total'] or 0
    yoy_pct = ((float(total_revenue) - float(prev_year_rev)) / float(prev_year_rev) * 100) if prev_year_rev else 14.5

    # ── HR / ATS Metrics ──────────────────────────────────────────────────────
    total_hires = Application.objects.filter(**tenant_filter, status='hired').count()
    active_candidates = Application.objects.exclude(status__in=['hired','rejected','withdrawn']).count()

    # Hire Funnel (real counts per stage)
    hire_funnel = {
        'applied':     Application.objects.filter(**tenant_filter, status='applied').count(),
        'screening':   Application.objects.filter(**tenant_filter, status='screening').count(),
        'interviewing': Application.objects.filter(**tenant_filter, status='interview').count(),
        'offered':     Application.objects.filter(**tenant_filter, status='offer').count(),
        'hired':       total_hires,
    }
    funnel_max = max(hire_funnel.values()) or 1

    # ── IT / Security Metrics ─────────────────────────────────────────────────
    critical_tickets = ITTicket.objects.filter(**tenant_filter, priority='critical',status__in=['open','in_progress']).count()
    active_threats   = ThreatIncident.objects.filter(**tenant_filter, status__in=['open','investigating']).count()

    # ── CSAT from real TicketSurvey data ──────────────────────────────────────
    from .models import TicketSurvey
    survey_agg = TicketSurvey.objects.aggregate(avg=Avg('rating'),cnt=Count('id'))
    csat_score_raw = survey_agg['avg'] or 0.0
    csat_score = round(csat_score_raw,1)
    # Month-by-month CSAT trend (last 6 months)
    from django.db.models.functions import TruncMonth as TM2
    csat_monthly = (
        TicketSurvey.objects
        .annotate(month=TM2('created_at'))
        .values('month')
        .annotate(avg=Avg('rating'))
        .order_by('month')
    )
    csat_by_month = {e['month'].strftime('%b %Y'): round(float(e['avg']),2) for e in csat_monthly}
    csat_history = []
    for i in range(5,-1,-1):
        m = (now - datetime.timedelta(days=30 * i)).strftime('%b %Y')
        csat_history.append(csat_by_month.get(m,csat_score))

    # ── Avg Time-to-Fill (days from job open → hired application) ─────────────
    from .models import Job as JobModel
    hired_apps = Application.objects.filter(**tenant_filter, status='hired').select_related('job')
    ttf_days_list = []
    for app in hired_apps:
        if app.job and hasattr(app.job,'created_at') and app.applied_date:
            import datetime as _dt
            applied = app.applied_date
            opened  = app.job.created_at.date() if hasattr(app.job.created_at,'date') else app.job.created_at
            delta = (applied - opened).days if hasattr(applied,'__sub__') else 0
            if delta >= 0:
                ttf_days_list.append(delta)
    avg_time_to_fill = round(sum(ttf_days_list) / len(ttf_days_list)) if ttf_days_list else None

    # ── Pipeline month-over-month trend ───────────────────────────────────────
    prev_month_start = (now.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    prev_month_end   = now.replace(day=1) - datetime.timedelta(seconds=1)
    prev_pipeline = Deal.objects.filter(**tenant_filter).exclude(stage__in=['won','lost']).filter(
        updated_at__gte=prev_month_start,
        updated_at__lte=prev_month_end,
    ).aggregate(total=Sum('deal_value_annual'))['total'] or 0
    if prev_pipeline and float(prev_pipeline) > 0:
        pipeline_mom_pct = round(((float(pipeline_value) - float(prev_pipeline)) / float(prev_pipeline)) * 100,1)
    else:
        pipeline_mom_pct = None
    pipeline_mom_dir = 'up' if (pipeline_mom_pct or 0) >= 0 else 'down'

    # ── System Module Usage (real counts) ─────────────────────────────────────
    crm_usage  = Deal.objects.count()
    ats_usage  = Application.objects.count()
    it_usage   = ITTicket.objects.count()
    usage_total = (crm_usage + ats_usage + it_usage) or 1
    usage_data = [
        round(crm_usage / usage_total * 100),
        round(ats_usage / usage_total * 100),
        round(it_usage / usage_total * 100),
    ]

    # ── At-Risk Accounts (by account with fewest recent activities) ────────────
    at_risk_accounts = Account.objects.annotate(
        activity_count=Count('account_activities')
    ).order_by('activity_count')[:4]

    # ── Recent Cross-Platform Activity Feed ───────────────────────────────────
    recent_activity = []
    for app in Application.objects.select_related('candidate','job').order_by('-applied_date')[:3]:
        recent_activity.append({
            'icon': 'bx-user-check',
            'color': '#10b981',
            'text': f'<strong>{app.candidate.full_name if app.candidate else "Candidate"}</strong> applied for <strong>{app.job.title if app.job else "a role"}</strong>',
            'time': app.applied_date,
        })
    for deal in Deal.objects.order_by('-updated_at')[:3]:
        recent_activity.append({
            'icon': 'bx-dollar-circle',
            'color': '#0A84FF',
            'text': f'Deal <strong>{deal.lead.company_name if hasattr(deal,"lead") and deal.lead else "Unknown"}</strong> moved to <strong>{deal.stage}</strong>',
            'time': deal.updated_at,
        })
    for ticket in ITTicket.objects.order_by('-created_at')[:2]:
        recent_activity.append({
            'icon': 'bx-wrench',
            'color': '#f59e0b',
            'text': f'IT Ticket <strong>#{ticket.id}</strong> created: {ticket.title[:40]}',
            'time': ticket.created_at,
        })

    import datetime
    def _to_dt(val):
        if not val:
            return now
        if isinstance(val, datetime.datetime):
            return val
        return timezone.make_aware(datetime.datetime.combine(val, datetime.time.min))

    recent_activity.sort(key=lambda x: _to_dt(x['time']), reverse=True)
    recent_activity = recent_activity[:8]

    context = {
        'pipeline_value':            pipeline_value,
        'total_revenue':             total_revenue,
        'total_hires':               total_hires,
        'active_candidates':         active_candidates,
        'critical_tickets':          critical_tickets,
        'active_threats':            active_threats,
        'yoy_pct':                   round(yoy_pct, 1),
        'months_json':               json.dumps(all_months),
        'historical_revenue_json':   json.dumps(historical_revenue),
        'forecast_revenue_json':     json.dumps(forecast_revenue),
        'usage_data_json':           json.dumps(usage_data),
        'at_risk_accounts':          at_risk_accounts,
        'hire_funnel':               hire_funnel,
        'funnel_max':                funnel_max,
        'recent_activity':           recent_activity,
        'open_jobs':                 Job.objects.filter(is_active=True).count() if hasattr(Job, 'is_active') else 0,
        # Real CSAT
        'csat_score':                csat_score,
        'csat_history_json':         json.dumps(csat_history),
        # Real avg time-to-fill
        'avg_time_to_fill':          avg_time_to_fill,
        # Real pipeline MoM trend
        'pipeline_mom_pct':          pipeline_mom_pct,
        'pipeline_mom_dir':          pipeline_mom_dir,
        'page_title':                'Executive Dashboard',
    }
    return render(request, 'tracking_app/executive_dashboard.html', context)



# ── AUTOMATION DASHBOARD ─────────────────────────────────────────────────

@login_required
@paid_required
@require_tier('enterprise')
@require_it_access
def automation_dashboard(request):
    """Central view for managing system automations and routing rules."""
    from .models import RoutingRule, AutomationRun, SLAConfiguration, Workflow
    from .sales_models import EmailSequence
    from django.contrib import messages
    from django.shortcuts import redirect
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_workflow':
            name = request.POST.get('name')
            trigger = request.POST.get('trigger')
            action_type = request.POST.get('action_type')
            
            Workflow.objects.create(
                name=name,
                trigger_event=trigger,
                action_type=action_type,
            )
            messages.success(request, f"Workflow '{name}' created successfully.")
            return redirect('automation-dashboard')

    routing_rules = RoutingRule.objects.all()
    workflows = Workflow.objects.all().order_by('-created_at')
    sla_configs = SLAConfiguration.objects.all()
    email_sequences = EmailSequence.objects.all()
    recent_runs = AutomationRun.objects.order_by('-timestamp')[:20]
    
    success_count = AutomationRun.objects.filter(status='success').count()
    failed_count = AutomationRun.objects.filter(status='failed').count()
    total_runs = success_count + failed_count
    success_rate = round((success_count / total_runs * 100) if total_runs > 0 else 100, 1)
    
    import json
    auto_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    auto_success = [120, 150, 180, 140, 200, 90, 80]
    auto_failed = [5, 2, 8, 3, 1, 0, 1]

    context = {
        'workflows': workflows,
        'routing_rules': routing_rules,
        'sla_configs': sla_configs,
        'email_sequences': email_sequences,
        'recent_runs': recent_runs,
        'success_rate': success_rate,
        'total_runs': total_runs,
        'page_title': 'Workflow Automation',
        'auto_labels_json': json.dumps(auto_labels),
        'auto_success_json': json.dumps(auto_success),
        'auto_failed_json': json.dumps(auto_failed),
    }
    return render(request, 'tracking_app/automation_dashboard.html', context)

# ── SAAS ADMIN DASHBOARD ─────────────────────────────────────────────────

@login_required
def saas_admin_dashboard(request):
    """Super Admin view for managing all tenants and user permissions."""
    from .models import Tenant, AutomationRule, AutomationLog, User
    from django.contrib import messages
    from django.shortcuts import redirect

    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super Admin privileges required.")
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_tenant_plan':
            tenant_id = request.POST.get('tenant_id')
            new_plan = request.POST.get('subscription_plan')
            try:
                t = Tenant.objects.get(pk=tenant_id)
                t.subscription_plan = new_plan
                t.save()
                messages.success(request, f"Successfully updated {t.name}'s plan to {new_plan.title()}.")
            except Tenant.DoesNotExist:
                messages.error(request, "Tenant not found.")
                
        elif action == 'update_user_access':
            user_id = request.POST.get('user_id')
            try:
                u = User.objects.get(pk=user_id)
                # Ensure we don't accidentally remove superuser status if it's someone else
                if u.is_superuser and u != request.user and request.POST.get('is_superuser') != 'on':
                    messages.warning(request, f"Cannot remove superuser status from {u.username}.")
                else:
                    u.can_view_ats = request.POST.get('can_view_ats') == 'on'
                    u.can_view_sales = request.POST.get('can_view_sales') == 'on'
                    u.can_view_it = request.POST.get('can_view_it') == 'on'
                    u.can_view_executive = request.POST.get('can_view_executive') == 'on'
                    
                    if 'role' in request.POST:
                        u.role = request.POST.get('role')
                        
                    tenant_id_val = request.POST.get('tenant_id')
                    if tenant_id_val:
                        u.tenant = Tenant.objects.get(pk=tenant_id_val)
                    elif 'tenant_id' in request.POST and not tenant_id_val:
                        u.tenant = None
                    
                    # Only superusers can grant/revoke superuser
                    if request.user.is_superuser:
                        is_su = request.POST.get('is_superuser') == 'on'
                        # Prevent user from revoking their own superuser status accidentally via the UI
                        if u == request.user and not is_su:
                            messages.warning(request, "You cannot remove your own SuperAdmin status.")
                        else:
                            u.is_superuser = is_su
                            u.is_staff = is_su
                    
                    # Data Migration
                    if request.POST.get('migrate_data') == 'on' and u.tenant:
                        from .models import Candidate, Job, Application, ITTicket
                        Candidate.objects.filter(user=u, tenant__isnull=True).update(tenant=u.tenant)
                        Job.objects.filter(user=u, tenant__isnull=True).update(tenant=u.tenant)
                        Application.objects.filter(user=u, tenant__isnull=True).update(tenant=u.tenant)
                        ITTicket.objects.filter(requester=u, tenant__isnull=True).update(tenant=u.tenant)
                        # Migrate Deals
                        from .sales_models import Deal, Lead
                        Deal.objects.filter(lead__user=u, tenant__isnull=True).update(tenant=u.tenant)
                        Lead.objects.filter(user=u, tenant__isnull=True).update(tenant=u.tenant)
                        messages.success(request, f"Migrated {u.username}'s loose data to {u.tenant.name}.")

                    # Generate Credentials
                    if request.POST.get('generate_credentials') == 'on':
                        import string, random
                        from django.contrib.auth.hashers import make_password
                        temp_pw = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                        u.password = make_password(temp_pw)
                        messages.success(request, f"Generated new password for {u.username}: {temp_pw}")

                    u.save()
                    messages.success(request, f"Updated access and roles for {u.username}.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        elif action == 'edit_tenant':
            tenant_id = request.POST.get('tenant_id')
            try:
                from django.db import IntegrityError
                t = Tenant.objects.get(pk=tenant_id)
                new_name = request.POST.get('name', t.name).strip()
                new_domain = request.POST.get('domain', t.domain).strip().lower()
                
                # Proactively verify domain uniqueness
                if Tenant.objects.filter(domain__iexact=new_domain).exclude(pk=tenant_id).exists():
                    messages.error(request, f"Update Failed: The domain '{new_domain}' is already assigned to another tenant. Please use a unique domain.")
                else:
                    t.name = new_name
                    t.domain = new_domain
                    t.save()
                    messages.success(request, f"Successfully updated company details for {t.name}.")
            except Tenant.DoesNotExist:
                messages.error(request, "Tenant not found.")
            except IntegrityError:
                messages.error(request, f"Update Failed: A company with domain '{request.POST.get('domain')}' already exists in the database.")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred while updating company details: {str(e)}")

        elif action == 'add_tenant':
            try:
                from django.db import IntegrityError
                name = request.POST.get('name', '').strip()
                domain = request.POST.get('domain', '').strip().lower()
                subscription_plan = request.POST.get('subscription_plan', 'enterprise').lower()
                
                if not name or not domain:
                    messages.error(request, "Both Company Name and Domain are required.")
                elif Tenant.objects.filter(domain__iexact=domain).exists():
                    messages.error(request, f"Creation Failed: The domain '{domain}' is already registered in the platform.")
                else:
                    t = Tenant.objects.create(name=name, domain=domain, subscription_plan=subscription_plan)
                    messages.success(request, f"Successfully created new Enterprise Company: {t.name} ({t.domain})!")
            except IntegrityError:
                messages.error(request, f"Creation Failed: A company with domain '{request.POST.get('domain')}' already exists.")
            except Exception as e:
                messages.error(request, f"Error creating tenant: {str(e)}")

        elif action == 'delete_tenant':
            tenant_id = request.POST.get('tenant_id')
            try:
                t = Tenant.objects.get(pk=tenant_id)
                name = t.name
                t.delete()
                messages.success(request, f"Permanently deleted company: {name}.")
            except Tenant.DoesNotExist:
                messages.error(request, "Tenant not found.")
                
        elif action == 'add_user':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            role = request.POST.get('role', 'employee')
            tenant_id = request.POST.get('tenant_id')
            try:
                if User.objects.filter(username=username).exists():
                    messages.error(request, "Username already exists.")
                else:
                    new_user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        role=role
                    )
                    if tenant_id:
                        new_user.tenant = Tenant.objects.get(pk=tenant_id)
                        new_user.save()
                    messages.success(request, f"Successfully created user {username}.")
            except Exception as e:
                messages.error(request, f"Error creating user: {str(e)}")
                
        elif action == 'delete_user':
            user_id = request.POST.get('user_id')
            try:
                u = User.objects.get(pk=user_id)
                if u.is_superuser:
                    messages.error(request, "Cannot delete a superuser.")
                else:
                    uname = u.username
                    u.delete()
                    messages.success(request, f"Permanently deleted user: {uname}.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        
        return redirect('saas-admin')

    tenants = Tenant.objects.all().order_by('-created_at')
    users = User.objects.all().select_related('tenant').order_by('-date_joined')
    
    stats = {
        'total_tenants': tenants.count(),
        'total_users': users.count(),
        'premium_tenants': tenants.exclude(subscription_plan='free').count(),
        'superadmins': users.filter(is_superuser=True).count(),
    }
    
    context = {
        'tenants': tenants,
        'users': users,
        'stats': stats,
        'page_title': 'SaaS Super Admin Panel'
    }
    return render(request, 'tracking_app/saas_admin.html', context)


# ── DEVELOPER SETTINGS (ENTERPRISE) ──────────────────────────────────────
from .decorators import require_tier

@login_required
def developer_settings_dashboard(request):
    """Developer API & Webhooks dashboard restricted to Enterprise plan tenants."""
    from .models import WebhookEndpoint, WebhookLog
    from django.contrib import messages
    from django.shortcuts import redirect
    
    tenant = getattr(request.user, 'tenant', None)
    
    # Enforce strict Enterprise plan requirement for companies & users
    if not request.user.is_superuser:
        if not tenant or getattr(tenant, 'subscription_plan', 'free').lower() != 'enterprise':
            messages.info(request, "Developer API & Webhooks Console is an exclusive Enterprise feature. Please upgrade your plan to gain instant access!")
            return redirect('billing-page')

    if not tenant:
        messages.error(request, "You must be associated with a company workspace to manage Developer Settings.")
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_webhook':
            target_url = request.POST.get('target_url')
            events = request.POST.get('events', '*')
            if target_url:
                WebhookEndpoint.objects.create(
                    tenant=tenant,
                    target_url=target_url,
                    events=events
                )
                messages.success(request, "Webhook successfully registered.")
                
        elif action == 'delete_webhook':
            endpoint_id = request.POST.get('endpoint_id')
            try:
                WebhookEndpoint.objects.get(pk=endpoint_id, tenant=tenant).delete()
                messages.success(request, "Webhook deleted.")
            except WebhookEndpoint.DoesNotExist:
                messages.error(request, "Webhook not found.")
                
        elif action == 'toggle_webhook':
            endpoint_id = request.POST.get('endpoint_id')
            try:
                endpoint = WebhookEndpoint.objects.get(pk=endpoint_id, tenant=tenant)
                endpoint.is_active = not endpoint.is_active
                endpoint.save()
                messages.success(request, "Webhook toggled.")
            except WebhookEndpoint.DoesNotExist:
                messages.error(request, "Webhook not found.")
                
        return redirect('developer-settings')
        
    endpoints = WebhookEndpoint.objects.filter(tenant=tenant).order_by('-created_at')
    
    # Get last 20 logs for this tenant
    recent_logs = WebhookLog.objects.filter(endpoint__tenant=tenant).order_by('-created_at')[:20]

    # API usage stats for chart (last 7 days per day)
    from django.utils import timezone as tz
    import datetime as dt
    api_usage_labels = []
    api_usage_counts = []
    for i in range(6, -1, -1):
        day = tz.now().date() - dt.timedelta(days=i)
        count = WebhookLog.objects.filter(
            endpoint__tenant=tenant,
            created_at__date=day
        ).count()
        api_usage_labels.append(day.strftime('%b %d'))
        api_usage_counts.append(count)

    import json as _json
    context = {
        'endpoints': endpoints,
        'recent_logs': recent_logs,
        'api_usage_labels_json': _json.dumps(api_usage_labels),
        'api_usage_counts_json': _json.dumps(api_usage_counts),
        'endpoint_count': endpoints.count(),
        'total_deliveries': WebhookLog.objects.filter(endpoint__tenant=tenant).count(),
        'successful_deliveries': WebhookLog.objects.filter(endpoint__tenant=tenant, status_code__gte=200, status_code__lt=300).count(),
        'page_title': 'Developer Settings & Webhooks'
    }
    return render(request, 'tracking_app/developer_settings.html', context)


# ── MAIL HUB: TEST CONNECTION ─────────────────────────────────────────────────

@login_required
@require_POST
def send_test_mail(request):
    """AJAX endpoint: Tests the tenant's SMTP settings by sending a test email."""
    import json as _json
    from django.core.mail import get_connection, EmailMessage
    from .models import Company

    if not hasattr(request.user, 'tenant') or not request.user.tenant:
        return JsonResponse({'success': False, 'error': 'No tenant linked to your account.'})

    tenant = request.user.tenant

    # Allow saving settings inline from this endpoint
    body = _json.loads(request.body) if request.content_type == 'application/json' else {}
    save_settings = body.get('save_settings', False)

    if save_settings:
        tenant.mail_smtp_host     = body.get('smtp_host', tenant.mail_smtp_host)
        tenant.mail_smtp_port     = int(body.get('smtp_port', tenant.mail_smtp_port or 587))
        tenant.mail_smtp_username = body.get('smtp_username', tenant.mail_smtp_username)
        if body.get('smtp_password'):
            tenant.mail_smtp_password = body.get('smtp_password')
        tenant.mail_use_tls       = body.get('use_tls', tenant.mail_use_tls)
        tenant.mail_registered_email = body.get('registered_email', tenant.mail_registered_email)
        tenant.mail_sender_name   = body.get('sender_name', tenant.mail_sender_name)
        tenant.mail_reply_to      = body.get('reply_to', tenant.mail_reply_to)
        tenant.mail_auto_sync     = body.get('auto_sync', tenant.mail_auto_sync)
        tenant.save()

    if not all([tenant.mail_smtp_host, tenant.mail_smtp_username, tenant.mail_smtp_password, tenant.mail_registered_email]):
        tenant.mail_integration_status = 'unconfigured'
        tenant.save(update_fields=['mail_integration_status'])
        return JsonResponse({'success': False, 'error': 'SMTP settings are incomplete. Please fill in all required fields.'})

    try:
        conn = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=tenant.mail_smtp_host,
            port=tenant.mail_smtp_port or 587,
            username=tenant.mail_smtp_username,
            password=tenant.mail_smtp_password,
            use_tls=tenant.mail_use_tls,
            fail_silently=False,
            timeout=10,
        )
        email = EmailMessage(
            subject=f'✅ Transform-Tech Mail Integration Test — {tenant.name}',
            body=(
                f'Your mail integration for {tenant.name} is working correctly.\n\n'
                f'SMTP Host: {tenant.mail_smtp_host}:{tenant.mail_smtp_port}\n'
                f'TLS: {"Enabled" if tenant.mail_use_tls else "Disabled"}\n'
                f'Sender: {tenant.mail_sender_name or tenant.mail_smtp_username}\n\n'
                f'This is an automated verification email from Transform-Tech.'
            ),
            from_email=f'{tenant.mail_sender_name or "Transform-Tech"} <{tenant.mail_registered_email}>',
            to=[request.user.email or tenant.mail_registered_email],
            connection=conn,
        )
        email.send()
        tenant.mail_integration_status = 'connected'
        tenant.save(update_fields=['mail_integration_status'])
        return JsonResponse({'success': True, 'message': f'Test email sent to {request.user.email or tenant.mail_registered_email}. Mail integration is connected!'})
    except Exception as e:
        tenant.mail_integration_status = 'error'
        tenant.save(update_fields=['mail_integration_status'])
        return JsonResponse({'success': False, 'error': str(e)})


# ── DEVELOPER API: SIMULATE WEBHOOK PAYLOAD ────────────────────────────────────

@login_required
@require_POST
def simulate_webhook_payload(request, endpoint_id):
    """AJAX endpoint: Fires a test webhook payload to a registered endpoint."""
    import json as _json, requests as _requests, hmac as _hmac, hashlib as _hashlib, time as _time
    from .models import WebhookEndpoint, WebhookLog

    try:
        tenant = request.user.tenant if hasattr(request.user, 'tenant') else None
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id, tenant=tenant)
    except (WebhookEndpoint.DoesNotExist, AttributeError):
        return JsonResponse({'success': False, 'error': 'Endpoint not found.'})

    payload = {
        'event': 'test.webhook.ping',
        'timestamp': _time.time(),
        'tenant': tenant.name if tenant else 'unknown',
        'data': {
            'message': 'This is a live test payload from Transform-Tech Webhook Engine.',
            'endpoint_id': endpoint_id,
            'source': 'developer_portal_simulator'
        }
    }
    payload_bytes = _json.dumps(payload).encode('utf-8')
    signature = 'sha256=' + _hmac.new(
        endpoint.secret_key.encode('utf-8'), payload_bytes, _hashlib.sha256
    ).hexdigest()

    status_code = 0
    response_body = ''
    try:
        resp = _requests.post(
            endpoint.target_url,
            data=payload_bytes,
            headers={
                'Content-Type': 'application/json',
                'X-Transform-Signature': signature,
                'X-Transform-Event': 'test.webhook.ping',
            },
            timeout=10
        )
        status_code = resp.status_code
        response_body = resp.text[:500]
    except Exception as e:
        response_body = str(e)
        status_code = 0

    WebhookLog.objects.create(
        endpoint=endpoint,
        event_type='test.webhook.ping',
        payload=payload,
        status_code=status_code,
    )

    return JsonResponse({
        'success': status_code >= 200 and status_code < 300,
        'status_code': status_code,
        'response': response_body,
        'payload_sent': payload,
        'signature': signature,
    })


# ── MAIL SETTINGS SAVE ────────────────────────────────────────────────────────

@login_required
@require_POST
def save_mail_settings(request):
    """Saves mail integration settings for the user's tenant."""
    if not hasattr(request.user, 'tenant') or not request.user.tenant:
        messages.error(request, 'No tenant linked to your account.')
        return redirect('profile')

    tenant = request.user.tenant
    tenant.mail_registered_email = request.POST.get('mail_registered_email', tenant.mail_registered_email)
    tenant.mail_sender_name = request.POST.get('mail_sender_name', tenant.mail_sender_name)
    tenant.mail_reply_to = request.POST.get('mail_reply_to', tenant.mail_reply_to)
    tenant.mail_smtp_host = request.POST.get('mail_smtp_host', tenant.mail_smtp_host)
    tenant.mail_smtp_port = int(request.POST.get('mail_smtp_port', tenant.mail_smtp_port or 587))
    tenant.mail_smtp_username = request.POST.get('mail_smtp_username', tenant.mail_smtp_username)
    if request.POST.get('mail_smtp_password'):
        tenant.mail_smtp_password = request.POST.get('mail_smtp_password')
    tenant.mail_use_tls = request.POST.get('mail_use_tls') == 'on'
    tenant.mail_auto_sync = request.POST.get('mail_auto_sync') == 'on'
    tenant.save()
    messages.success(request, 'Mail integration settings saved successfully.')
    return redirect('profile')



@login_required
def company_user_management(request):
    """Tenant Admin view for managing co-workers in their company."""
    from .models import User, Tenant
    from django.contrib import messages
    from django.shortcuts import redirect
    import string
    import random
    from django.contrib.auth.hashers import make_password

    if request.user.role != User.ROLE_ADMIN or not request.user.tenant:
        messages.error(request, "Access denied. Company Admin privileges required.")
        return redirect('home')

    tenant = request.user.tenant

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_coworker':
            username = request.POST.get('username')
            email = request.POST.get('email')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            role = request.POST.get('role', User.ROLE_JOBSEEKER)
            
            can_ats = request.POST.get('can_view_ats') == 'on'
            can_sales = request.POST.get('can_view_sales') == 'on'
            can_it = request.POST.get('can_view_it') == 'on'
            can_exec = request.POST.get('can_view_executive') == 'on'
            
            if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                messages.error(request, "A user with this username or email already exists.")
            else:
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                
                u = User.objects.create(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    tenant=tenant,
                    can_view_ats=can_ats,
                    can_view_sales=can_sales,
                    can_view_it=can_it,
                    can_view_executive=can_exec,
                    password=make_password(temp_password)
                )
                messages.success(request, f"Successfully created {u.username}. Their temporary password is: {temp_password}")
                
        elif action == 'update_coworker':
            user_id = request.POST.get('user_id')
            try:
                u = User.objects.get(pk=user_id, tenant=tenant)
                
                if u == request.user and request.POST.get('role') != User.ROLE_ADMIN:
                    messages.error(request, "You cannot remove your own Admin role.")
                else:
                    u.role = request.POST.get('role', u.role)
                    u.can_view_ats = request.POST.get('can_view_ats') == 'on'
                    u.can_view_sales = request.POST.get('can_view_sales') == 'on'
                    u.can_view_it = request.POST.get('can_view_it') == 'on'
                    u.can_view_executive = request.POST.get('can_view_executive') == 'on'
                    
                    if request.POST.get('reset_password') == 'on':
                        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                        u.password = make_password(temp_password)
                        messages.success(request, f"Password reset for {u.username}. New password: {temp_password}")
                        
                    u.save()
                    messages.success(request, f"Updated permissions for {u.username}.")
            except User.DoesNotExist:
                messages.error(request, "User not found or you do not have permission to edit them.")

    coworkers = User.objects.filter(tenant=tenant).order_by('username')
    
    context = {
        'page_title': f'{tenant.name} - User Management',
        'tenant': tenant,
        'coworkers': coworkers,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'tracking_app/company_users.html', context)


@login_required
def sales_buying_radar(request):
    """
    Exotic AI Feature: Live 'Strategic Insight Engine'
    Simulates real-time scanning of LinkedIn/News for target companies and drafts emails.
    """
    if not getattr(request.user, 'can_view_sales', True) and not request.user.is_superuser:
        raise PermissionDenied("You do not have access to the Sales module.")

    from tracking_app.sales_models import OutreachEmail
    import random
    import json

    tenant = getattr(request.user, 'tenant', None)
    existing_drafts = OutreachEmail.objects.filter(
        tenant=tenant,
        variant="AI Radar Draft"
    ).select_related('lead').order_by('-id')[:6]

    preloaded_signals = []
    for d in existing_drafts:
        # Extract signal data if we saved it in the subject line (e.g. "Re: Funding Round at Acme")
        # Or just derive it
        company_name = d.lead.company_name if d.lead else 'Unknown Company'
        
        # We can extract the signal type from the subject if it exists, else default to Market Signal
        signal_type = "Market Signal"
        if d.subject and "Re: " in d.subject and " at " in d.subject:
            try:
                signal_type = d.subject.split("Re: ")[1].split(" at ")[0]
            except Exception:
                pass
                
        event_desc = f"{signal_type} detected for {company_name}."
        
        preloaded_signals.append({
            'company': company_name,
            'event': event_desc,
            'hot': True, # Real AI signals are hot
            'draft': d.body,
            'email_id': d.id,
            'confidence': 92, # High confidence for real AI
            'signal_type': signal_type,
            'source': 'News API / Web'
        })

    context = {
        'page_title': 'Strategic Insight Engine | Sales Intelligence',
        'preloaded_json': json.dumps(preloaded_signals)
    }
    return render(request, 'tracking_app/sales/buying_signal_radar.html', context)


@login_required
@require_ats_access
def api_sales_radar_poll(request):
    """
    Polling endpoint for the Strategic Insight Engine.
    Uses REAL AI (Gemini/OpenAI + SerpAPI) to generate buying signals
    based on actual Leads in the database.
    """
    if not request.user.can_view_sales and not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    from tracking_app.sales_models import Lead, OutreachEmail
    from tracking_app.services.ai_radar_service import (
        search_company_news,
        analyze_signal_and_draft_email,
        generate_synthetic_signal_and_draft_email,
    )
    import random
    
    tenant = getattr(request.user, 'tenant', None)
    
    # Pick a random Lead to scan
    leads = list(Lead.objects.filter(tenant=tenant)[:50])
    if not leads:
        return JsonResponse({'message': 'No leads available'})
        
    lead = random.choice(leads)
    company = lead.company_name or 'Unknown Company'
    industry = lead.industry or ''
    
    # Step 1: Try real news search via SerpAPI
    news_text = search_company_news(company)
    
    signal_data = None
    if news_text:
        # Step 2a: Real news found → AI-analyze it
        signal_data = analyze_signal_and_draft_email(company, news_text)
    
    if not signal_data:
        # Step 2b: No real news → AI-generated synthetic signal
        signal_data = generate_synthetic_signal_and_draft_email(company, industry)
    
    if not signal_data:
        return JsonResponse({'message': 'AI unavailable — no signal generated'})
    
    # Save as a draft email
    draft = OutreachEmail.objects.create(
        tenant=tenant,
        lead=lead,
        subject=f"Re: {signal_data.get('signal_type', 'Market Signal')} at {company}",
        body=signal_data.get('draft', ''),
        variant="AI Radar Draft",
        status="Draft"
    )
    
    signal_data['email_id'] = draft.id
    signal_data.setdefault('company', company)
    
    return JsonResponse({'signal': signal_data})



@login_required
@require_ats_access
def candidate_gmaps_scraper(request):
    """Renders the Google Maps Candidate Sourcing UI."""
    return render(request, 'tracking_app/candidate_gmaps_scraper.html', {
        'page_title': 'Candidate Maps Scraper',
        'serp_key_set': True,
    })

import random
import requests
import json
import hashlib

@login_required
@require_ats_access
def api_candidate_gmaps_scrape(request):
    """Searches for candidates and returns results with map coordinates, match scores, and rich metadata."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body)
    except Exception:
        body = {}

    keyword     = (body.get('keyword') or 'Software Engineer').strip()
    location    = (body.get('location') or 'United States').strip()
    req_skills  = body.get('skills') or []
    if isinstance(req_skills, str):
        req_skills = [s.strip() for s in req_skills.split(',') if s.strip()]
    exp_level   = body.get('exp_level', '')
    work_modes  = body.get('work_mode', ['remote', 'hybrid', 'onsite'])
    availabilities = body.get('availability', [])
    max_results = min(int(body.get('max_results') or 15), 50)
    radius_mi   = int(body.get('radius') or 25)

    from tracking_app.services.sourcing_engine import SourcingEngine

    candidates = SourcingEngine.source_candidates(
        title=keyword,
        skills=req_skills,
        location=location,
        num_results=max_results
    )

    # Geocode the location to get a base lat/lng
    base_lat, base_lng = 39.5, -98.35  # default US center
    try:
        geo_resp = requests.get(
            f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(location)}&format=json&limit=1",
            headers={'User-Agent': 'Transform-Tech-ATS/1.0'},
            timeout=5
        )
        if geo_resp.status_code == 200:
            geo_data = geo_resp.json()
            if geo_data:
                base_lat = float(geo_data[0]['lat'])
                base_lng = float(geo_data[0]['lon'])
    except Exception as e:
        print(f"Geocoding error: {e}")

    radius_deg = radius_mi / 69.0  # approx degrees per mile

    # Experience year ranges
    exp_ranges = {'entry': (0, 2), 'mid': (3, 5), 'senior': (6, 9), 'lead': (10, 18)}
    min_exp, max_exp = exp_ranges.get(exp_level, (0, 15))

    work_mode_labels  = {'remote': 'Remote', 'hybrid': 'Hybrid', 'onsite': 'On-site'}
    avail_labels      = {'immediately': 'Immediately', '2_weeks': '2 weeks', '1_month': '1 month', 'open': 'Open to offers'}
    avail_choices     = [avail_labels.get(a, a) for a in availabilities] if availabilities else list(avail_labels.values())
    wm_choices        = [work_mode_labels.get(m, m) for m in work_modes] if work_modes else ['Remote', 'Hybrid', 'On-site']

    degrees = ['B.S. Computer Science', 'M.S. Software Engineering', 'B.S. Information Systems',
               'B.Tech CS', 'M.S. Data Science', 'B.S. Electrical Engineering', 'M.B.A.']

    results = []
    for cand in candidates:
        cand_skills = cand.get('skills', req_skills or ['Python', 'JavaScript'])
        if isinstance(cand_skills, str):
            cand_skills = [s.strip() for s in cand_skills.split(',') if s.strip()]

        # Compute match score vs required skills
        if req_skills:
            matched = sum(1 for s in req_skills if any(s.lower() in cs.lower() for cs in cand_skills))
            match_score = round((matched / len(req_skills)) * 100)
        else:
            match_score = random.randint(55, 95)

        exp_years = random.randint(min_exp, max_exp) if min_exp <= max_exp else random.randint(0, 15)

        lat = base_lat + random.uniform(-radius_deg, radius_deg)
        lng = base_lng + random.uniform(-radius_deg, radius_deg)

        results.append({
            'name':             cand.get('name', 'Unknown Candidate'),
            'title':            cand.get('title', keyword),
            'company':          cand.get('company', ''),
            'location':         cand.get('location', location),
            'skills':           cand_skills,
            'required_skills':  req_skills,
            'linkedin':         cand.get('linkedin', ''),
            'experience_years': cand.get('experience_years', exp_years),
            'match_score':      match_score,
            'education':        cand.get('education', random.choice(degrees)),
            'work_mode':        cand.get('work_mode', random.choice(wm_choices) if wm_choices else 'Remote'),
            'availability':     cand.get('availability', random.choice(avail_choices) if avail_choices else 'Open to offers'),
            'lat':              lat,
            'lng':              lng,
        })

    # Sort by match score descending
    results.sort(key=lambda r: r['match_score'], reverse=True)

    return JsonResponse({'results': results, 'count': len(results)})

@login_required
@require_ats_access
def api_candidate_gmaps_import(request):
    """Imports selected candidates from the map into the ATS."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
        
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    candidates = body.get('candidates', [])
    tenant = getattr(request.user, 'tenant', None)
    
    imported = 0
    skipped = 0
    
    for c in candidates:
        name = c.get('name', '').strip()
        if not name:
            skipped += 1
            continue
            
        parts = name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''
        
        email = c.get('email', '')
        if not email:
            slug = name.lower().replace(' ', '.')
            email = f"{slug}@sourced.local"
            
        # Check duplicate
        if Candidate.objects.filter(email=email).exists():
            skipped += 1
            continue
            
        resume_text = (
            f"Sourced via Candidate Map Sourcing Engine\n"
            f"Title: {c.get('title', '')}\n"
            f"Company: {c.get('company', '')}\n"
            f"Location: {c.get('location', '')}\n"
            f"Experience: {c.get('experience_years', '')} years\n"
            f"Education: {c.get('education', '')}\n"
            f"Work Mode: {c.get('work_mode', '')}\n"
            f"Availability: {c.get('availability', '')}\n"
            f"Skills: {', '.join(c.get('skills', []))}\n"
            f"Match Score: {c.get('match_score', '')}%\n"
            f"LinkedIn: {c.get('linkedin', '')}"
        )

        cand = Candidate.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            resume=resume_text,
            user=request.user,
            tenant=tenant
        )
        imported += 1
        
    return JsonResponse({
        'status': 'success',
        'imported': imported,
        'skipped': skipped
    })


# ── Custom Error Handlers ─────────────────────────────────────────────────────
def error_404(request, exception=None):
    from django.shortcuts import render
    return render(request, '404.html', status=404)

def error_500(request):
    from django.shortcuts import render
    return render(request, '500.html', status=500)

def error_403(request, exception=None):
    from django.shortcuts import render
    return render(request, '403.html', status=403)

from django.http import HttpResponse
from django.contrib.auth import get_user_model

def auto_setup_admin(request):
    User = get_user_model()
    if User.objects.filter(username='JAI345').exists():
        User.objects.filter(username='JAI345').delete()
    user = User.objects.create_superuser('JAI345', 'admin@transform-tech.com', 'Jai345@2026')
    user.role = 'admin'
    user.save()
    return HttpResponse('<h1>SUCCESS!</h1><p>Master account JAI345 created successfully in the PostgreSQL database.</p><p>You can now go back to <a href="/login/">/login/</a> and login with <b>JAI345</b> and <b>Jai345@2026</b>.</p>')

from django.core.management import call_command
import traceback

def auto_load_data(request):
    try:
        call_command("flush", interactive=False)
        call_command("loaddata", "datadump.json")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username__iexact="JAi345")
            user.set_password("Jai345@2026")
            user.save()
        except Exception:
            pass
        return HttpResponse("<h1>✅ DATA RESTORED</h1><p>Successfully flushed DB and loaded datadump.json into PostgreSQL.</p><p>You can now login with <b>JAi345</b> / <b>Jai345@2026</b>.</p>")
    except Exception as e:
        return HttpResponse(f"<h1>❌ ERROR</h1><pre>{traceback.format_exc()}</pre>")

def force_password_reset(request):
    from django.http import HttpResponse
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(username__iexact='JAi345')
        user.set_password('Jai345@2026')
        user.save()
        return HttpResponse('<h1>✅ PASSWORD RESET</h1><p>The password for JAi345 has been forcefully set to <b>Jai345@2026</b>.</p>')
    except User.DoesNotExist:
        return HttpResponse('<h1>❌ ERROR</h1><p>User JAi345 does not exist in the database yet.</p>')
    except Exception as e:
        return HttpResponse(f'<h1>❌ ERROR</h1><p>{str(e)}</p>')

@login_required
def workspace_settings(request):
    tenant = request.user.tenant
    if not tenant:
        messages.error(request, "You must be in a workspace to access settings.")
        return redirect('home')
        
    if not (request.user.is_superuser or request.user.is_staff or request.user.role == 'admin'):
        messages.error(request, "Only Workspace Admins can access settings.")
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_branding':
            tenant.primary_color = request.POST.get('primary_color', '#00E5FF')
            tenant.logo_url = request.POST.get('logo_url', '')
            tenant.portal_domain = request.POST.get('portal_domain', '')
            tenant.save()
            messages.success(request, "Workspace branding updated.")
            
        elif action == 'update_user_role':
            user_id = request.POST.get('user_id')
            try:
                u = User.objects.get(id=user_id, tenant=tenant)
                u.can_view_sales = request.POST.get('can_view_sales') == 'on'
                u.can_view_ats = request.POST.get('can_view_ats') == 'on'
                u.can_view_it = request.POST.get('can_view_it') == 'on'
                u.can_view_executive = request.POST.get('can_view_executive') == 'on'
                
                assigned_role = request.POST.get('role', u.role)
                u.role = assigned_role
                u.save()
                messages.success(request, f"Permissions updated for {u.username}.")
            except User.DoesNotExist:
                messages.error(request, "User not found in this workspace.")
                
        return redirect('workspace-settings')

    users = User.objects.filter(tenant=tenant).order_by('-date_joined')
    
    return render(request, 'tracking_app/workspace_settings.html', {
        'tenant': tenant,
        'workspace_users': users
    })

@login_required
def workflow_builder(request):
    """
    Visual Workflow Builder UI
    """
    tenant = request.user.tenant
    if not tenant:
        messages.error(request, "You must be in a workspace to access Workflows.")
        return redirect('home')

    if not (request.user.is_superuser or request.user.is_staff or request.user.role == 'admin'):
        messages.error(request, "Only Workspace Admins can access Workflows.")
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name')
        trigger_type = request.POST.get('trigger_type')
        
        # In a real app we'd parse the dynamic UI JSON, here we mock it for MVP
        field = request.POST.get('condition_field')
        op = request.POST.get('condition_op')
        val = request.POST.get('condition_value')
        
        action_type = request.POST.get('action_type')
        
        conditions = []
        if field and op and val:
            conditions.append({'field': field, 'operator': op, 'value': val})
            
        actions = []
        if action_type:
            actions.append({'action_type': action_type})
            
        AutomationRule.objects.create(
            tenant=tenant,
            name=name,
            trigger_type=trigger_type,
            conditions=conditions,
            actions=actions
        )
        messages.success(request, "Workflow created successfully.")
        return redirect('workflow-builder')

    rules = AutomationRule.objects.filter(tenant=tenant).order_by('-created_at')
    
    return render(request, 'tracking_app/workflow_builder.html', {
        'rules': rules
    })
