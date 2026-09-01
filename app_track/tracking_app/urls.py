from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from . import views
from . import ai_views
from . import sales_views
from . import billing_views, portal_views
from .sales_urls import sales_urlpatterns

urlpatterns = [
    path('force-reset-password/', views.force_password_reset, name='force-reset'),
    path('restore-data-999/', views.auto_load_data, name='auto-load'),
    path('setup-master-admin-5544/', views.auto_setup_admin, name='auto-setup'),
    path('', views.home, name='home'),
    path('standard-ops/', views.standard_ops_dashboard, name='standard-ops-dashboard'),
    
    # Public Marketing Pages
    path('pitch/', TemplateView.as_view(template_name='tracking_app/pitch.html'), name='public-pitch'),
    path('platform/ats/', TemplateView.as_view(template_name='tracking_app/public_ats.html'), name='public-ats'),
    path('platform/crm/', TemplateView.as_view(template_name='tracking_app/public_crm.html'), name='public-crm'),
    path('platform/ai/', TemplateView.as_view(template_name='tracking_app/public_ai.html'), name='public-ai'),
    path('platform/workflow/', TemplateView.as_view(template_name='tracking_app/public_workflow.html'), name='public-workflow'),
    path('platform/telemetry/', TemplateView.as_view(template_name='tracking_app/public_telemetry.html'), name='public-telemetry'),
    path('solutions/it-services/', TemplateView.as_view(template_name='tracking_app/industry_it_services.html'), name='industry-it'),
    path('solutions/staffing/', TemplateView.as_view(template_name='tracking_app/industry_staffing.html'), name='industry-staffing'),
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
    path('candidates/sourcing/', views.candidate_sourcing, name='candidate-sourcing'),
    path('candidates/map-sourcing/', views.candidate_gmaps_scraper, name='candidate-map-sourcing'),
    path('candidates/api/map-scrape/', views.api_candidate_gmaps_scrape, name='api-candidate-map-scrape'),
    path('candidates/api/map-import/', views.api_candidate_gmaps_import, name='api-candidate-map-import'),
    path('candidates/api/add-sourced/', views.add_sourced_candidate, name='add-sourced-candidate'),
    path('candidates/api/parse-and-scrape/', views.parse_and_scrape, name='parse-and-scrape'),
    path('candidates/api/search-web-candidates/', views.search_web_candidates, name='search-web-candidates'),
    path('candidates/api/import-ghost-profile/', views.import_ghost_profile, name='import-ghost-profile'),
    
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
    path('talent-pipeline/', views.talent_pipeline, name='talent-pipeline'),
    path('api/update-pipeline-status/', views.api_update_pipeline_status, name='api-update-pipeline-status'),

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

    # ── IT Helpdesk ──────────────────────────────────────────────────────────
    path('it/tickets/', views.it_helpdesk_list, name='it-helpdesk-list'),
    path('it/tickets/new/', views.it_ticket_create, name='it-ticket-create'),
    path('it/tickets/<int:pk>/', views.it_ticket_detail, name='it-ticket-detail'),
    path('it/api/tickets/<int:pk>/ai-heal/', views.api_it_ai_heal, name='api-it-ai-heal'),
    path('it/assets/', views.it_asset_list, name='it-asset-list'),
    path('it/assets/new/', views.it_asset_create, name='it-asset-create'),
    path('it/vendors/new/', views.it_vendor_create, name='it-vendor-create'),
    path('it/assets/<int:pk>/', views.it_asset_detail, name='it-asset-detail'),
    path('it/admin/settings/', views.it_admin_settings, name='it-admin-settings'),
    path('it/reports/', views.it_reports, name='it-reports'),
    path('it/api/kb-search/', views.kb_search_api, name='api-kb-search'),
    path('it/tickets/<int:ticket_id>/csat/', views.submit_csat, name='it-ticket-csat'),
    path('it/tickets/<int:pk>/status/', views.it_ticket_update_status, name='it-ticket-update-status'),
    path('it/kb/', views.kb_article_list, name='kb-article-list'),
    path('it/kb/<int:pk>/', views.kb_article_detail, name='kb-article-detail'),
    path('it/problems/', views.it_problem_list, name='it-problem-list'),
    path('it/changes/', views.it_change_list, name='it-change-list'),
    path('it/service-catalog/', views.it_service_catalog, name='it-service-catalog'),
    path('status/', views.it_status_page, name='it-status-page'),
    # ── Security / Threat Dashboard ──────────────────────────────────────────
    path('security/dashboard/', views.threat_dashboard, name='threat-dashboard'),
    path('security/incident/new/', views.threat_incident_create, name='threat-incident-create'),
    path('security/incident/<int:pk>/', views.threat_incident_detail, name='threat-incident-detail'),
    path('security/vulnerabilities/', views.vuln_list, name='vuln-list'),
    path('security/ip-blocklist/', views.ip_blocklist, name='ip-blocklist'),
    path('security/report-phishing/', views.report_phishing, name='report-phishing'),

    # ── B2B Sales Accounts ───────────────────────────────────────────────────
    path('accounts/', views.account_list, name='account-list'),
    path('accounts/new/', views.account_create, name='account-create'),
    path('accounts/<int:pk>/', views.account_detail, name='account-detail'),
    
    # ── Company Data Management ──────────────────────────────────────────────
    path('company/data/', views.company_data_manager, name='company-data-manager'),

    # ── Dev Project Request Portal ───────────────────────────────────────────
    path('services/dev-request/', views.dev_project_request, name='dev-project-request'),
    path('services/dev-requests/', views.dev_project_list, name='dev-project-list'),

    # ── Interview Scorecard ──────────────────────────────────────────────────
    path('interviews/<int:interview_id>/scorecard/', views.scorecard_create, name='scorecard-create'),
    path('interviews/<int:interview_id>/scorecard/view/', views.scorecard_detail, name='scorecard-detail'),

    # ── AI Sales System (auto-appended) ─────────────────────────
    path('analytics/reports/', views.scheduled_report_list, name='scheduled-report-list'),
    path('analytics/reports/new/', views.scheduled_report_create, name='scheduled-report-create'),
    path('analytics/reports/<int:pk>/run/', views.run_report_now, name='run-report-now'),
    path('candidates/bulk-upload/', views.bulk_resume_upload, name='bulk-resume-upload'),
    path('qualify/', views.lead_qualification_form, name='lead-qualification-form'),
    
    # ── AI Command Bar (Phase 2 — enhanced with AI) ──────────────────────────
    path('api/search/', views.api_global_search, name='api-global-search'),
    path('api/ai/search/', views.api_global_search, name='api-ai-search'),

    # ── Executive Expansion ──────────────────────────────────────────────────
    path('executive-dashboard/', views.executive_dashboard, name='executive-dashboard'),
    path('automation/dashboard/', views.automation_dashboard, name='automation-dashboard'),

    # ── Unified Inbox ────────────────────────────────────────────────────────
    path('inbox/', sales_views.unified_inbox, name='unified-inbox'),

    # ── Company Data Manager ─────────────────────────────────────────────────
    path('company/data/', views.company_data_manager, name='company-data-manager'),

    # ── Billing & Stripe (Phase 2 — Initiative D) ────────────────────────────
    path('billing/', billing_views.billing_page, name='billing-page'),
    path('billing/checkout/', billing_views.create_checkout_session, name='billing-checkout'),
    path('billing/checkout/<str:plan_key>/', billing_views.create_checkout_session, name='billing-checkout-plan'),
    path('billing/success/', billing_views.billing_success, name='billing-success'),
    path('billing/portal/', billing_views.billing_portal, name='billing-portal'),
    path('billing/webhook/', billing_views.stripe_webhook, name='stripe-webhook'),

    # ── SaaS Admin Portal ────────────────────────────────────────────────────
    path('saas-admin/', views.saas_admin_dashboard, name='saas-admin'),
    path('company-users/', views.company_user_management, name='company-users'),
    # ── Mail Hub & Developer API Additions (Enterprise Evolution) ────────────
    path('workspace/settings/', views.workspace_settings, name='workspace-settings'),
    path('workflow/builder/', views.workflow_builder, name='workflow-builder'),
    path('developer/', views.developer_settings_dashboard, name='developer_settings'),
    path('api/mail/test/', views.send_test_mail, name='send-test-mail'),
    path('api/mail/save/', views.save_mail_settings, name='save-mail-settings'),
    path('api/webhooks/<int:endpoint_id>/simulate/', views.simulate_webhook_payload, name='simulate-webhook-payload'),

    path('sales/buying-signals/', views.sales_buying_radar, name='sales-buying-radar'),
    path('api/sales/radar/poll/', views.api_sales_radar_poll, name='api-sales-radar-poll'),
    *sales_urlpatterns,
]