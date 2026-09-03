"""
tracking_app/tasks.py
─────────────────────────────────────────────────────────────
All background Celery tasks for Transform-Tech.

Tasks:
  - scan_sla_breaches        : Escalate overdue IT tickets every 15 min
  - run_sales_alerts         : Hot leads / cold deals every hour  
  - sync_imap_inbox          : Poll Gmail IMAP for new replies every 10 min
  - send_weekly_digest       : Weekly summary email every Monday 08:00
  - cleanup_old_sessions     : Purge expired sessions daily
  - push_notification        : Utility — push a WebSocket notification to a user
  - run_outreach_drip        : 24/7 autonomous outreach — processes 10 leads every 5 min
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Task: SLA Breach Scanner (runs every 15 minutes)
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.scan_sla_breaches")
def scan_sla_breaches():
    """
    Check all open IT tickets against their SLA deadlines.
    If breached, escalate priority and push a WebSocket notification.
    """
    try:
        from tracking_app.models import ITTicket
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        now = timezone.now()
        breached = 0

        tickets = ITTicket.objects.filter(
            status__in=["open", "in_progress"],
            sla_due__lt=now,
            priority__in=["low", "medium"],  # Only escalate non-critical ones
        )

        for ticket in tickets:
            old_priority = ticket.priority
            ticket.priority = "high" if ticket.priority == "medium" else "medium"
            ticket.save(update_fields=["priority"])
            breached += 1
            logger.warning(
                "SLA BREACH: Ticket #%s escalated %s→%s", ticket.id, old_priority, ticket.priority
            )

            # Push WebSocket notification to assignee
            if ticket.assignee_id and channel_layer:
                try:
                    async_to_sync(channel_layer.group_send)(
                        f"notifications_{ticket.assignee_id}",
                        {
                            "type": "notification_message",
                            "title": f"SLA Breach: #{ticket.id}",
                            "body": f'Ticket "{ticket.title}" exceeded SLA. Priority escalated.',
                            "url": f"/it/tickets/{ticket.id}/",
                            "icon": "bx bx-alarm-exclamation",
                            "color": "#ef4444",
                        },
                    )
                except Exception as ws_err:
                    logger.warning("WebSocket push failed: %s", ws_err)

        logger.info("scan_sla_breaches: %d tickets escalated", breached)
        return {"escalated": breached}

    except Exception as e:
        logger.error("scan_sla_breaches error: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# Task: Sales Alert Generator (runs every hour)
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.run_sales_alerts")
def run_sales_alerts():
    """Wraps the sales engine alert generator as a Celery task."""
    try:
        from tracking_app.sales_engine import generate_sales_alerts
        count = generate_sales_alerts()
        logger.info("run_sales_alerts: %d alerts generated", count)
        return {"alerts_created": count}
    except Exception as e:
        logger.error("run_sales_alerts error: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# Task: IMAP Inbox Sync (runs every 10 minutes)
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.sync_imap_inbox")
def sync_imap_inbox():
    """
    Connects to IMAP servers for every Tenant that has mail configured.
    Reads unread emails, matches them to OutreachEmail via threading,
    and creates EmailReply records linked to that specific Tenant.
    """
    import imaplib
    import email as email_lib
    from email.header import decode_header
    from tracking_app.models import Tenant
    from tracking_app.sales_models import OutreachEmail, EmailReply
    
    tenants = Tenant.objects.exclude(mail_registered_email__isnull=True).exclude(mail_app_password__isnull=True)
    
    total_synced = 0
    for tenant in tenants:
        if not tenant.mail_imap_host:
            continue
            
        try:
            # Secure IMAP connection per Tenant
            mail = imaplib.IMAP4_SSL(tenant.mail_imap_host, tenant.mail_imap_port or 993)
            mail.login(tenant.mail_registered_email, tenant.mail_app_password)
            mail.select("INBOX")
            
            # Fetch unread emails
            status, messages = mail.search(None, "(UNSEEN)")
            if status != "OK" or not messages[0]:
                mail.logout()
                continue
                
            for msg_id in messages[0].split():
                res, msg_data = mail.fetch(msg_id, "(RFC822)")
                if res != "OK":
                    continue
                    
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email_lib.message_from_bytes(response_part[1])
                        
                        subject, encoding = decode_header(msg.get("Subject", ""))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="replace")
                            
                        # Simple thread matching: check if Subject matches an OutreachEmail sent by this Tenant
                        matched = OutreachEmail.objects.filter(
                            tenant=tenant,
                            subject__icontains=subject.replace("Re: ", "").replace("RE: ", "").strip()
                        ).first()
                        
                        if matched:
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                        break
                            else:
                                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                                
                            # Save the EmailReply for this Tenant's unified inbox
                            if not EmailReply.objects.filter(email=matched, raw_content=body).exists():
                                EmailReply.objects.create(
                                    email=matched,
                                    raw_content=body,
                                    classified_intent="OTHER"
                                )
                                matched.status = "replied"
                                matched.save(update_fields=["status"])
                                logger.info(f"Stored IMAP reply to OutreachEmail #{matched.id} for Tenant {tenant.id}")
                                total_synced += 1
                                
            mail.logout()
        except Exception as e:
            logger.error(f"IMAP Sync Error for Tenant {tenant.id}: {e}")
            
    return {"total_synced": total_synced}



# ─────────────────────────────────────────────────────────────
# Task: Weekly Digest Email (runs Monday 08:00 UTC)
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.send_weekly_digest")
def send_weekly_digest():
    """Sends a weekly HTML summary email to all admin users."""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from tracking_app.models import User, ITTicket, Candidate
        from tracking_app.sales_models import Lead, Deal, SalesAlert

        week_ago = timezone.now() - timedelta(days=7)

        stats = {
            "new_tickets": ITTicket.objects.filter(created_at__gte=week_ago).count(),
            "new_candidates": Candidate.objects.filter(created_at__gte=week_ago).count(),
            "new_leads": Lead.objects.filter(created_at__gte=week_ago).count(),
            "deals_won": Deal.objects.filter(stage="won", updated_at__gte=week_ago).count(),
            "open_alerts": SalesAlert.objects.filter(is_read=False).count(),
        }

        body = (
            f"Transform-Tech Weekly Digest\n\n"
            f"Past 7 days:\n"
            f"• New IT Tickets: {stats['new_tickets']}\n"
            f"• New Candidates: {stats['new_candidates']}\n"
            f"• New Leads: {stats['new_leads']}\n"
            f"• Deals Won: {stats['deals_won']}\n"
            f"• Open Sales Alerts: {stats['open_alerts']}\n\n"
            f"Visit your dashboard to review: https://your-domain.com"
        )

        admins = User.objects.filter(is_superuser=True).values_list("email", flat=True)
        if admins:
            send_mail(
                subject="Transform-Tech Weekly Digest",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=list(admins),
                fail_silently=True,
            )

        logger.info("send_weekly_digest sent to %d admins", len(admins))
        return {"sent_to": len(admins)}

    except Exception as e:
        logger.error("send_weekly_digest error: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# Task: DB Cleanup (runs daily)
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.cleanup_old_data")
def cleanup_old_data():
    """Purge expired Django sessions and stale tracking pixels."""
    try:
        from django.contrib.sessions.backends.db import SessionStore
        from django.contrib.sessions.models import Session

        expired = Session.objects.filter(expire_date__lt=timezone.now())
        count = expired.count()
        expired.delete()
        logger.info("cleanup_old_data: deleted %d expired sessions", count)
        return {"sessions_deleted": count}
    except Exception as e:
        logger.error("cleanup_old_data error: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# Utility: Push a notification to a user via WebSocket
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.push_notification")
def push_notification(user_id: int, title: str, body: str, url: str = "#",
                      icon: str = "bx bx-bell", color: str = "#00E5FF"):
    """
    Push a WebSocket notification to a specific user.
    Safe to call from anywhere — handles channel layer unavailability gracefully.
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if not channel_layer:
            return {"error": "No channel layer configured"}

        async_to_sync(channel_layer.group_send)(
            f"notifications_{user_id}",
            {
                "type": "notification_message",
                "title": title,
                "body": body,
                "url": url,
                "icon": icon,
                "color": color,
            },
        )
        return {"sent": True}
    except Exception as e:
        logger.error("push_notification error: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# Task: Run Autonomous Sales Agent Outreach
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.run_autonomous_agent")
def run_autonomous_agent(lead_id, campaign_id=None, channels=None, tenant_id=None):
    """
    Background task to run the Autonomous AI Sales Outreach Agent for a specific lead.
    """
    from tracking_app.outreach_agent import run_full_outreach

    # We do a direct try-except. Tracking_app tenant resolution handled within.
    try:
        # Note: Tenant fetching can be done inside run_full_outreach or here
        from tracking_app.models import Tenant
        tenant = None
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                pass
                
        result = run_full_outreach(
            lead_id=lead_id,
            campaign_id=campaign_id,
            channels=channels,
            tenant=tenant
        )
        return result
    except Exception as e:
        logger.error(f"Failed to run autonomous agent for lead {lead_id}: {e}")
        return {"status": "error", "message": str(e)}

@shared_task(name="tracking_app.tasks.execute_automation_action", bind=True, max_retries=3)
def execute_automation_action(self, rule_id, tenant_id, action, payload):
    from django.core.cache import cache
    from .models import AutomationRule, AutomationLog, Tenant
    import hashlib
    import json
    
    payload_str = json.dumps(payload, sort_keys=True)
    lock_key = f"wf_lock_{rule_id}_{tenant_id}_{hashlib.md5(payload_str.encode()).hexdigest()}"
    
    if not cache.add(lock_key, "running", 600):
        return {"status": "skipped", "reason": "idempotency_lock_active"}
    
    try:
        rule = AutomationRule.objects.get(id=rule_id)
        tenant = Tenant.objects.get(id=tenant_id)
        
        action_type = action.get('action_type')
        
        # Example Actions
        if action_type == 'send_email':
            # e.g. trigger email via django.core.mail
            pass
        elif action_type == 'run_ai_agent':
            lead_id = payload.get('id')
            if lead_id and 'lead' in rule.trigger_type:
                from .outreach_agent import run_full_outreach
                run_full_outreach(lead_id=lead_id)
                
        # Log Success
        AutomationLog.objects.create(
            rule=rule,
            tenant=tenant,
            event_type=rule.trigger_type,
            payload_snapshot=payload,
            status='SUCCESS'
        )
        
    except Exception as e:
        # Log Failure
        AutomationLog.objects.create(
            rule_id=rule_id,
            tenant_id=tenant_id,
            event_type='UNKNOWN',
            payload_snapshot=payload,
            status='FAILED',
            error_message=str(e)
        )

@shared_task(name="tracking_app.tasks.evaluate_account_churn")
def evaluate_account_churn():
    """
    Daily task that evaluates the churn risk of all active Won deals.
    """
    from .sales_models import Deal
    from .ai_churn_predictor import predict_deal_churn
    
    # Evaluate churn for deals that are 'won' (active clients)
    deals = Deal.objects.filter(stage='won')
    for deal in deals:
        predict_deal_churn(deal.id)
        
    return {"evaluated_deals": deals.count()}

@shared_task(name="tracking_app.tasks.launch_ai_voice_call")
def launch_ai_voice_call(lead_id, script_prompt):
    """
    Connects to a Voice AI Provider (e.g. Bland AI, Retell, or Twilio) to initiate a scripted call.
    """
    from .sales_models import Lead
    import requests
    import os
    
    try:
        lead = Lead.objects.get(id=lead_id)
        if not lead.phone:
            return {"error": "Lead has no phone number"}
            
        # Example using Bland AI API (Standard for AI Outbound Calls)
        bland_api_key = os.environ.get("BLAND_API_KEY", "")
        if not bland_api_key:
            logger.warning("No BLAND_API_KEY set. Simulating AI call.")
            return {"status": "simulated", "message": "Voice AI simulated (No API key)"}
            
        headers = {'authorization': bland_api_key, 'Content-Type': 'application/json'}
        payload = {
            'phone_number': lead.phone,
            'task': script_prompt,
            'voice': 'josh',
            'reduce_latency': True,
            'record': True
        }
        
        response = requests.post('https://api.bland.ai/v1/calls', json=payload, headers=headers)
        if response.status_code == 200:
            return {"status": "success", "call_id": response.json().get('call_id')}
        else:
            return {"error": response.text}
            
    except Exception as e:
        logger.error(f"Voice AI Call Failed: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# Task: 24/7 Autonomous Outreach Drip (runs every 5 minutes via Beat)
# Picks up to 10 fresh leads that have never been contacted and runs the full AI agent on each.
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.run_outreach_drip")
def run_outreach_drip():
    """
    24/7 drip: picks the next batch of un-contacted leads belonging to any
    active campaign and runs the full AI outreach agent on each one.
    Processes up to 10 leads per run (every 5 minutes = up to 2,880 leads/day).
    """
    from .sales_models import Lead, OutreachCampaign, OutreachAgentRun
    from .outreach_agent import run_full_outreach
    from .models import Tenant

    try:
        # Only process leads that have never been touched by the agent
        already_contacted = OutreachAgentRun.objects.values_list('lead_id', flat=True).distinct()

        # Find un-contacted leads from active campaigns, ordered oldest first
        active_campaigns = OutreachCampaign.objects.filter(status='active', channel_email=True)
        if not active_campaigns.exists():
            logger.info("run_outreach_drip: No active campaigns found, skipping.")
            return {"status": "skipped", "reason": "no_active_campaigns"}

        # Get leads belonging to active campaign tenants
        tenant_ids = active_campaigns.values_list('tenant_id', flat=True).distinct()
        leads = (
            Lead.objects
            .filter(tenant_id__in=tenant_ids, status__in=['new', 'contacted'])
            .exclude(id__in=already_contacted)
            .exclude(email='')
            .order_by('id')[:10]  # Process 10 per tick
        )

        if not leads:
            logger.info("run_outreach_drip: No pending leads found.")
            return {"status": "idle", "leads_processed": 0}

        processed = 0
        errors = 0
        for lead in leads:
            try:
                # Find the best active campaign for this lead's tenant
                campaign = active_campaigns.filter(tenant_id=lead.tenant_id).first()
                if not campaign:
                    continue

                result = run_full_outreach(
                    lead_id=lead.id,
                    campaign_id=campaign.id,
                    channels=['email'],
                    tenant=lead.tenant
                )

                if result and result.get('email') == 'sent':
                    processed += 1
                    logger.info(f"run_outreach_drip: Sent to lead {lead.id} ({lead.email})")
                else:
                    errors += 1
                    logger.warning(f"run_outreach_drip: Agent returned non-sent for lead {lead.id}: {result}")

            except Exception as e:
                errors += 1
                logger.error(f"run_outreach_drip: Error on lead {lead.id}: {e}")

        logger.info(f"run_outreach_drip: Completed. Sent={processed}, Errors={errors}")
        return {"status": "ok", "leads_processed": processed, "errors": errors}

    except Exception as e:
        logger.error(f"run_outreach_drip: Fatal error: {e}")
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────────────────────
# Task: Trigger Outreach for a Single Lead (called from UI button)
# ─────────────────────────────────────────────────────────────

@shared_task(name="tracking_app.tasks.trigger_single_lead_outreach")
def trigger_single_lead_outreach(lead_id, tenant_id):
    """
    Triggered directly from the Lead Detail page 'Run AI Outreach' button.
    Finds the best active campaign and immediately runs the full agent.
    """
    from .sales_models import OutreachCampaign
    from .outreach_agent import run_full_outreach
    from .models import Tenant

    try:
        tenant = Tenant.objects.get(id=tenant_id)
        campaign = OutreachCampaign.objects.filter(
            tenant=tenant, status='active', channel_email=True
        ).first()

        if not campaign:
            # Auto-create a default campaign so the button always works
            campaign, _ = OutreachCampaign.objects.get_or_create(
                tenant=tenant,
                name="Default Outreach Campaign",
                defaults={
                    "goal": "Book demos and generate pipeline.",
                    "status": "active",
                    "channel_email": True,
                    "channel_sms": False,
                }
            )

        result = run_full_outreach(
            lead_id=lead_id,
            campaign_id=campaign.id,
            channels=['email'],
            tenant=tenant
        )
        return result

    except Exception as e:
        logger.error(f"trigger_single_lead_outreach: Error for lead {lead_id}: {e}")
        return {"status": "error", "message": str(e)}
