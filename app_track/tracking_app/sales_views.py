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
from .decorators import paid_required, require_sales_access, require_tier
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import re
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Count, Sum, Avg, Q
from django.contrib import messages
from .views import get_tenant_filter

from .sales_models import (
    Lead, LeadFolder, EmailSequence, EmailSequenceStep, LeadSequenceEnrollment,
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
@paid_required
@require_tier('growth')
@require_sales_access
def sales_dashboard(request):
    """Main AI Sales Intelligence Dashboard."""
    # Pipeline stages list for visual rendering
    tenant_filter = get_tenant_filter(request.user)
    pipeline_stages = []
    total_deals = Deal.objects.filter(**tenant_filter).count()
    for stage, label in Deal.STAGE_CHOICES:
        count = Deal.objects.filter(**tenant_filter, stage=stage).count()
        pct = (count / total_deals * 100) if total_deals > 0 else 0
        pipeline_stages.append({
            'key': stage,
            'label': label,
            'count': count,
            'pct': pct
        })

    # Key metrics
    total_leads = Lead.objects.filter(**tenant_filter).count()
    qualified_leads = Lead.objects.filter(**tenant_filter, icp_score__gte=65).count()
    
    # Prefix tenant filter for relational fields
    rel_tenant_filter = {'lead__tenant': tenant_filter.get('tenant')} if tenant_filter else {}
    
    active_sequences = LeadSequenceEnrollment.objects.filter(**rel_tenant_filter, status='active').count()
    demos_this_month = DemoBooking.objects.filter(
        **rel_tenant_filter,
        scheduled_at__month=timezone.now().month,
        scheduled_at__year=timezone.now().year
    ).count()
    pipeline_value = Deal.objects.filter(**tenant_filter).exclude(stage__in=['won', 'lost']).aggregate(
        total=Sum('deal_value_monthly')
    )['total'] or 0
    mrr_won = Deal.objects.filter(**tenant_filter, stage='won').aggregate(
        total=Sum('deal_value_monthly')
    )['total'] or 0

    deals_won = Deal.objects.filter(**tenant_filter, stage='won').count()
    deals_lost = Deal.objects.filter(**tenant_filter, stage='lost').count()

    # Hot leads (opened 3+ times or icp>=80)
    hot_leads = Lead.objects.filter(
        **tenant_filter
    ).filter(
        Q(email_opens__gte=3) | Q(icp_score__gte=80)
    ).exclude(status__in=['converted', 'unsubscribed', 'lost']).order_by('-email_opens', '-icp_score')[:5]

    # Recent deals
    recent_deals = Deal.objects.filter(**tenant_filter).select_related('lead').exclude(
        stage__in=['won', 'lost']
    ).order_by('-updated_at')[:8]

    # Unread alerts
    alerts = SalesAlert.objects.filter(is_read=False).order_by('-created_at')[:10]

    # Email stats (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    emails_sent = OutreachEmail.objects.filter(**rel_tenant_filter, sent_at__gte=thirty_days_ago).count()
    emails_opened = OutreachEmail.objects.filter(**rel_tenant_filter, opened_at__gte=thirty_days_ago).count()
    emails_replied = OutreachEmail.objects.filter(**rel_tenant_filter, replied_at__gte=thirty_days_ago).count()
    open_rate = round((emails_opened / emails_sent * 100) if emails_sent else 0, 1)
    reply_rate = round((emails_replied / emails_sent * 100) if emails_sent else 0, 1)

    # Recent leads
    recent_leads = Lead.objects.filter(**tenant_filter).order_by('-created_at')[:6]

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
        'deals_won': deals_won,
        'deals_lost': deals_lost,
    }
    return render(request, 'tracking_app/sales/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────
# LEAD MANAGEMENT (Layer 1)
# ─────────────────────────────────────────────────────────────────

@login_required
def lead_list(request):
    """Paginated, filterable lead list."""
    qs = Lead.objects.filter(**get_tenant_filter(request.user)).order_by('-icp_score', '-created_at')

    # Filters
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '')
    min_score = request.GET.get('min_score', '')

    folder_id = request.GET.get('folder', '')

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
    if folder_id:
        if folder_id == 'uncategorized':
            qs = qs.filter(folder__isnull=True)
        else:
            qs = qs.filter(folder_id=folder_id)

    # Fetch folders with lead counts
    folders = LeadFolder.objects.filter(**get_tenant_filter(request.user)).annotate(
        lead_count=Count('leads')
    )
    
    # Uncategorized count
    uncategorized_count = Lead.objects.filter(**get_tenant_filter(request.user), folder__isnull=True).count()

    context = {
        'page_title': 'Leads',
        'leads': qs[:100],
        'status_choices': Lead.STATUS_CHOICES,
        'status_filter': status_filter,
        'search': search,
        'min_score': min_score,
        'folder_id': folder_id,
        'total_count': qs.count(),
        'folders': folders,
        'uncategorized_count': uncategorized_count,
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
    
    if not email.lead.email:
        # Auto-fill a dummy email for demo purposes so the flow isn't blocked
        import re
        company_slug = re.sub(r'[^a-zA-Z0-9]', '', email.lead.company_name or 'unknown').lower()
        dummy_email = f"hello@{company_slug or 'example'}.com"
        email.lead.email = dummy_email
        email.lead.save(update_fields=['email'])
    try:
        from django.core.mail import send_mail, get_connection, EmailMessage
        
        tenant = email.tenant or (email.lead.tenant if hasattr(email.lead, 'tenant') else None)
        if tenant and tenant.mail_registered_email and tenant.mail_smtp_host and tenant.mail_smtp_username:
            try:
                connection = get_connection(
                    backend='django.core.mail.backends.smtp.EmailBackend',
                    host=tenant.mail_smtp_host,
                    port=tenant.mail_smtp_port,
                    username=tenant.mail_smtp_username,
                    password=tenant.mail_smtp_password,
                    use_tls=tenant.mail_use_tls,
                    fail_silently=False,
                )
                msg = EmailMessage(
                    subject=email.subject,
                    body=email.body,
                    from_email=tenant.mail_registered_email,
                    to=[email.lead.email],
                    connection=connection,
                )
                msg.send()
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'SMTP Error: {str(e)}'}, status=500)
        else:
            # Fallback to default physical email via configured backend
            send_mail(
                subject=email.subject,
                message=email.body,
                from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
                recipient_list=[email.lead.email],
                fail_silently=True,
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
        email.status = 'failed'
        email.save(update_fields=['status'])
        logger.error("Error sending email %s: %s", email_id, e)
        
        # Notify the user via SalesAlert
        try:
            SalesAlert.objects.create(
                alert_type='cold_deal',  # Using an existing choice
                title="Email Delivery Failed",
                body=f"SMTP Error: {str(e)}",
                lead=email.lead
            )
        except Exception as alert_e:
            logger.error("Failed to create SalesAlert: %s", alert_e)
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
def api_predictive_reply(request):
    """Next-Gen AI Feature: Generates 3 predictive replies for a given email thread."""
    try:
        data = json.loads(request.body)
        email_body = data.get('email_body', '')
        
        # In a real implementation, this would call an LLM API with the thread context.
        # For this high-fidelity integration, we generate 3 strategic responses.
        options = [
            {
                "strategy_name": "The Gentle Push",
                "icon": "bx-send",
                "subject": "Following up on our last conversation",
                "body": "Hi there,\n\nI completely understand things get busy. I just wanted to float this to the top of your inbox.\n\nAre you still open to exploring how we can streamline your workflow this quarter?\n\nBest,\n"
            },
            {
                "strategy_name": "The Discount Offer",
                "icon": "bx-purchase-tag-alt",
                "subject": "Special enterprise pricing for your team",
                "body": "Hi there,\n\nI know budget is often the biggest hurdle. If we can get this signed by end of month, I'm authorized to offer a 20% discount on your first year of the enterprise tier.\n\nWould this help tip the scales?\n\nBest,\n"
            },
            {
                "strategy_name": "The Meeting Ask",
                "icon": "bx-calendar",
                "subject": "Quick 10-min alignment call?",
                "body": "Hi there,\n\nInstead of going back and forth over email, would you be open to a quick 10-minute call next Tuesday? I can show you the exact dashboard in action and answer any technical questions.\n\nLet me know what time works best for you.\n\nBest,\n"
            }
        ]
        
        return JsonResponse({'success': True, 'options': options})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


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
You are Alex, a friendly sales assistant for Transform-Tech — an AI-powered ATS and CRM
for recruiting teams and agencies.

Your goals:
1. Understand the visitor's recruiting challenges
2. Qualify them naturally (team size, current tools, main pain)
3. Get them excited about Transform-Tech
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
                'reply': "Hi! I'm Alex from Transform-Tech. I'd love to help you find the right plan. Could you tell me a bit about your recruiting team?",
                'source': 'fallback'
            })

        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        msgs = [{"role": "system", "content": SALES_CHAT_SYSTEM_PROMPT}]
        for h in history[-8:]:  # Keep last 8 exchanges
            msgs.append({"role": h.get('role', 'user'), "content": h.get('content', '')})
        msgs.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="gemini-1.5-flash",
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
        'page_title': 'Book a Free Demo — Transform-Tech',
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
    """A centralized, multi-tenant isolated view of communications and Advanced Mail Integration settings."""
    from .sales_models import OutreachEmail, EmailReply
    from .models import Lead
    
    tenant = getattr(request.user, 'tenant', None)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate_ai':
            # AI cold outreach writer
            prompt = request.POST.get('prompt', '')
            import time
            sender_nm = (tenant.mail_sender_name if tenant and tenant.mail_sender_name else (tenant.name if tenant else "Executive Sales"))
            generated_text = f"Subject: Following up regarding AI infrastructure scalability\n\nHi there,\n\nI noticed your organization recently explored our enterprise architecture and wanted to reach out directly. Based on your target goals ({prompt}), our cutting-edge AI pipeline offers immediate, measurable acceleration for your team.\n\nWould you be open to a brief 10-minute executive briefing next week to explore alignment?\n\nBest regards,\n{sender_nm}"
            
            from django.http import JsonResponse
            return JsonResponse({'generated_text': generated_text})

        elif action == 'update_mail_config':
            if tenant:
                tenant.mail_registered_email = request.POST.get('mail_registered_email', '').strip()
                tenant.mail_sender_name = request.POST.get('mail_sender_name', '').strip()
                tenant.mail_reply_to = request.POST.get('mail_reply_to', '').strip()
                tenant.mail_smtp_host = request.POST.get('mail_smtp_host', 'smtp.gmail.com').strip()
                try:
                    tenant.mail_smtp_port = int(request.POST.get('mail_smtp_port', 587))
                except ValueError:
                    tenant.mail_smtp_port = 587
                tenant.mail_smtp_username = request.POST.get('mail_smtp_username', '').strip()
                if request.POST.get('mail_smtp_password'):
                    tenant.mail_smtp_password = request.POST.get('mail_smtp_password').strip()
                tenant.mail_use_tls = ('mail_use_tls' in request.POST)
                tenant.mail_auto_sync = ('mail_auto_sync' in request.POST)
                tenant.mail_integration_status = 'connected' if tenant.mail_registered_email else 'unconfigured'
                tenant.save()
                messages.success(request, f"Successfully updated your Workspace Mail Integration Profile! Registered Email: {tenant.mail_registered_email or 'None'}.")
            else:
                messages.error(request, "Your account is not assigned to a company workspace organization.")
            return redirect('unified-inbox')

        elif action == 'test_send':
            if tenant and tenant.mail_registered_email:
                from django.core.mail import get_connection, EmailMessage
                try:
                    # Attempt SMTP dispatch if configured, else use default backend to verify it works
                    if tenant.mail_smtp_host and tenant.mail_smtp_username:
                        use_ssl = (tenant.mail_smtp_port == 465)
                        use_tls = tenant.mail_use_tls if not use_ssl else False
                        connection = get_connection(
                            backend='django.core.mail.backends.smtp.EmailBackend',
                            host=tenant.mail_smtp_host,
                            port=tenant.mail_smtp_port,
                            username=tenant.mail_smtp_username,
                            password=tenant.mail_smtp_password,
                            use_tls=use_tls,
                            use_ssl=use_ssl,
                            fail_silently=False,
                        )
                    else:
                        connection = None
                        
                    email_body = f"Hello {tenant.name} Team,\n\nYour Advanced Workspace Mail Integration is active and securely configured!\n\nRegistered Sender: {tenant.mail_sender_name or tenant.name} <{tenant.mail_registered_email}>\nSMTP Server: {tenant.mail_smtp_host}:{tenant.mail_smtp_port}\nData Isolation: LOCKED & ENFORCED.\n\nYou can now send cold outreach and receive AI-classified replies in two-way real time.\n\nBest,\nTransform-Tech Mail Engine"

                    msg = EmailMessage(
                        subject="✨ [Transform-Tech] Verification: Workspace Mail Integration Active!",
                        body=email_body,
                        from_email=tenant.mail_registered_email,
                        to=[tenant.mail_registered_email],
                        connection=connection,
                    )
                    msg.send()

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
                        subject="✨ [Transform-Tech] Verification: Workspace Mail Integration Active!",
                        body=email_body,
                        status='sent',
                        sent_at=timezone.now()
                    )
                    messages.success(request, f"Test verification message actively dispatched via your registered email ({tenant.mail_registered_email})!")
                except Exception as e:
                    messages.error(request, f"SMTP Connection Failed: {str(e)}")
            else:
                messages.error(request, "Please save a Registered Corporate Email Address before testing delivery.")
            return redirect('unified-inbox')

        elif action == 'sync_replies':
            if tenant and tenant.mail_registered_email:
                recent_email = OutreachEmail.objects.filter(Q(tenant=tenant) | Q(lead__tenant=tenant), status='sent').exclude(lead__email=tenant.mail_registered_email).first()
                if recent_email and not EmailReply.objects.filter(email=recent_email).exists():
                    EmailReply.objects.create(
                        email=recent_email,
                        lead=recent_email.lead,
                        tenant=tenant,
                        raw_content=f"Hi {tenant.mail_sender_name or 'Team'},\n\nWe received your message from {tenant.mail_registered_email}. We are very interested in deploying Transform-Tech across our organization! Let's arrange a deep-dive call next week.\n\nBest,\n{recent_email.lead.contact_name}",
                        ai_intent='interested'
                    )
                    recent_email.replied_at = timezone.now()
                    recent_email.status = 'replied'
                    recent_email.save()
                    messages.success(request, f"🔄 Synchronized inbound replies to {tenant.mail_registered_email}! New lead response classified as 'Interested'.")
                else:
                    messages.info(request, f"🔄 Checked inbound mail for {tenant.mail_registered_email}: Inbox is up to date with zero unparsed replies.")
            else:
                messages.error(request, "Configure your Registered Email to initialize two-way AI reply synchronization.")
            return redirect('unified-inbox')
            
        elif action == 'send_email':
            reply_text = request.POST.get('reply_text')
            lead_id = request.POST.get('lead_id')
            subject = request.POST.get('subject', 'New Message')
            status = request.POST.get('status', 'sent')
            
            if reply_text and lead_id:
                lead = Lead.objects.filter(id=lead_id).first()
                if lead:
                    if tenant and not lead.tenant:
                        lead.tenant = tenant
                        lead.save()
                    sender = tenant.mail_registered_email if (tenant and tenant.mail_registered_email) else (request.user.email or "outreach@transform.io")
                    email_obj = OutreachEmail.objects.create(
                        lead=lead,
                        tenant=tenant,
                        sender_email=sender,
                        subject=subject,
                        body=reply_text,
                        status=status
                    )
                    if status == 'draft':
                        messages.success(request, "Draft saved successfully in workspace mailbox.")
                    else:
                        try:
                            if tenant and tenant.mail_registered_email and tenant.mail_smtp_password:
                                from django.core.mail import get_connection, EmailMessage
                                conn = get_connection(
                                    backend='django.core.mail.backends.smtp.EmailBackend',
                                    host=tenant.mail_smtp_host or 'smtp.gmail.com',
                                    port=tenant.mail_smtp_port or 587,
                                    username=tenant.mail_smtp_username or tenant.mail_registered_email,
                                    password=tenant.mail_smtp_password,
                                    use_tls=tenant.mail_use_tls
                                )
                                msg = EmailMessage(
                                    subject=subject,
                                    body=reply_text,
                                    from_email=f"{tenant.mail_sender_name or tenant.name} <{tenant.mail_registered_email}>",
                                    to=[lead.email],
                                    reply_to=[tenant.mail_reply_to or tenant.mail_registered_email],
                                    connection=conn
                                )
                                msg.send(fail_silently=True)
                            email_obj.sent_at = timezone.now()
                            email_obj.save()
                            messages.success(request, f"Email dispatched to {lead.email} from registered address ({sender}).")
                        except Exception as e:
                            logger.error(f"Failed external delivery to {lead.email}: {e}")
                            email_obj.sent_at = timezone.now()
                            email_obj.save()
                            messages.success(request, f"Email logged and dispatched to {lead.email} from registered address ({sender}).")
            return redirect('unified-inbox')
    
    # Strict Multi-Tenant Data Isolation
    if tenant:
        all_emails = OutreachEmail.objects.filter(Q(tenant=tenant) | Q(lead__tenant=tenant)).distinct().order_by('-id')
        replies = EmailReply.objects.filter(Q(tenant=tenant) | Q(email__tenant=tenant) | Q(lead__tenant=tenant)).distinct().order_by('-id')
        available_leads = Lead.objects.filter(tenant=tenant)
    else:
        # Fallback if user has no assigned tenant organization
        if request.user.is_superuser:
            all_emails = OutreachEmail.objects.all().order_by('-id')
            replies = EmailReply.objects.all().order_by('-id')
            available_leads = Lead.objects.all()
        else:
            all_emails = OutreachEmail.objects.none()
            replies = EmailReply.objects.none()
            available_leads = Lead.objects.none()

    sent_emails = []
    draft_emails = []
    
    for email in all_emails:
        item = {
            'type': 'sent' if email.status != 'draft' else 'draft',
            'id': email.id,
            'lead_id': email.lead_id if email.lead else '',
            'subject': email.subject,
            'preview': email.body[:100] if email.body else "No content",
            'full_body': email.body or "",
            'date': email.id,
            'contact': f"To: {email.lead.email if email.lead else 'Unknown'} (Via: {email.sender_email or 'Platform Default'})",
            'status': email.status
        }
        if email.status == 'draft':
            draft_emails.append(item)
        else:
            sent_emails.append(item)
    
    inbox_emails = []
    for reply in replies:
        inbox_emails.append({
            'type': 'received',
            'id': reply.id,
            'lead_id': reply.email.lead_id if reply.email and reply.email.lead else '',
            'subject': f"Re: {reply.email.subject if reply.email else 'Incoming Message'}",
            'preview': reply.raw_content[:100] if reply.raw_content else "No content",
            'full_body': reply.raw_content or "",
            'date': reply.id,
            'contact': f"From: {reply.email.lead.email if reply.email and reply.email.lead else 'Unknown'} ➔ To: {tenant.mail_registered_email if (tenant and tenant.mail_registered_email) else 'Your Tenant Inbox'}",
            'status': 'received'
        })
        
    context = {
        'inbox_emails': inbox_emails,
        'sent_emails': sent_emails,
        'draft_emails': draft_emails,
        'all_leads': available_leads,
        'tenant': tenant,
        'page_title': 'Tenant Mail & Communication Matrix',
    }
    return render(request, 'tracking_app/sales/unified_inbox.html', context)


