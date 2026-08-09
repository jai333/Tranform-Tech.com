"""AI Sales System — URL patterns"""

from django.urls import path
from . import sales_views

sales_urlpatterns = [

    # ── Sales Dashboard & Analytics ──────────────────────────────
    path('sales/', sales_views.sales_dashboard, name='sales-dashboard'),
    path('sales/analytics/', sales_views.sales_analytics, name='sales-analytics'),

    # ── Lead Management ──────────────────────────────────────────
    path('sales/leads/', sales_views.lead_list, name='lead-list'),
    path('sales/leads/new/', sales_views.lead_create, name='lead-create'),
    path('sales/leads/import/', sales_views.import_leads, name='import-leads'),
    path('sales/leads/google-maps/', sales_views.gmaps_lead_scraper, name='gmaps-lead-scraper'),
    path('sales/leads/<int:lead_id>/', sales_views.lead_detail, name='lead-detail'),


    # ── Deal Pipeline ─────────────────────────────────────────────
    path('sales/pipeline/', sales_views.deal_pipeline, name='deal-pipeline'),
    path('sales/deals/<int:deal_id>/', sales_views.deal_detail, name='deal-detail'),

    # ── Demo Booking (public) ─────────────────────────────────────
    path('demo/', sales_views.demo_booking_page, name='demo-booking'),

    # ── AI API Endpoints ─────────────────────────────────────────
    path('api/sales/leads/<int:lead_id>/score/', sales_views.api_score_lead, name='api-score-lead'),
    path('api/sales/leads/<int:lead_id>/email/', sales_views.api_generate_email, name='api-generate-email'),
    path('api/sales/emails/<int:email_id>/send/', sales_views.api_send_email, name='api-send-email'),
    path('api/sales/emails/<int:email_id>/classify-reply/', sales_views.api_classify_reply, name='api-classify-reply'),
    path('api/sales/deals/<int:deal_id>/stage/', sales_views.api_update_deal_stage, name='api-update-deal-stage'),
    path('api/sales/deals/<int:deal_id>/next-action/', sales_views.api_get_next_action, name='api-get-next-action'),
    path('api/sales/demo/<int:booking_id>/brief/', sales_views.api_generate_demo_brief, name='api-demo-brief'),
    path('api/sales/alerts/<int:alert_id>/dismiss/', sales_views.api_dismiss_alert, name='api-dismiss-alert'),

    # ── Google Maps Scraper API ───────────────────────────────────
    path('api/sales/gmaps/scrape/', sales_views.gmaps_lead_scraper, name='api-gmaps-scrape'),
    path('api/sales/gmaps/import/', sales_views.api_gmaps_import, name='api-gmaps-import'),

    # ── Email Tracking Pixel (public) ────────────────────────────
    path('t/<str:tracking_id>.gif', sales_views.email_tracking_pixel, name='email-pixel'),

    # ── AI Sales Chat Widget (public) ────────────────────────────
    path('api/sales-chat/', sales_views.api_sales_chat, name='api-sales-chat'),
]
