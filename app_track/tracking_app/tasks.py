"""
tracking_app/tasks.py
─────────────────────────────────────────────────────────────
All background Celery tasks for Transform.io.

Tasks:
  - scan_sla_breaches        : Escalate overdue IT tickets every 15 min
  - run_sales_alerts         : Hot leads / cold deals every hour  
  - sync_imap_inbox          : Poll Gmail IMAP for new replies every 10 min
  - send_weekly_digest       : Weekly summary email every Monday 08:00
  - cleanup_old_sessions     : Purge expired sessions daily
  - push_notification        : Utility — push a WebSocket notification to a user
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
    Connects to Gmail IMAP and checks for new replies.
    Matches replies to existing OutreachEmail by subject threading.
    Creates EmailReply records for matched messages.
    """
    import imaplib
    import email as email_lib
    from email.header import decode_header
    from django.conf import settings

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        mail.select("INBOX")

        # Search for unseen emails
        _, message_ids = mail.search(None, "UNSEEN")
        ids = message_ids[0].split()
        processed = 0

        for uid in ids[-20:]:  # Process at most last 20 unread
            try:
                _, msg_data = mail.fetch(uid, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw_email)

                subject_raw = msg.get("Subject", "")
                subject_parts = decode_header(subject_raw)
                subject = " ".join(
                    part.decode(enc or "utf-8") if isinstance(part, bytes) else part
                    for part, enc in subject_parts
                )
                sender = msg.get("From", "")

                # Extract plain text body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                _store_reply(subject, sender, body[:2000])
                processed += 1

            except Exception as msg_err:
                logger.warning("IMAP message processing error: %s", msg_err)

        mail.logout()
        logger.info("sync_imap_inbox: processed %d messages", processed)
        return {"processed": processed}

    except Exception as e:
        logger.error("sync_imap_inbox error: %s", e)
        return {"error": str(e)}


def _store_reply(subject: str, sender: str, body: str):
    """Match an incoming email to an OutreachEmail and create an EmailReply."""
    from tracking_app.sales_models import OutreachEmail, EmailReply

    # Try to find matching sent email by subject (strip Re: prefix)
    clean_subject = subject.replace("Re:", "").replace("RE:", "").strip()
    matched = OutreachEmail.objects.filter(subject__icontains=clean_subject).first()
    if matched and not EmailReply.objects.filter(
        email=matched, raw_content__startswith=body[:50]
    ).exists():
        EmailReply.objects.create(
            email=matched,
            raw_content=body,
            classified_intent="OTHER",
        )
        matched.status = "replied"
        matched.save(update_fields=["status"])
        logger.info("Stored IMAP reply to OutreachEmail #%s", matched.id)


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
            f"Transform.io Weekly Digest\n\n"
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
                subject="Transform.io Weekly Digest",
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
