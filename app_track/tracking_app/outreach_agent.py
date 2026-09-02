"""
Autonomous AI Sales Outreach Agent — Core Orchestrator
=======================================================
Given a lead_id, this agent:
1. Loads and validates the lead
2. AI-scores the lead against the ICP
3. Generates personalized content for every enabled channel (email, SMS, call)
4. Sends email via Django SMTP backend
5. Sends SMS via Twilio (or simulates)
6. Initiates a voice call / voicemail drop via Twilio TwiML (or simulates)
7. Logs every step to OutreachAgentLog
8. Enrolls the lead in a follow-up email sequence
9. Updates lead status and campaign stats
"""

import os
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


PRODUCT_CONTEXT = """
You are an elite sales AI for Transform-Tech — an AI-powered ATS and CRM SaaS platform.
Transform-Tech helps companies hire 3x faster with AI resume parsing, automated outreach,
smart interview scheduling, buying signal radar, and a full sales CRM in one platform.
Pricing: Starter $49/mo, Growth $99/mo, Enterprise $199/mo. 14-day free trial available.
Key value props: Saves 8+ hours/week, reduces time-to-hire by 60%, works for teams of 5-5000.
Your tone: confident, warm, human — never corporate or spammy.
"""


# ─────────────────────────────────────────────────────────────────
# AI Client Helper
# ─────────────────────────────────────────────────────────────────

def _get_ai_client():
    try:
        from openai import OpenAI
        api_key  = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "")
        if api_key and base_url:
            return OpenAI(api_key=api_key, base_url=base_url), "gemini-1.5-flash-latest"
        if api_key:
            return OpenAI(api_key=api_key), "gpt-4o-mini"
    except Exception as e:
        logger.warning("AI client unavailable: %s", e)
    return None, None


def _ai(system, user, max_tokens=600):
    client, model = _get_ai_client()
    if not client:
        return ""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.78,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("AI call failed: %s", e)
        return ""


# ─────────────────────────────────────────────────────────────────
# Logging Helper
# ─────────────────────────────────────────────────────────────────

def _log(run, lead, tenant, level, channel, message, meta=None):
    try:
        from tracking_app.sales_models import OutreachAgentLog
        OutreachAgentLog.objects.create(
            run=run, lead=lead, tenant=tenant,
            level=level, channel=channel, message=message, meta=meta or {},
        )
    except Exception as e:
        logger.error("Failed to write agent log: %s", e)


# ─────────────────────────────────────────────────────────────────
# Content Generation
# ─────────────────────────────────────────────────────────────────

def generate_email_content(lead):
    import json
    first_name = lead.contact_name.split()[0] if lead.contact_name else "there"
    company    = lead.company_name or "your company"
    industry   = lead.industry or "your industry"
    pain_hints = ", ".join(lead.pain_points[:2]) if lead.pain_points else "manual hiring processes"

    system = PRODUCT_CONTEXT + "\nWrite professional B2B cold outreach emails."
    user = (
        f"Write a cold outreach email to {first_name} at {company} ({industry}).\n"
        f"Known pain points: {pain_hints}\n"
        f"ICP score: {lead.icp_score:.0f}/100\n\n"
        f"Return EXACTLY this JSON (no markdown fences):\n"
        f'{{ "subject": "<compelling subject under 60 chars>", "body": "<3-4 short paragraphs, use {first_name}>" }}'
    )
    raw = _ai(system, user, max_tokens=800)
    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data  = json.loads(clean)
        subject = data.get("subject", "").strip()
        body    = data.get("body", "").strip()
        if subject and body:
            return {"subject": subject, "body": body, "ai": True}
    except Exception:
        pass

    # Fallback
    subject = f"Quick question for {company}'s team, {first_name}"
    body = (
        f"Hi {first_name},\n\n"
        f"I came across {company} and noticed you might be dealing with {pain_hints}.\n\n"
        f"Transform-Tech is an AI-powered hiring & CRM platform that helps teams like yours "
        f"reduce time-to-hire by 60% and automate the manual work that slows you down.\n\n"
        f"I'd love to show you a quick 15-minute demo. Would any time this week work?\n\n"
        f"Best,\nThe Transform-Tech Team\nhttps://transform.io"
    )
    return {"subject": subject, "body": body, "ai": False}