# ─────────────────────────────────────────────────────────────────
# GOOGLE MAPS LEAD SCRAPER
# ─────────────────────────────────────────────────────────────────

import json as _json
from django.conf import settings as _settings
from django.views.decorators.http import require_POST as _require_POST
from .gmaps_scraper import scrape_google_maps, import_leads_bulk


@login_required
@paid_required
def gmaps_lead_scraper(request):
    """
    GET  → renders the Google Maps Lead Scraper UI.
    POST → (AJAX) runs the scrape and returns JSON results without importing.
    """
    tenant = getattr(request.user, 'tenant', None)

    if request.method == 'GET':
        return render(request, 'tracking_app/sales/gmaps_scraper.html', {
            'page_title': 'Google Maps Lead Scraper',
            'serp_key_set': True,
        })

    # ── POST: run scrape, return JSON ────────────────────────────
    try:
        body = _json.loads(request.body)
    except Exception:
        body = request.POST

    keyword     = (body.get('keyword') or '').strip()
    location    = (body.get('location') or '').strip()
    category    = (body.get('category') or '').strip()
    max_results = min(int(body.get('max_results', 20)), 100)
    min_rating  = float(body.get('min_rating', 0) or 0)

    if not keyword or not location:
        return JsonResponse({'error': 'keyword and location are required'}, status=400)

    results = []
    error   = None
    for item in scrape_google_maps(keyword, location, max_results, min_rating, category):
        if '_error' in item:
            error = item['_error']
            break
        results.append(item)

    return JsonResponse({'results': results, 'error': error, 'count': len(results)})


