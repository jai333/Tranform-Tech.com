from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import Http404, JsonResponse
from .models import Candidate, Job, Interview, User, Application, Friendship, Message, Notification, JobSeekerApplication, Note
from .forms import UserRegistrationForm, ProfileUpdateForm, JobSeekerApplicationForm, JobForm
from django.db import models
from datetime import datetime, timedelta
from .utils import generate_meeting_url
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

def home(request):
    return render(request, 'tracking_app/home.html')
# User Authentication Views
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
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
            
    context = {
        'jobs': jobs,
        'selected_job': selected_job,
        'pipeline_data': pipeline_data,
        'status_choices': JobSeekerApplication.STATUS_CHOICES
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