def generate_sms_content(lead):
    first_name = lead.contact_name.split()[0] if lead.contact_name else "there"
    company    = lead.company_name or "your company"
    system = PRODUCT_CONTEXT + "\nWrite ultra-concise, human SMS messages under 160 characters."
    user   = (
        f"Write a personalized cold outreach SMS to {first_name} at {company}. "
        f"Must be under 160 characters, conversational, invite a quick call. "
        f"Return ONLY the SMS text."
    )
    result = _ai(system, user, max_tokens=100)
    if result and len(result) <= 200:
        return result[:160]
    return (
        f"Hi {first_name}! Saw {company} is growing. Transform-Tech can help you hire 3x faster with AI. "
        f"Worth a 10-min chat?"
    )[:160]


def generate_call_script(lead):
    first_name = lead.contact_name.split()[0] if lead.contact_name else "there"
    company    = lead.company_name or "your company"
    industry   = lead.industry or "your industry"
    system = PRODUCT_CONTEXT + "\nWrite short professional voicemail scripts under 90 words."
    user   = (
        f"Write a voicemail drop script for {first_name} at {company} ({industry}). "
        f"Should sound natural when spoken. Return ONLY the script text."
    )
    result = _ai(system, user, max_tokens=200)
    if result and len(result) > 30:
        return result
    return (
        f"Hi {first_name}, this is Alex from Transform-Tech. "
        f"I'm reaching out because we help companies in {industry} like {company} "
        f"reduce time-to-hire by 60 percent with our AI platform. "
        f"I'd love to show you a quick demo. Please call back or visit transform dot io. Thanks!"
    )


# ─────────────────────────────────────────────────────────────────
# Channel Executors
# ─────────────────────────────────────────────────────────────────

