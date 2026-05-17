from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from . import views
from . import ai_views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Public Marketing Pages
    path('platform/ats/', TemplateView.as_view(template_name='tracking_app/public_ats.html'), name='public-ats'),
    path('platform/crm/', TemplateView.as_view(template_name='tracking_app/public_crm.html'), name='public-crm'),
    path('platform/ai/', TemplateView.as_view(template_name='tracking_app/public_ai.html'), name='public-ai'),
    path('platform/workflow/', TemplateView.as_view(template_name='tracking_app/public_workflow.html'), name='public-workflow'),
    path('platform/telemetry/', TemplateView.as_view(template_name='tracking_app/public_telemetry.html'), name='public-telemetry'),
    path('solutions/tech/', TemplateView.as_view(template_name='tracking_app/industry_tech.html'), name='industry-tech'),
    path('solutions/healthcare/', TemplateView.as_view(template_name='tracking_app/industry_health.html'), name='industry-health'),
    path('solutions/executive/', TemplateView.as_view(template_name='tracking_app/industry_exec.html'), name='industry-exec'),
    path('roles/agency/', TemplateView.as_view(template_name='tracking_app/role_agency.html'), name='role-agency'),
    path('roles/internal/', TemplateView.as_view(template_name='tracking_app/role_internal.html'), name='role-internal'),
    path('roles/manager/', TemplateView.as_view(template_name='tracking_app/role_manager.html'), name='role-manager'),
    path('resources/blog/', TemplateView.as_view(template_name='tracking_app/public_blog.html'), name='public-blog'),

    # Authentication URLs
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='tracking_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='tracking_app/logout.html'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('public-profile/<str:username>/', views.public_profile, name='public-profile'),
    
    # Friend request URLs
    path('friends/', views.friend_list, name='friend-list'),
    path('send-friend-request/<int:user_id>/', views.send_friend_request, name='send-friend-request'),
    path('accept-friend-request/<int:request_id>/', views.accept_friend_request, name='accept-friend-request'),
    path('reject-friend-request/<int:request_id>/', views.reject_friend_request, name='reject-friend-request'),
    
    # Chat URLs
    path('chat/<str:username>/', views.chat, name='chat'),
    path('send-message/<int:friendship_id>/', views.send_message, name='send-message'),
    
    # Notification URLs
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark-notification-read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark-all-notifications-read'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete-notification'),
    path('notifications/count/', views.notifications_count, name='notifications-count'),
    path('api/notifications/', views.get_notifications, name='get-notifications'),
    
    # Candidate URLs
    path('candidates/', views.CandidateListView.as_view(), name='candidate-list'),
    path('candidates/new/', views.CandidateCreateView.as_view(), name='candidate-create'),
    path('candidates/<int:pk>/', views.CandidateDetailView.as_view(), name='candidate-detail'),
    path('candidates/<int:pk>/update/', views.CandidateUpdateView.as_view(), name='candidate-update'),
    path('candidates/<int:pk>/delete/', views.CandidateDeleteView.as_view(), name='candidate-delete'),
    
    # Job URLs
    path('jobs/', views.JobListView.as_view(), name='job-list'),
    path('jobs/new/', views.JobCreateView.as_view(), name='job-create'),
    path('jobs/<int:pk>/', views.JobDetailView.as_view(), name='job-detail'),
    path('jobs/<int:pk>/update/', views.JobUpdateView.as_view(), name='job-update'),
    path('jobs/<int:pk>/delete/', views.JobDeleteView.as_view(), name='job-delete'),
    
    # Application URLs
    path('applications/', views.ApplicationListView.as_view(), name='application-list'),
    path('applications/new/', views.ApplicationCreateView.as_view(), name='application-create'),
    path('applications/<int:application_id>/', views.application_detail, name='application-detail'),
    path('applications/<int:pk>/update/', views.ApplicationUpdateView.as_view(), name='application-update'),
    path('applications/<int:pk>/delete/', views.ApplicationDeleteView.as_view(), name='application-delete'),
    
    # Interview URLs
    path('interviews/', views.InterviewListView.as_view(), name='interview-list'),
    path('interviews/new/', views.InterviewCreateView.as_view(), name='interview-create'),
    path('interviews/<int:pk>/', views.InterviewDetailView.as_view(), name='interview-detail'),
    path('interviews/<int:pk>/update/', views.InterviewUpdateView.as_view(), name='interview-update'),
    path('interviews/<int:pk>/delete/', views.InterviewDeleteView.as_view(), name='interview-delete'),

    # Job Applications URLs for Job Seekers
    path('jobs/<int:job_id>/apply/', views.apply_for_job, name='apply-for-job'),
    path('my-applications/', views.my_applications, name='my-applications'),
    path('application-detail/<int:application_id>/', views.application_detail, name='application-detail'),
    path('withdraw-application/<int:application_id>/', views.withdraw_application, name='withdraw-application'),
    path('my-interviews/', views.my_interviews, name='my-interviews'),
    path('my-interview/<int:interview_id>/', views.my_interview_detail, name='my-interview-detail'),

    # Job Applications URLs for Recruiters
    path('job-applications/', views.JobApplicationsListView.as_view(), name='job-applications-list'),
    path('update-application-status/<int:application_id>/', views.update_application_status, name='update-application-status'),

    # Note URLs
    path('notes/create/', views.NoteCreateView.as_view(), name='note-create'),
    path('notes/<int:pk>/update/', views.NoteUpdateView.as_view(), name='note-update'),
    path('notes/<int:pk>/delete/', views.NoteDeleteView.as_view(), name='note-delete'),
    
    # AI/ML Features URLs
    path('api/parse-resume/', ai_views.parse_resume_api, name='parse-resume-api'),
    path('api/calculate-job-match/', ai_views.calculate_job_match_api, name='calculate-job-match-api'),
    path('api/jobs/', ai_views.get_jobs_api, name='get-jobs-api'),
    path('api/candidate/<int:candidate_id>/matches/', ai_views.get_candidate_matches, name='get-candidate-matches'),
    path('api/job/<int:job_id>/candidates/', ai_views.get_job_candidates, name='get-job-candidates'),
    path('api/save-search/', ai_views.save_advanced_search, name='save-advanced-search'),
    path('api/candidate/<int:candidate_id>/ai-summary/', ai_views.get_candidate_ai_summary, name='get-candidate-ai-summary'),
    path('candidate/<int:candidate_id>/ai-profile/', ai_views.candidate_detail_with_ai, name='candidate-ai-profile'),
    path('ai-pipeline/', ai_views.ai_pipeline_dashboard, name='ai-pipeline-dashboard'),
    path('add-ons/', views.service_addons_view, name='service-addons'),
]