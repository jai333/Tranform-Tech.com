"""
AI Sales System — Views
Handles: Sales dashboard, lead management, deal pipeline,
         AI chat endpoint, email tracking pixel, demo booking
"""

import json
import uuid
import logging
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import re
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Count, Sum, Avg, Q
from django.contrib import messages

from .sales_models import (
    Lead, EmailSequence, EmailSequenceStep, LeadSequenceEnrollment,
    OutreachEmail, EmailReply, DemoBooking, Deal, DealActivity,
    SalesDailySnapshot, SalesAlert, OnboardingFunnel
)
from .sales_engine import (
    score_lead_icp, generate_cold_email, classify_reply,
    predict_close_probability, generate_next_action,
    generate_sales_alerts, generate_demo_brief,
    generate_onboarding_health_notes, generate_tracking_id,
    _call_openai
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# SALES DASHBOARD (Layer 6)
# ─────────────────────────────────────────────────────────────────

@login_required
def sales_dashboard(request):
    """Main AI Sales Intelligence Dashboard."""
    # Pipeline stages list for visual rendering
    pipeline_stages = []
    total_deals = Deal.objects.count()
    for stage, label in Deal.STAGE_CHOICES:
        count = Deal.objects.filter(stage=stage).count()
        pct = (count / total_deals * 100) if total_deals > 0 else 0
        pipeline_stages.append({
            'key': stage,
            'label': label,
            'count': count,
            'pct': pct
        })

    # Key metrics
    total_leads = Lead.objects.count()
    qualified_leads = Lead.objects.filter(icp_score__gte=65).count()
    active_sequences = LeadSequenceEnrollment.objects.filter(status='active').count()
    demos_this_month = DemoBooking.objects.filter(
        scheduled_at__month=timezone.now().month,
        scheduled_at__year=timezone.now().year
    ).count()
    pipeline_value = Deal.objects.exclude(stage__in=['won', 'lost']).aggregate(
        total=Sum('deal_value_monthly')
    )['total'] or 0
    mrr_won = Deal.objects.filter(stage='won').aggregate(
        total=Sum('deal_value_monthly')
    )['total'] or 0

    # Hot leads (opened 3+ times or icp>=80)
    hot_leads = Lead.objects.filter(
        Q(email_opens__gte=3) | Q(icp_score__gte=80)
    ).exclude(status__in=['converted', 'unsubscribed', 'lost']).order_by('-email_opens', '-icp_score')[:5]

    # Recent deals
    recent_deals = Deal.objects.select_related('lead').exclude(
        stage__in=['won', 'lost']
    ).order_by('-updated_at')[:8]

    # Unread alerts
    alerts = SalesAlert.objects.filter(is_read=False).order_by('-created_at')[:10]

    # Email stats (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    emails_sent = OutreachEmail.objects.filter(sent_at__gte=thirty_days_ago).count()
    emails_opened = OutreachEmail.objects.filter(opened_at__gte=thirty_days_ago).count()
    emails_replied = OutreachEmail.objects.filter(replied_at__gte=thirty_days_ago).count()
    open_rate = round((emails_opened / emails_sent * 100) if emails_sent else 0, 1)
    reply_rate = round((emails_replied / emails_sent * 100) if emails_sent else 0, 1)

    # Recent leads
    recent_leads = Lead.objects.order_by('-created_at')[:6]

    context = {
        'page_title': 'AI Sales Dashboard',
        'pipeline_stages': pipeline_stages,
        'total_leads': total_leads,
        'qualified_leads': qualified_leads,
        'active_sequences': active_sequences,
        'demos_this_month': demos_this_month,
        'pipeline_value': pipeline_value,
        'mrr_won': mrr_won,
        'hot_leads': hot_leads,
        'recent_deals': recent_deals,
        'alerts': alerts,
        'emails_sent': emails_sent,
        'emails_opened': emails_opened,
        'emails_replied': emails_replied,
        'open_rate': open_rate,
        'reply_rate': reply_rate,
        'recent_leads': recent_leads,
    }
    return render(request, 'tracking_app/sales/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────
# LEAD MANAGEMENT (Layer 1)
# ─────────────────────────────────────────────────────────────────

@login_required
def lead_list(request):
    """Paginated, filterable lead list."""
    qs = Lead.objects.all().order_by('-icp_score', '-created_at')

    # Filters
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '')
    min_score = request.GET.get('min_score', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(
            Q(contact_name__icontains=search) |
            Q(company_name__icontains=search) |
            Q(email__icontains=search)
        )
    if min_score:
        qs = qs.filter(icp_score__gte=float(min_score))

    context = {
        'page_title': 'Leads',
        'leads': qs[:100],
        'status_choices': Lead.STATUS_CHOICES,
        'status_filter': status_filter,
        'search': search,
        'min_score': min_score,
        'total_count': qs.count(),
    }
    return render(request, 'tracking_app/sales/leads.html', context)


@login_required
def lead_detail(request, lead_id):
    """Lead detail page with full activity timeline."""
    lead = get_object_or_404(Lead, id=lead_id)
    emails = lead.outreach_emails.order_by('-created_at')
    replies = lead.replies.order_by('-received_at')
    demo_bookings = lead.demo_bookings.order_by('-created_at')
    deal = getattr(lead, 'deal', None)

    context = {
        'page_title': f'{lead.contact_name} @ {lead.company_name}',
        'lead': lead,
        'emails': emails,
        'replies': replies,
        'demo_bookings': demo_bookings,
        'deal': deal,
    }
    return render(request, 'tracking_app/sales/lead_detail.html', context)


@login_required
def lead_create(request):
    """Manually add a new lead."""
    if request.method == 'POST':
        data = request.POST
        lead = Lead.objects.create(
            contact_name=data.get('contact_name', ''),
            email=data.get('email', ''),
            linkedin_url=data.get('linkedin_url', ''),
            phone=data.get('phone', ''),
            company_name=data.get('company_name', ''),
            company_size=data.get('company_size') or None,
            industry=data.get('industry', ''),
            company_website=data.get('company_website', ''),
            current_ats_tool=data.get('current_ats_tool', ''),
            source='manual',
            status='new',
        )
        messages.success(request, f"Lead '{lead.contact_name}' created. Scoring with AI...")
        return redirect('lead-detail', lead_id=lead.id)

    return render(request, 'tracking_app/sales/lead_form.html', {
        'page_title': 'Add New Lead'
    })


# ─────────────────────────────────────────────────────────────────
# DEAL PIPELINE (Layer 5)
# ─────────────────────────────────────────────────────────────────

@login_required
def deal_pipeline(request):
    """Kanban-style deal pipeline view."""
    stages = [s[0] for s in Deal.STAGE_CHOICES]
    pipeline = {}
    for stage in stages:
        pipeline[stage] = Deal.objects.filter(stage=stage).select_related('lead').order_by('-close_probability')

    total_pipeline_value = Deal.objects.exclude(stage__in=['won', 'lost']).aggregate(
        total=Sum('deal_value_monthly')
    )['total'] or 0
    mrr_won = Deal.objects.filter(stage='won').aggregate(
        total=Sum('deal_value_monthly')
    )['total'] or 0

    context = {
        'page_title': 'Deal Pipeline',
        'pipeline': pipeline,
        'stage_labels': dict(Deal.STAGE_CHOICES),
        'total_pipeline_value': total_pipeline_value,
        'mrr_won': mrr_won,
    }
    return render(request, 'tracking_app/sales/pipeline.html', context)


@login_required
def deal_detail(request, deal_id):
    """Deal detail with AI recommendations and activity log."""
    deal = get_object_or_404(Deal, id=deal_id)
    activities = deal.activities.all()[:20]

    context = {
        'page_title': f'Deal: {deal.lead.company_name}',
        'deal': deal,
        'activities': activities,
    }
    return render(request, 'tracking_app/sales/deal_detail.html', context)


# ─────────────────────────────────────────────────────────────────
# API ENDPOINTS — AI Actions
# ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def api_score_lead(request, lead_id):
    """Trigger AI ICP scoring for a lead."""
    lead = get_object_or_404(Lead, id=lead_id)
    try:
        result = score_lead_icp(lead)
        lead.icp_score = result.get('score', 0)
        lead.icp_score_breakdown = result.get('breakdown', {})
        lead.status = 'qualified' if lead.icp_score >= 65 else 'enriched'
        lead.save()

        # Create a Deal if score is high enough
        if lead.icp_score >= 65:
            deal, created = Deal.objects.get_or_create(
                lead=lead,
                defaults={
                    'stage': 'lead',
                    'close_probability': predict_close_probability(
                        type('obj', (object,), {
                            'stage': 'lead', 'days_since_activity': 0,
                            'lead': lead, 'deal_value_monthly': 49
                        })()
                    ),
                    'deal_value_monthly': 49,
                }
            )
            if created:
                DealActivity.objects.create(
                    deal=deal,
                    activity_type='ai_action',
                    description=f"Deal created automatically — ICP score: {lead.icp_score:.0f}/100. {result.get('reason', '')}",
                    is_ai_generated=True,
                )

        return JsonResponse({
            'success': True,
            'score': lead.icp_score,
            'breakdown': lead.icp_score_breakdown,
            'reason': result.get('reason', ''),
            'status': lead.status,
        })
    except Exception as e:
        logger.error("Error scoring lead %s: %s", lead_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_generate_email(request, lead_id):
    """Generate a personalized email for a lead."""
    lead = get_object_or_404(Lead, id=lead_id)
    try:
        data = json.loads(request.body)
        step = int(data.get('step', 1))
        variant = data.get('variant', 'A')

        email_content = generate_cold_email(lead, step_number=step, variant=variant)

        # Save as a draft email
        tracking_id = generate_tracking_id()
        email = OutreachEmail.objects.create(
            lead=lead,
            subject=email_content['subject'],
            body=email_content['body'],
            variant=variant,
            status='draft',
            tracking_pixel_id=tracking_id,
        )

        return JsonResponse({
            'success': True,
            'email_id': email.id,
            'subject': email.subject,
            'body': email.body,
            'tracking_id': tracking_id,
        })
    except Exception as e:
        logger.error("Error generating email for lead %s: %s", lead_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_send_email(request, email_id):
    """Mark an email as sent and dispatch it through SMTP backend (Gmail)."""
    email = get_object_or_404(OutreachEmail, id=email_id)
    try:
        from django.core.mail import send_mail
        
        # Send physical email via configured backend
        send_mail(
            subject=email.subject,
            message=email.body,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[email.lead.email],
            fail_silently=False,
        )

        email.status = 'sent'
        email.sent_at = timezone.now()
        email.save()

        email.lead.last_activity_at = timezone.now()
        email.lead.status = 'in_sequence'
        email.lead.save()

        # Log deal activity
        if hasattr(email.lead, 'deal'):
            DealActivity.objects.create(
                deal=email.lead.deal,
                activity_type='email_sent',
                description=f"Email sent: '{email.subject}'",
            )

        return JsonResponse({'success': True, 'sent_at': email.sent_at.isoformat()})
    except Exception as e:
        logger.error("Error sending email %s: %s", email_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_GET
def email_tracking_pixel(request, tracking_id):
    """Invisible 1x1 pixel — records email open when loaded."""
    try:
        email = OutreachEmail.objects.get(tracking_pixel_id=tracking_id)
        if email.status == 'sent':
            email.status = 'opened'
            email.opened_at = timezone.now()
            email.save()

            # Update lead
            email.lead.email_opens = (email.lead.email_opens or 0) + 1
            email.lead.last_activity_at = timezone.now()
            email.lead.save()

            # Alert if threshold hit
            if email.lead.email_opens >= 3:
                SalesAlert.objects.get_or_create(
                    lead=email.lead,
                    alert_type='hot_lead',
                    is_read=False,
                    defaults={
                        'title': f"{email.lead.contact_name} is hot!",
                        'body': f"Opened your email {email.lead.email_opens} times. Reach out now.",
                    }
                )
    except OutreachEmail.DoesNotExist:
        pass

    # Return transparent 1x1 GIF
    pixel = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
        b'\xFF\xFF\xFF\x00\x00\x00\x21\xF9\x04\x00\x00\x00\x00'
        b'\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
        b'\x44\x01\x00\x3B'
    )
    return HttpResponse(pixel, content_type='image/gif')


@login_required
@require_POST
def api_classify_reply(request, email_id):
    """AI classifies an email reply and drafts a response."""
    email = get_object_or_404(OutreachEmail, id=email_id)
    try:
        data = json.loads(request.body)
        reply_content = data.get('reply_content', '')

        result = classify_reply(reply_content, lead_company=email.lead.company_name)

        # Save reply record
        reply = EmailReply.objects.create(
            email=email,
            lead=email.lead,
            raw_content=reply_content,
            ai_intent=result.get('intent', 'OTHER').lower(),
            ai_response_draft=result.get('response', ''),
        )

        # Update email status
        email.status = 'replied'
        email.replied_at = timezone.now()
        email.save()

        # Update lead status
        email.lead.status = 'replied'
        email.lead.last_activity_at = timezone.now()
        email.lead.save()

        # Handle next action
        next_action = result.get('next_action', 'human_review')
        if next_action == 'remove_lead':
            email.lead.status = 'unsubscribed'
            email.lead.save()

        # Log on deal
        if hasattr(email.lead, 'deal'):
            DealActivity.objects.create(
                deal=email.lead.deal,
                activity_type='email_replied',
                description=f"Reply received. AI intent: {result.get('intent')}. Next: {next_action}",
                is_ai_generated=True,
            )
            if result.get('intent') == 'INTERESTED':
                email.lead.deal.stage = 'replied'
                email.lead.deal.close_probability = 0.25
                email.lead.deal.save()

        return JsonResponse({
            'success': True,
            'reply_id': reply.id,
            'intent': result.get('intent'),
            'response_draft': result.get('response'),
            'next_action': next_action,
        })
    except Exception as e:
        logger.error("Error classifying reply: %s", e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_update_deal_stage(request, deal_id):
    """Update deal stage and recalculate probability."""
    deal = get_object_or_404(Deal, id=deal_id)
    try:
        data = json.loads(request.body)
        old_stage = deal.stage
        new_stage = data.get('stage', deal.stage)

        deal.stage = new_stage
        deal.close_probability = predict_close_probability(deal)
        deal.last_activity_at = timezone.now()

        if new_stage == 'won':
            deal.actual_close_date = timezone.now().date()
            deal.lead.status = 'converted'
            deal.lead.save()
        elif new_stage == 'lost':
            deal.lost_reason = data.get('lost_reason', '')

        deal.save()

        DealActivity.objects.create(
            deal=deal,
            activity_type='stage_changed',
            description=f"Stage changed: {old_stage} → {new_stage}",
        )

        return JsonResponse({
            'success': True,
            'stage': deal.stage,
            'close_probability': deal.close_probability,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_get_next_action(request, deal_id):
    """AI recommends the best next action for a deal."""
    deal = get_object_or_404(Deal, id=deal_id)
    try:
        action = generate_next_action(deal)
        deal.ai_next_action = action
        deal.save()
        return JsonResponse({'success': True, 'next_action': action})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_generate_demo_brief(request, booking_id):
    """Generate AI pre-call brief for a demo."""
    booking = get_object_or_404(DemoBooking, id=booking_id)
    try:
        brief = generate_demo_brief(booking)
        booking.ai_prep_notes = brief
        booking.save()
        return JsonResponse({'success': True, 'brief': brief})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_dismiss_alert(request, alert_id):
    """Mark a sales alert as read."""
    alert = get_object_or_404(SalesAlert, id=alert_id)
    alert.is_read = True
    alert.save()
    return JsonResponse({'success': True})


# ─────────────────────────────────────────────────────────────────
# AI SALES CHAT (Website Widget — Layer 3)
# ─────────────────────────────────────────────────────────────────

SALES_CHAT_SYSTEM_PROMPT = """
You are Alex, a friendly sales assistant for Transform.io — an AI-powered ATS and CRM
for recruiting teams and agencies.

Your goals:
1. Understand the visitor's recruiting challenges
2. Qualify them naturally (team size, current tools, main pain)
3. Get them excited about Transform.io
4. Book a 15-minute demo

Key features to highlight when relevant:
- AI resume parsing (saves 3 hrs/week per recruiter)
- Smart candidate-job matching score
- Automated interview scheduling
- Real-time hiring pipeline dashboard

Rules:
- Never discuss exact pricing — say "Our plans start from $49/mo, happy to share more on a call"
- Keep responses under 80 words
- Ask ONE question at a time
- Be human, warm, and helpful — not salesy
- If they want a demo, say: "Great! You can book directly at: https://transformio.ai/demo"
"""


@csrf_exempt
@require_POST
def api_sales_chat(request):
    """Website AI sales chat endpoint."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        history = data.get('history', [])  # List of {role, content}

        if not message:
            return JsonResponse({'error': 'No message provided'}, status=400)

        # Capture inbound lead info if provided
        visitor_name = data.get('visitor_name', '')
        visitor_email = data.get('visitor_email', '')
        if visitor_email:
            Lead.objects.get_or_create(
                email=visitor_email,
                defaults={
                    'contact_name': visitor_name or 'Website Visitor',
                    'company_name': 'Unknown',
                    'source': 'inbound',
                    'status': 'new',
                }
            )

        # Build messages with history
        import os
        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            return JsonResponse({
                'reply': "Hi! I'm Alex from Transform.io. I'd love to help you find the right plan. Could you tell me a bit about your recruiting team?",
                'source': 'fallback'
            })

        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        msgs = [{"role": "system", "content": SALES_CHAT_SYSTEM_PROMPT}]
        for h in history[-8:]:  # Keep last 8 exchanges
            msgs.append({"role": h.get('role', 'user'), "content": h.get('content', '')})
        msgs.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=msgs,
            temperature=0.8,
            max_tokens=200,
        )
        reply = response.choices[0].message.content.strip()

        return JsonResponse({'reply': reply, 'source': 'ai'})

    except Exception as e:
        logger.error("Sales chat error: %s", e)
        return JsonResponse({
            'reply': "Thanks for reaching out! Let me connect you with our team — book a quick demo at transformio.ai/demo",
            'source': 'error'
        })


# ─────────────────────────────────────────────────────────────────
# DEMO BOOKING (Layer 4)
# ─────────────────────────────────────────────────────────────────

def demo_booking_page(request):
    """Public demo booking landing page."""
    if request.method == 'POST':
        data = request.POST
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()
        company = data.get('company', '').strip()
        team_size = data.get('team_size') or None
        current_ats = data.get('current_ats', '')
        pain = data.get('pain_point', '')

        # Get or create lead
        lead, _ = Lead.objects.get_or_create(
            email=email,
            defaults={
                'contact_name': name,
                'company_name': company or 'Unknown',
                'source': 'inbound',
                'status': 'demo_booked',
            }
        )
        if company:
            lead.company_name = company
        lead.status = 'demo_booked'
        lead.current_ats_tool = current_ats
        lead.last_activity_at = timezone.now()
        lead.save()

        # Create demo booking
        booking = DemoBooking.objects.create(
            lead=lead,
            scheduled_at=timezone.now() + timedelta(days=2),  # placeholder
            team_size=int(team_size) if team_size else None,
            current_ats=current_ats,
            main_pain_point=pain,
            status='scheduled',
        )

        # Create or update deal
        deal, _ = Deal.objects.get_or_create(
            lead=lead,
            defaults={
                'stage': 'demo_booked',
                'deal_value_monthly': 49,
                'close_probability': 0.35,
            }
        )
        deal.stage = 'demo_booked'
        deal.last_activity_at = timezone.now()
        deal.save()

        # Alert
        SalesAlert.objects.create(
            alert_type='demo_reminder',
            title=f"New demo booked: {name} @ {company}",
            body=f"Pain: {pain} | Team size: {team_size} | Current ATS: {current_ats}",
            lead=lead,
            deal=deal,
        )

        return render(request, 'tracking_app/sales/demo_confirmed.html', {
            'booking': booking,
            'lead': lead,
        })

    return render(request, 'tracking_app/sales/demo_booking.html', {
        'page_title': 'Book a Free Demo — Transform.io',
    })


# ─────────────────────────────────────────────────────────────────
# ANALYTICS SUMMARY
# ─────────────────────────────────────────────────────────────────

@login_required
def sales_analytics(request):
    """Revenue and funnel analytics view."""
    from django.db.models.functions import TruncDate

    thirty_days_ago = timezone.now() - timedelta(days=30)

    daily_emails = OutreachEmail.objects.filter(
        sent_at__gte=thirty_days_ago
    ).annotate(date=TruncDate('sent_at')).values('date').annotate(
        sent=Count('id'),
        opened=Count('id', filter=Q(status__in=['opened', 'clicked', 'replied'])),
        replied=Count('id', filter=Q(status='replied')),
    ).order_by('date')

    funnel = {
        'leads': Lead.objects.count(),
        'qualified': Lead.objects.filter(icp_score__gte=65).count(),
        'in_sequence': Lead.objects.filter(status='in_sequence').count(),
        'replied': Lead.objects.filter(status='replied').count(),
        'demo_booked': Lead.objects.filter(status='demo_booked').count(),
        'converted': Lead.objects.filter(status='converted').count(),
    }

    context = {
        'page_title': 'Sales Analytics',
        'daily_emails': list(daily_emails),
        'funnel': funnel,
        'mrr': Deal.objects.filter(stage='won').aggregate(total=Sum('deal_value_monthly'))['total'] or 0,
    }
    return render(request, 'tracking_app/sales/analytics.html', context)


# ─────────────────────────────────────────────────────────────────
# LEAD IMPORT (CSV / Paste)
# ─────────────────────────────────────────────────────────────────

import csv
import io

@login_required
def import_leads(request):
    """
    Import leads from a pasted CSV block or an uploaded CSV file.

    Accepted CSV columns (case-insensitive, any order):
        contact_name / name, email, company_name / company,
        phone, linkedin_url / linkedin, industry,
        company_location / location, status, source
    """

    if request.method == 'GET':
        return render(request, 'tracking_app/sales/import_leads.html', {
            'page_title': 'Import Leads',
        })

    # ── Resolve raw CSV text ──────────────────────────────────────
    raw_text = ''
    uploaded_file = request.FILES.get('csv_file')
    if uploaded_file:
        try:
            raw_text = uploaded_file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            raw_text = uploaded_file.read().decode('latin-1')
    else:
        raw_text = request.POST.get('csv_text', '').strip()

    if not raw_text:
        messages.error(request, 'No data provided. Please upload a CSV file or paste CSV text.')
        return redirect('import-leads')

    # ── Parse CSV ─────────────────────────────────────────────────
    reader = csv.DictReader(io.StringIO(raw_text))
    # Normalise headers to lowercase, strip whitespace
    try:
        reader.fieldnames = [h.strip().lower().replace(' ', '_') for h in reader.fieldnames]
    except TypeError:
        messages.error(request, 'Could not read headers. Make sure the first line contains column names.')
        return redirect('import-leads')

    # Column aliases
    ALIASES = {
        'name': 'contact_name',
        'full_name': 'contact_name',
        'company': 'company_name',
        'organisation': 'company_name',
        'organization': 'company_name',
        'linkedin': 'linkedin_url',
        'linkedin_profile': 'linkedin_url',
        'location': 'company_location',
        'city': 'company_location',
    }
    reader.fieldnames = [ALIASES.get(h, h) for h in reader.fieldnames]

    created, skipped, errors = 0, 0, []
    for row in reader:
        contact_name = (row.get('contact_name') or '').strip()
        email = (row.get('email') or '').strip().lower()
        company_name = (row.get('company_name') or '').strip()

        if not email:
            errors.append(f'Row missing email: {dict(row)}')
            continue
        if not contact_name:
            contact_name = email.split('@')[0].replace('.', ' ').title()

        status = (row.get('status') or 'new').strip().lower()
        valid_statuses = [s[0] for s in Lead.STATUS_CHOICES]
        if status not in valid_statuses:
            status = 'new'

        source = (row.get('source') or 'manual').strip().lower()
        valid_sources = [s[0] for s in Lead.SOURCE_CHOICES]
        if source not in valid_sources:
            source = 'manual'

        try:
            lead, created_flag = Lead.objects.get_or_create(
                email=email,
                defaults={
                    'contact_name': contact_name,
                    'company_name': company_name or 'Unknown',
                    'phone': (row.get('phone') or '').strip() or None,
                    'linkedin_url': (row.get('linkedin_url') or '').strip() or None,
                    'industry': (row.get('industry') or '').strip() or None,
                    'company_location': (row.get('company_location') or '').strip() or None,
                    'status': status,
                    'source': source,
                }
            )
            if created_flag:
                created += 1
            else:
                skipped += 1
        except Exception as exc:
            errors.append(f'{email}: {exc}')

    # Build result message
    parts = []
    if created:
        parts.append(f'✅ {created} lead{"s" if created != 1 else ""} imported successfully.')
    if skipped:
        parts.append(f'⚠️ {skipped} duplicate{"s" if skipped != 1 else ""} skipped (already exist).')
    if errors:
        parts.append(f'❌ {len(errors)} error{"s" if len(errors) != 1 else ""} encountered.')

    msg = ' '.join(parts) if parts else 'Nothing to import.'

    if created:
        messages.success(request, msg)
    elif skipped and not errors:
        messages.warning(request, msg)
    else:
        messages.error(request, msg)

    for err in errors[:5]:   # show at most 5 individual errors
        messages.warning(request, err)

    return redirect('lead-list')


# ── UNIFIED INBOX (TWO-WAY EMAIL) ────────────────────────────────────────

@login_required
def unified_inbox(request):
    """A centralized view of all communications (OutreachEmails, Replies, etc)."""
    from .sales_models import OutreachEmail, EmailReply
    from .models import Lead
    
    if request.method == 'POST':
        reply_text = request.POST.get('reply_text')
        lead_id = request.POST.get('lead_id')
        subject = request.POST.get('subject', 'Re: ')
        
        if reply_text and lead_id:
            lead = Lead.objects.filter(id=lead_id).first()
            if lead:
                OutreachEmail.objects.create(
                    lead=lead,
                    subject=subject,
                    body=reply_text,
                    status='sent'
                )
                from django.contrib import messages
                messages.success(request, "Reply sent successfully.")
                from django.shortcuts import redirect
                return redirect('unified-inbox')
    
    # Get recent sent emails
    sent_emails = OutreachEmail.objects.all().order_by('-id')[:20]
    
    # Get recent replies (incoming)
    replies = EmailReply.objects.all().order_by('-id')[:20]
    
    # Combine and sort them by date (mocking a unified stream)
    inbox_items = []
    
    for email in sent_emails:
        inbox_items.append({
            'type': 'sent',
            'id': email.id,
            'lead_id': email.lead_id if email.lead else '',
            'subject': email.subject,
            'preview': email.body[:100] if email.body else "No content",
            'full_body': email.body or "",
            'date': email.id,  # Fallback sorting since we don't have sent_at
            'contact': f"To: {email.lead.email if email.lead else 'Unknown'}",
            'status': email.status
        })
        
    for reply in replies:
        inbox_items.append({
            'type': 'received',
            'id': reply.id,
            'lead_id': reply.email.lead_id if reply.email and reply.email.lead else '',
            'subject': f"Re: {reply.email.subject if reply.email else 'Incoming'}",
            'preview': reply.raw_content[:100] if reply.raw_content else "No content",
            'full_body': reply.raw_content or "",
            'date': reply.id,
            'contact': f"From: {reply.email.lead.email if reply.email and reply.email.lead else 'Unknown'}",
            'status': 'received'
        })
        
    inbox_items.sort(key=lambda x: x['date'], reverse=True)
    
    context = {
        'inbox_items': inbox_items,
        'page_title': 'Unified Inbox',
    }
    return render(request, 'tracking_app/sales/unified_inbox.html', context)