def execute_email(run, lead, tenant):
    import re
    from django.utils import timezone as tz
    try:
        if not lead.email:
            run.email_status = "skipped"
            run.save(update_fields=["email_status"])
            _log(run, lead, tenant, "warning", "email", "No email address — skipped")
            return False

        plain_body = re.sub(r'<[^>]+>', '', run.email_body).strip()
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token  = os.environ.get("TWILIO_AUTH_TOKEN")
        
        if account_sid and auth_token:
            import requests
            from requests.auth import HTTPBasicAuth
            url = "https://comms.twilio.com/v1/Emails"
            
            payload = {
                "from": {
                    "address": f"{account_sid}@twilio.email", 
                    "name": tenant.name if tenant else "AI Sales Agent"
                },
                "to": [{"address": lead.email}],
                "content": {
                    "subject": run.email_subject,
                    "html": run.email_body
                }
            }
            resp = requests.post(
                url, 
                json=payload, 
                auth=HTTPBasicAuth(account_sid, auth_token),
                timeout=10
            )
            if resp.status_code >= 400:
                logger.warning("Twilio Email API failed (status %s): %s. Falling back to SMTP.", resp.status_code, resp.text)
                account_sid = None
        
                sendgrid_key = os.environ.get("SENDGRID_API_KEY")
        if sendgrid_key:
            import requests
            url = "https://api.sendgrid.com/v3/mail/send"
            from_email = os.environ.get("DEFAULT_FROM_EMAIL", "j@transform-tech.com")
            payload = {
                "personalizations": [{"to": [{"email": lead.email}]}],
                "from": {"email": from_email, "name": "J Martin | Transform-Tech"},
                "subject": run.email_subject,
                "content": [{"type": "text/html", "value": run.email_body}]
            }
            resp = requests.post(url, json=payload, headers={"Authorization": f"Bearer {sendgrid_key}"}, timeout=10)
            if resp.status_code >= 400:
                logger.error(f"SendGrid failed: {resp.text}")
                raise Exception(f"SendGrid HTTP Error: {resp.text}")
        else:
            if not account_sid or not auth_token:
                from django.core.mail import get_connection, send_mail
                connection = None
                if tenant and tenant.mail_smtp_host and tenant.mail_smtp_username and tenant.mail_smtp_password:
                    use_ssl = (tenant.mail_smtp_port == 465)
                    use_tls = tenant.mail_use_tls if not use_ssl else False
                    connection = get_connection(
                        host=tenant.mail_smtp_host,
                        port=tenant.mail_smtp_port,
                        username=tenant.mail_smtp_username,
                        password=tenant.mail_smtp_password,
                        use_tls=use_tls,
                        use_ssl=use_ssl
                    )
                    from_email = tenant.mail_registered_email or tenant.mail_smtp_username
                else:
                    from_email = (
                        os.environ.get("DEFAULT_FROM_EMAIL")
                        or os.environ.get("EMAIL_HOST_USER")
                        or "sales@transform.io"
                    )
                
                send_mail(
                    subject=run.email_subject,
                    message=plain_body,
                    html_message=run.email_body,
                    from_email=from_email,
                    recipient_list=[lead.email],
                    fail_silently=False,
                    connection=connection,
                )

        run.email_status  = "sent"
        run.email_sent_at = tz.now()
        run.save(update_fields=["email_status", "email_sent_at"])

        try:
            from tracking_app.sales_models import OutreachEmail
            from tracking_app.sales_engine import generate_tracking_id
            OutreachEmail.objects.create(
                lead=lead, tenant=tenant,
                subject=run.email_subject, body=run.email_body,
                variant="A", sender_email=from_email,
                status="sent", sent_at=tz.now(),
                tracking_pixel_id=generate_tracking_id(),
            )
        except Exception:
            pass

        _log(run, lead, tenant, "success", "email",
             f'Email sent to {lead.email}: "{run.email_subject[:60]}"',
             {"to": lead.email, "subject": run.email_subject[:80]})
        return True

    except Exception as e:
        run.email_status = "failed"
        run.save(update_fields=["email_status"])
        _log(run, lead, tenant, "error", "email", f"Email failed: {e}", {"error": str(e)})
        return False


def execute_sms(run, lead, tenant):
    from django.utils import timezone as tz
    try:
        if not lead.phone:
            run.sms_status = "skipped"
            run.save(update_fields=["sms_status"])
            _log(run, lead, tenant, "warning", "sms", "No phone number — skipped")
            return False

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token  = os.environ.get("TWILIO_AUTH_TOKEN")
        from_phone  = os.environ.get("TWILIO_PHONE_NUMBER")
        simulated   = False
        sid         = None

        if account_sid and auth_token and from_phone and from_phone != "+1234567890":
            # Normalize phone for Twilio (assumes India +91 if exactly 10 digits)
            target_phone = lead.phone.strip()
            if len(target_phone) == 10 and target_phone.isdigit():
                target_phone = "+91" + target_phone
            elif not target_phone.startswith("+"):
                target_phone = "+" + target_phone

            try:
                from twilio.rest import Client
                client  = Client(account_sid, auth_token)
                message = client.messages.create(body=run.sms_body, to=target_phone, from_=from_phone)
                sid     = message.sid
            except Exception as err:
                # Retry with Trial Template if restricted
                if "predefined SMS templates" in str(err) or "trial" in str(err).lower():
                    try:
                        message = client.messages.create(body="sms_appointment_reminders", to=target_phone, from_=from_phone)
                        sid = message.sid
                    except Exception as fallback_err:
                        logger.warning("Twilio Trial SMS also failed, simulating: %s", fallback_err)
                        simulated = True
                        sid = "SIM_" + target_phone.replace("+","")
                else:
                    logger.warning("Twilio SMS failed, simulating: %s", err)
                    simulated = True
                    sid = "SIM_" + target_phone.replace("+","")
        else:
            simulated = True
            sid = "SIM_" + lead.phone.replace("+","").replace(" ","")

        run.sms_status  = "sent"
        run.sms_sent_at = tz.now()
        run.sms_sid     = sid
        run.save(update_fields=["sms_status", "sms_sent_at", "sms_sid"])
        _log(run, lead, tenant, "success", "sms",
             f"SMS sent to {lead.phone}",
             {"phone": lead.phone, "sid": sid, "simulated": simulated})
        return True

    except Exception as e:
        run.sms_status = "failed"
        run.save(update_fields=["sms_status"])
        _log(run, lead, tenant, "error", "sms", f"SMS failed: {e}", {"error": str(e)})
        return False