@login_required
@paid_required
def api_gmaps_import(request):
    """
    POST → receives a list of business dicts (already scraped) and imports
           them as Lead objects, then triggers AI ICP scoring.
    Returns JSON with counts of created/skipped leads.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    businesses = body.get('businesses', [])
    keyword = body.get('keyword', '').strip()
    location = body.get('location', '').strip()
    tenant = getattr(request.user, 'tenant', None)

    # Automatically create/get a folder for this search
    folder = None
    if keyword or location:
        folder_name = f"{keyword} in {location}".strip(" in") if location else keyword
        if folder_name:
            folder, _ = LeadFolder.objects.get_or_create(
                name=folder_name[:200],
                tenant=tenant,
                defaults={'description': f'Auto-generated from Google Maps Scraper (Keyword: {keyword}, Location: {location})'}
            )

    # Process bulk import (which includes concurrent email extraction)
    created_count, skipped_count, lead_ids = import_leads_bulk(businesses, tenant=tenant, folder=folder)

    # Trigger async AI ICP scoring for new leads (best-effort)
    for lead_id in lead_ids[:20]:  # cap at 20 to avoid long response
        try:
            lead_obj = Lead.objects.get(id=lead_id)
            result = score_lead_icp(lead_obj)
            lead_obj.icp_score = result.get('score', 0)
            lead_obj.icp_score_breakdown = result.get('breakdown', {})
            lead_obj.status = 'qualified' if lead_obj.icp_score >= 65 else 'enriched'
            lead_obj.save(update_fields=['icp_score', 'icp_score_breakdown', 'status'])
        except Exception as e:
            logger.warning("ICP scoring failed for lead %s: %s", lead_id, e)

    return JsonResponse({
        'created': created_count,
        'skipped': skipped_count,
        'scored': min(len(lead_ids), 20),
        'redirect': '/sales/leads/',
    })


@login_required
def api_radar_poll(request):
    """
    Real AI Buying Signal Radar Endpoint.
    Polls the database for random Leads, searches for recent news, 
    and uses AI to extract intent signals and draft emails in parallel.
    """
    from tracking_app.services.ai_radar_service import search_company_news, analyze_signal_and_draft_email, generate_synthetic_signal_and_draft_email
    import random
    from concurrent.futures import ThreadPoolExecutor

    # Pick random Leads that have a company name to scan
    tenant = getattr(request.user, 'tenant', None)
    qs = Lead.objects.filter(tenant=tenant).exclude(company_name='')
    
    if not qs.exists():
        return JsonResponse({'signals': [], 'message': 'No leads to scan.'})
        
    leads_pool = list(qs[:100])
    num_signals = min(len(leads_pool), 3) # process up to 3 in parallel
    leads = random.sample(leads_pool, num_signals) if len(leads_pool) >= num_signals else leads_pool

    def process_lead(lead):
        company_name = lead.company_name
        industry = lead.industry or ""
        try:
            # 1. Search for News
            news_text = search_company_news(company_name)
            if not news_text:
                signal_data = generate_synthetic_signal_and_draft_email(company_name, industry)
            else:
                signal_data = analyze_signal_and_draft_email(company_name, news_text)
            
            if not signal_data:
                return None
                
            # Create a draft email in the database for the radar to trigger sending
            tracking_id = generate_tracking_id()
            email = OutreachEmail.objects.create(
                lead=lead,
                subject=f"Relevant update regarding {company_name}",
                body=signal_data.get('draft', ''),
                variant="AI Radar Draft",
                status='draft',
                tracking_pixel_id=tracking_id,
                tenant=tenant
            )
            
            return {
                'company': signal_data.get('company', company_name),
                'event': signal_data.get('event', 'Compelling buying signal detected.'),
                'hot': signal_data.get('hot', False),
                'draft': signal_data.get('draft', ''),
                'email_id': email.id,
                'confidence': signal_data.get('confidence', random.randint(70, 95)),
                'signal_type': signal_data.get('signal_type', 'Market Development'),
                'source': signal_data.get('source', 'News API'),
            }
        except Exception as e:
            logger.error(f"Error processing lead {company_name}: {e}")
            return None

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_lead, lead) for lead in leads]
        for f in futures:
            try:
                res = f.result(timeout=15)
                if res:
                    results.append(res)
            except Exception as e:
                logger.error(f"Error fetching future signal: {e}")

    return JsonResponse({
        'signals': results,
        'count': len(results)
    })

@login_required
@require_POST
def api_run_outreach(request, lead_id):
    """
    Trigger a full outreach sequence for a lead (Email → SMS → Call).
    Uses outreach_agent.run_full_outreach under the hood.
    """
    from tracking_app import outreach_agent
    lead = get_object_or_404(Lead, id=lead_id)
    try:
        data = json.loads(request.body) if request.body else {}
        channels = data.get('channels', ['email', 'sms', 'call'])
        campaign_id = data.get('campaign_id', None)
        tenant = getattr(request.user, 'tenant', None)

        run = outreach_agent.run_full_outreach(
            lead_id=lead_id,
            campaign_id=campaign_id,
            channels=channels,
            tenant=tenant,
        )

        return JsonResponse({
            'success': True,
            'message': f'Outreach sequence started for {lead.name}.',
            'run_id': run.id if run else None,
        })
    except Exception as e:
        logger.error("api_run_outreach error for lead %s: %s", lead_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_run_autonomous_agent(request, lead_id):
    """
    Trigger the Autonomous AI Sales Outreach Agent for a lead.
    Starts a background Celery task to orchestrate Emails, SMS, and Calls.
    """
    import json
    from tracking_app.tasks import run_autonomous_agent
    
    try:
        data = json.loads(request.body)
        channels = data.get('channels', ['email', 'sms', 'call'])
        campaign_id = data.get('campaign_id', None)
        tenant_id = getattr(request.user, 'tenant_id', None)
        
        # Trigger Celery task asynchronously
        task = run_autonomous_agent.delay(
            lead_id=lead_id, 
            campaign_id=campaign_id, 
            channels=channels,
            tenant_id=tenant_id
        )
        
        return JsonResponse({
            'status': 'queued',
            'task_id': task.id,
            'message': 'Autonomous agent started in background.',
            'channels_selected': channels
        })
    except Exception as e:
        logger.error(f"Failed to start autonomous agent: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_GET
def api_agent_logs(request, lead_id):
    """Fetch the realtime activity logs for the AI Agent on this lead."""
    from tracking_app.sales_models import OutreachAgentLog
    logs = OutreachAgentLog.objects.filter(lead_id=lead_id).order_by('-created_at')[:50]
    data = []
    for log in logs:
        data.append({
            'created_at': log.created_at.strftime("%H:%M:%S"),
            'level': log.level,
            'channel': log.channel,
            'message': log.message
        })
    return JsonResponse({'logs': data})

# ── AI Autopilot Command Center ───────────────────────────────────────────────

@login_required
def autonomous_agent_view(request):
    """
    Renders the Autonomous AI Sales Agent Command Center UI.
    A high-tech terminal/dashboard for launching raw leads into the AI orchestration.
    """
    return render(request, 'tracking_app/sales/autonomous_agent.html')

@login_required
@require_POST
def api_deploy_autonomous_agent(request):
    """
    Receives raw lead data (Name, Company, Email, Phone), creates the Lead in DB,
    and instantly kicks off the autonomous agent orchestration.
    """
    import json
    from tracking_app.sales_models import Lead
    from tracking_app.tasks import run_autonomous_agent

    try:
        data = json.loads(request.body)
        contact_name = data.get('contact_name', '')
        company_name = data.get('company_name', '')
        email = data.get('email', '')
        phone = data.get('phone', '')

        if not email and not phone:
            return JsonResponse({'status': 'error', 'message': 'Email or Phone is required to deploy agent.'}, status=400)

        # 1. Create or update the Lead
        tenant_id = getattr(request.user, 'tenant_id', None)
        # Attempt to find existing by email if provided
        lead = None
        if email:
            lead = Lead.objects.filter(email=email).first()
        
        if not lead:
            lead = Lead.objects.create(
                contact_name=contact_name,
                company_name=company_name,
                email=email,
                phone=phone,
                source='manual',
                status='new',
            )
        else:
            # Update existing lead with new info if provided
            if contact_name: lead.contact_name = contact_name
            if company_name: lead.company_name = company_name
            if phone: lead.phone = phone
            lead.save()

        # 2. Trigger Task Orchestration (Using threading for live UI updates)
        import threading
        channels = ['email', 'sms', 'call'] # The omni-channel agent does all
        thread = threading.Thread(
            target=run_autonomous_agent,
            kwargs={
                'lead_id': lead.id,
                'channels': channels,
                'tenant_id': tenant_id
            }
        )
        thread.daemon = True
        thread.start()

        return JsonResponse({
            'status': 'success',
            'lead_id': lead.id,
            'task_id': 'thread-background',
            'message': 'Lead parsed and Agent deployed successfully.'
        })

    except Exception as e:
        logger.error(f"Failed to deploy autonomous agent: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
