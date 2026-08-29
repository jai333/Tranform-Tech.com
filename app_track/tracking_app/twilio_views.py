import os
import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

try:
    from twilio.rest import Client
except ImportError:
    Client = None

logger = logging.getLogger(__name__)


# ── Twilio client helper ──────────────────────────────────────────────────────
def get_twilio_client():
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token  = os.environ.get('TWILIO_AUTH_TOKEN')
    if account_sid and auth_token and Client:
        return Client(account_sid, auth_token)
    return None


# ── Call Initiation ───────────────────────────────────────────────────────────
@csrf_exempt
@require_POST
def api_twilio_call(request):
    try:
        data      = json.loads(request.body)
        to_phone  = data.get('phone')

        if not to_phone:
            return JsonResponse({'status': 'error', 'message': 'Phone number is required.'}, status=400)

        client     = get_twilio_client()
        from_phone = os.environ.get('TWILIO_PHONE_NUMBER')

        if not client or not from_phone:
            logger.warning(f"Simulating Twilio Call to {to_phone} (Missing Credentials)")
            return JsonResponse({
                'status':    'success',
                'message':   'Simulated call initiated.',
                'call_sid':  'SIM_' + to_phone.replace('+', '').replace(' ', ''),
                'simulated': True
            })

        call = client.calls.create(
            twiml='<Response><Say>Hello from Transform dot I O. We are connecting you to an enterprise sales representative.</Say></Response>',
            to=to_phone,
            from_=from_phone
        )
        return JsonResponse({'status': 'success', 'message': 'Call initiated.', 'call_sid': call.sid})

    except Exception as e:
        logger.error(f"Error initiating Twilio call: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── Call Status ───────────────────────────────────────────────────────────────
@csrf_exempt
@require_POST
def api_twilio_call_status(request):
    """Returns live status for a given call_sid."""
    try:
        data     = json.loads(request.body)
        call_sid = data.get('call_sid', '')

        if not call_sid:
            return JsonResponse({'status': 'error', 'message': 'call_sid required.'}, status=400)

        # Simulated call — return synthetic status progression
        if call_sid.startswith('SIM_'):
            return JsonResponse({'status': 'success', 'call_status': 'in-progress', 'simulated': True})

        client = get_twilio_client()
        if not client:
            return JsonResponse({'status': 'success', 'call_status': 'in-progress', 'simulated': True})

        call = client.calls(call_sid).fetch()
        return JsonResponse({'status': 'success', 'call_status': call.status})

    except Exception as e:
        logger.error(f"Error fetching call status: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── SMS Send ──────────────────────────────────────────────────────────────────
@csrf_exempt
@require_POST
def api_twilio_sms(request):
    try:
        data         = json.loads(request.body)
        to_phone     = data.get('phone')
        message_body = data.get('message')

        if not to_phone or not message_body:
            return JsonResponse({'status': 'error', 'message': 'Phone and message are required.'}, status=400)

        client     = get_twilio_client()
        from_phone = os.environ.get('TWILIO_PHONE_NUMBER')

        if not client or not from_phone:
            logger.warning(f"Simulating Twilio SMS to {to_phone}: {message_body}")
            return JsonResponse({
                'status':      'success',
                'message':     'Simulated SMS sent.',
                'message_sid': 'SIM_MSG_' + to_phone.replace('+', '').replace(' ', ''),
                'simulated':   True
            })

        message = client.messages.create(
            body=message_body,
            to=to_phone,
            from_=from_phone
        )
        return JsonResponse({'status': 'success', 'message': 'SMS sent.', 'message_sid': message.sid})

    except Exception as e:
        logger.error(f"Error sending Twilio SMS: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ── SMS Templates ─────────────────────────────────────────────────────────────
@require_GET
def api_twilio_sms_templates(request):
    """Returns a list of quick-insert SMS templates."""
    templates = [
        {
            "id":    "follow_up",
            "label": "⚡ Quick Follow-Up",
            "text":  "Hi {name}! Just following up on our earlier conversation. Would you be open to a quick 15-min call this week to explore how Transform-Tech can help? 🚀",
        },
        {
            "id":    "demo_invite",
            "label": "📅 Demo Invite",
            "text":  "Hi {name}, I'd love to show you how Transform-Tech's AI-powered ATS & CRM is helping teams like yours hire 3x faster. Can I grab 20 minutes on your calendar?",
        },
        {
            "id":    "value_prop",
            "label": "💡 Value Prop",
            "text":  "Hi {name}! Transform-Tech just launched AI-powered candidate sourcing + buying signal radar. Companies like yours are cutting time-to-hire by 60%. Worth a look?",
        },
        {
            "id":    "check_in",
            "label": "👋 Check-In",
            "text":  "Hey {name}, hope you're doing well! Just wanted to check in — has anything changed on your hiring or CRM needs lately? Happy to reconnect anytime.",
        },
    ]
    return JsonResponse({'status': 'success', 'templates': templates})


# ── AI Draft SMS ──────────────────────────────────────────────────────────────
@csrf_exempt
@require_POST
def api_ai_draft_sms(request):
    """
    Uses Gemini / OpenAI to generate a personalized SMS draft for a contact.
    Accepts: { name, company, context }
    """
    try:
        data    = json.loads(request.body)
        name    = data.get('name', 'there')
        company = data.get('company', '')
        context = data.get('context', '')   # optional extra context

        from openai import OpenAI

        gemini_key = os.environ.get('GEMINI_API_KEY')
        openai_key = os.environ.get('OPENAI_API_KEY')

        if gemini_key:
            client = OpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            model = "gemini-1.5-flash"
        elif openai_key:
            client = OpenAI(api_key=openai_key)
            model  = "gpt-4o-mini"
        else:
            # Fallback without AI
            draft = (
                f"Hi {name}! I wanted to reach out personally about how Transform-Tech "
                f"is helping {company or 'companies like yours'} transform their hiring pipeline. "
                f"Would love to connect — even a 10-min call could be worth it! 🚀"
            )
            return JsonResponse({'status': 'success', 'draft': draft, 'ai': False})

        company_ctx = f" at {company}" if company else ""
        extra_ctx   = f"\n\nAdditional context: {context}" if context else ""

        prompt = (
            f"Write a short, warm, personalized SMS (under 160 characters) from a sales rep at Transform-Tech "
            f"(an enterprise ATS & CRM) to {name}{company_ctx}. "
            f"It should be conversational, not salesy, and invite a quick conversation.{extra_ctx}\n"
            f"Return ONLY the SMS text, nothing else."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You write short, human, personalized sales SMS messages."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.85,
        )
        draft = response.choices[0].message.content.strip().strip('"').strip("'")
        return JsonResponse({'status': 'success', 'draft': draft, 'ai': True})

    except Exception as e:
        logger.error(f"Error generating AI SMS draft: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