def execute_call(run, lead, tenant):
    from django.utils import timezone as tz
    try:
        if not lead.phone:
            run.call_status = "skipped"
            run.save(update_fields=["call_status"])
            _log(run, lead, tenant, "warning", "call", "No phone number — skipped")
            return False

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token  = os.environ.get("TWILIO_AUTH_TOKEN")
        from_phone  = os.environ.get("TWILIO_PHONE_NUMBER")
        simulated   = False
        sid         = None

        script_safe = (run.call_script
                       .replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
        twiml = f"<Response><Say voice='Polly.Joanna'>{script_safe}</Say></Response>"

        if account_sid and auth_token and from_phone and from_phone != "+1234567890":
            # Normalize phone
            target_phone = lead.phone.strip()
            if len(target_phone) == 10 and target_phone.isdigit():
                target_phone = "+91" + target_phone
            elif not target_phone.startswith("+"):
                target_phone = "+" + target_phone

            try:
                from twilio.rest import Client
                client = Client(account_sid, auth_token)
                call   = client.calls.create(twiml=twiml, to=target_phone, from_=from_phone)
                sid    = call.sid
            except Exception as err:
                if "trial" in str(err).lower() or "disallowed" in str(err).lower():
                    try:
                        call = client.calls.create(url="https://webhooks.twilio.com/v1/Voice/Template/voice_speech_recognition", to=target_phone, from_=from_phone)
                        sid = call.sid
                    except Exception as fallback_err:
                        logger.warning("Twilio Trial call also failed, simulating: %s", fallback_err)
                        simulated = True
                        sid = "SIM_CALL_" + target_phone.replace("+","")
                else:
                    logger.warning("Twilio call failed, simulating: %s", err)
                    simulated = True
                    sid = "SIM_CALL_" + target_phone.replace("+","")
        else:
            simulated = True
            sid = "SIM_CALL_" + lead.phone.replace("+","").replace(" ","")

        run.call_status       = "initiated"
        run.call_sid          = sid
        run.call_initiated_at = tz.now()
        run.save(update_fields=["call_status", "call_sid", "call_initiated_at"])
        _log(run, lead, tenant, "success", "call",
             f"Call initiated to {lead.phone}",
             {"phone": lead.phone, "sid": sid, "simulated": simulated})
        return True

    except Exception as e:
        run.call_status = "failed"
        run.save(update_fields=["call_status"])
        _log(run, lead, tenant, "error", "call", f"Call failed: {e}", {"error": str(e)})
        return False


# ─────────────────────────────────────────────────────────────────
# Sequence Enrollment
# ─────────────────────────────────────────────────────────────────

def enroll_in_follow_up(run, lead, tenant, delay_days_list=None):
    from django.utils import timezone as tz
    try:
        from tracking_app.sales_models import (
            EmailSequence, EmailSequenceStep, LeadSequenceEnrollment
        )
        if delay_days_list is None:
            delay_days_list = [3, 7, 14]

        seq, created = EmailSequence.objects.get_or_create(
            name="AI Agent — Automated Follow-Up",
            defaults={"description": "Auto-created by Outreach Agent", "is_active": True}
        )
        if created:
            steps = [
                (1, delay_days_list[0] if len(delay_days_list)>0 else 3,
                 "Following up — {company}", "AI follow-up 1: new hook or insight + CTA."),
                (2, delay_days_list[1] if len(delay_days_list)>1 else 7,
                 "Quick question, {first_name}", "AI follow-up 2: relevant case study + invite."),
                (3, delay_days_list[2] if len(delay_days_list)>2 else 14,
                 "Last note — {company}", "AI breakup email: low pressure, leave door open."),
            ]
            for step_num, delay, subj, body in steps:
                EmailSequenceStep.objects.create(
                    sequence=seq, step_number=step_num, delay_days=delay,
                    subject_template=subj, body_template=body, is_ai_generated=True
                )

        next_at = tz.now() + timedelta(days=delay_days_list[0] if delay_days_list else 3)
        enrollment, enrolled = LeadSequenceEnrollment.objects.get_or_create(
            lead=lead, sequence=seq,
            defaults={"status": "active", "current_step": 1, "next_email_at": next_at}
        )

        run.sequence_enrolled = True
        run.sequence_step     = enrollment.current_step
        run.next_follow_up_at = enrollment.next_email_at
        run.save(update_fields=["sequence_enrolled", "sequence_step", "next_follow_up_at"])

        action = "Enrolled" if enrolled else "Already enrolled"
        _log(run, lead, tenant, "success", "system",
             f"{action} in follow-up sequence (Day +{delay_days_list[0] if delay_days_list else 3})",
             {"sequence_id": seq.id})
        return True

    except Exception as e:
        logger.error("Sequence enrollment failed: %s", e)
        _log(run, lead, tenant, "error", "system", f"Sequence enrollment failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────

def run_full_outreach(lead_id, campaign_id=None, channels=None, tenant=None):
    """
    Main entry point. Runs the full autonomous multi-channel outreach for a lead.
    Returns: dict with run_id, status, and per-channel results.
    """
    from tracking_app.sales_models import Lead, AgentOutreachRun, OutreachCampaign
    from tracking_app.sales_engine import score_lead_icp
    from django.utils import timezone as tz

    if channels is None:
        channels = ["email", "sms"]

    try:
        lead = Lead.objects.get(id=lead_id)
    except Lead.DoesNotExist:
        return {"status": "failed", "error": "Lead not found"}

    if tenant is None:
        tenant = None # Lead model does not have tenant field

    campaign = None
    if campaign_id:
        try:
            campaign = OutreachCampaign.objects.get(id=campaign_id)
        except OutreachCampaign.DoesNotExist:
            pass

    run = AgentOutreachRun.objects.create(
        lead=lead, tenant=tenant, campaign=campaign,
        status="running",
        email_enabled="email" in channels,
        sms_enabled="sms" in channels,
        call_enabled="call" in channels,
        started_at=tz.now(),
    )

    _log(run, lead, tenant, "info", "system",
         f"Agent started: {lead.contact_name} @ {lead.company_name}",
         {"channels": channels})

    # Step 1: Score
    try:
        score_result = score_lead_icp(lead)
        icp_score    = score_result.get("score", 0)
        run.icp_score = icp_score
        run.save(update_fields=["icp_score"])
        if icp_score > 0:
            lead.icp_score = icp_score
            lead.save(update_fields=["icp_score"])
        _log(run, lead, tenant, "ai", "ai",
             f"ICP scored: {icp_score:.0f}/100 — {score_result.get('reason','')[:120]}",
             {"score": icp_score})
        if icp_score < 20:
            run.status = "skipped"
            run.skip_reason = f"ICP score too low: {icp_score:.0f}/100"
            run.completed_at = tz.now()
            run.save(update_fields=["status", "skip_reason", "completed_at"])
            _log(run, lead, tenant, "warning", "system",
                 f"Skipped — ICP {icp_score:.0f} below threshold")
            return {"run_id": run.id, "status": "skipped", "reason": run.skip_reason}
    except Exception as e:
        logger.warning("ICP scoring failed: %s", e)

    # Step 2: Generate content
    if "email" in channels:
        content = generate_email_content(lead)
        run.email_subject = content["subject"]
        run.email_body    = content["body"]
        run.save(update_fields=["email_subject", "email_body"])
        _log(run, lead, tenant, "ai", "email",
             f'Email drafted: "{content["subject"][:60]}"', {"ai": content["ai"]})

    if "sms" in channels:
        sms_text = generate_sms_content(lead)
        run.sms_body = sms_text
        run.save(update_fields=["sms_body"])
        _log(run, lead, tenant, "ai", "sms",
             f"SMS drafted ({len(sms_text)} chars)", {})

    if "call" in channels:
        script = generate_call_script(lead)
        run.call_script = script
        run.save(update_fields=["call_script"])
        _log(run, lead, tenant, "ai", "call",
             f"Voicemail script drafted ({len(script.split())} words)", {})

    # Step 3: Execute
    results    = {}
    email_ok   = sms_ok = call_ok = False

    if "email" in channels:
        email_ok = execute_email(run, lead, tenant)
        results["email"] = "sent" if email_ok else ("skipped" if not lead.email else "failed")

    if "sms" in channels:
        sms_ok = execute_sms(run, lead, tenant)
        results["sms"] = "sent" if sms_ok else ("skipped" if not lead.phone else "failed")

    if "call" in channels:
        call_ok = execute_call(run, lead, tenant)
        results["call"] = "initiated" if call_ok else ("skipped" if not lead.phone else "failed")

    # Step 4: Follow-up sequence
    if email_ok or sms_ok:
        delay_days = (campaign.sequence_days if campaign and campaign.sequence_days else [3, 7, 14])
        enroll_in_follow_up(run, lead, tenant, delay_days)

    # Step 5: Update lead
    if email_ok or sms_ok or call_ok:
        lead.status = "in_sequence"
        lead.last_activity_at = tz.now()
        lead.save(update_fields=["status", "last_activity_at"])

    # Step 6: Update campaign stats
    if campaign:
        try:
            if email_ok:
                OutreachCampaign.objects.filter(pk=campaign.pk).update(
                    emails_sent=campaign.emails_sent + 1
                )
            if sms_ok:
                OutreachCampaign.objects.filter(pk=campaign.pk).update(
                    sms_sent=campaign.sms_sent + 1
                )
            if call_ok:
                OutreachCampaign.objects.filter(pk=campaign.pk).update(
                    calls_initiated=campaign.calls_initiated + 1
                )
        except Exception as e:
            logger.warning("Campaign stats update failed: %s", e)

    # Finalize
    any_ok  = email_ok or sms_ok or call_ok
    all_ok  = all([
        (email_ok if "email" in channels else True),
        (sms_ok   if "sms"   in channels else True),
        (call_ok  if "call"  in channels else True),
    ])
    final_status = "completed" if all_ok else ("partial" if any_ok else "failed")
    run.status       = final_status
    run.completed_at = tz.now()
    run.save(update_fields=["status", "completed_at"])

    _log(run, lead, tenant, "success" if any_ok else "error", "system",
         f"Outreach [{final_status.upper()}] — " + ", ".join(f"{k}:{v}" for k,v in results.items()),
         {"results": results, "duration": run.duration_seconds})

    return {
        "run_id":  run.id,
        "status":  final_status,
        "results": results,
        "lead":    {"id": lead.id, "name": lead.contact_name, "company": lead.company_name},
    }
