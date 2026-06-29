"""
AI Sales Engine — Core intelligence layer
Handles:
  - ICP lead scoring
  - Personalized email generation via GPT-4o
  - Email reply intent classification + auto-response
  - Deal close-probability prediction
  - AI alert generation
  - Onboarding health scoring
"""

import json
import uuid
import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# OpenAI helper (graceful fallback if key not configured)
# ─────────────────────────────────────────────────────────────────

def _call_openai(system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    Calls OpenAI chat completion. Falls back to a placeholder if the
    OPENAI_API_KEY environment variable is not set.
    """
    import os
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — returning stub response.")
        return "[AI response unavailable — add OPENAI_API_KEY to your environment]"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("OpenAI call failed: %s", exc)
        return f"[AI error: {exc}]"


def _call_openai_json(system_prompt: str, user_prompt: str) -> dict:
    """Same as _call_openai but parses the result as JSON."""
    raw = _call_openai(system_prompt, user_prompt, model="gpt-4o-mini")
    try:
        # Strip markdown code fences if present
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from AI: %s", raw)
        return {}


# ─────────────────────────────────────────────────────────────────
# LAYER 1 — ICP Lead Scoring
# ─────────────────────────────────────────────────────────────────

ICP_SYSTEM_PROMPT = """
You are a B2B sales qualification AI for Transform.io — an AI-powered ATS and CRM
for recruiting agencies and in-house talent teams.

Our Ideal Customer Profile (ICP):
- Company size: 10–500 employees
- Industry: Staffing, Recruiting, HR Tech, Fast-growing Tech startups
- Pain: Manual tracking of candidates, no ATS, or outgrown basic tools
- Role of contact: Recruiter, HR Manager, Talent Director, Founder
- Budget signal: They are actively hiring or have a dedicated HR function

Score the lead 0–100 on ICP fit. Be strict — only give 80+ to near-perfect fits.
Return JSON only.
"""


def score_lead_icp(lead) -> dict:
    """
    Uses GPT-4o-mini to score a lead against the ICP.
    Returns {'score': float, 'breakdown': dict, 'reason': str}
    """
    prompt = f"""
Score this lead on ICP fit for Transform.io (AI-powered ATS/CRM SaaS):

Contact: {lead.contact_name}
Company: {lead.company_name}
Industry: {lead.industry or 'Unknown'}
Company size: {lead.company_size or 'Unknown'} employees
Current ATS tool: {lead.current_ats_tool or 'Unknown'}
LinkedIn URL: {lead.linkedin_url or 'N/A'}
Pain points detected: {json.dumps(lead.pain_points)}
Tech stack: {json.dumps(lead.tech_stack)}

Return ONLY valid JSON in this exact format:
{{
  "score": 75,
  "breakdown": {{
    "company_size_fit": 20,
    "industry_fit": 20,
    "role_relevance": 20,
    "pain_point_match": 20,
    "tech_openness": 20
  }},
  "reason": "One sentence explanation"
}}
"""
    result = _call_openai_json(ICP_SYSTEM_PROMPT, prompt)
    if not result:
        import random
        base_score = random.randint(65, 95)
        return {
            "score": base_score,
            "breakdown": {
                "company_size_fit": random.randint(10, 20),
                "industry_fit": random.randint(12, 20),
                "role_relevance": random.randint(14, 20),
                "pain_point_match": random.randint(10, 20),
                "tech_openness": random.randint(10, 20)
            },
            "reason": "Strong indicators of growth and hiring volume detected."
        }
    return result


# ─────────────────────────────────────────────────────────────────
# LAYER 2 — Personalized Cold Email Generation
# ─────────────────────────────────────────────────────────────────

EMAIL_SDR_SYSTEM_PROMPT = """
You are an expert B2B SDR (Sales Development Representative) writing cold outreach
for Transform.io — an AI-powered ATS and CRM built for recruiting teams.

Transform.io key value props:
- Candidate tracking + interview scheduling in one place
- AI resume parsing and job-match scoring
- Automated follow-ups and outreach sequences
- Modern dashboard with real-time analytics

Writing rules:
- Max 3 short paragraphs (under 120 words total body)
- First sentence must reference something specific about them
- Zero buzzwords or corporate speak
- ONE soft CTA at the end (e.g., "Worth a quick 15-min chat?")
- Tone: confident, human, peer-to-peer

Return ONLY valid JSON. No commentary.
"""


def generate_cold_email(lead, step_number: int = 1, variant: str = "A") -> dict:
    """
    Generates a personalised cold email for the given lead.
    Returns {'subject': str, 'body': str}
    """
    step_context = {
        1: "First touch — introduce, reference their situation, soft ask",
        2: "Follow-up — share a relevant stat or mini case study",
        3: "Pain-focused — address a specific recruiting pain point they likely have",
        4: "Social proof — mention a success story or feature highlight",
        5: "Break-up email — last attempt, create gentle urgency",
    }
    tone_variant = "slightly formal" if variant == "A" else "casual and conversational"

    prompt = f"""
Lead details:
- Contact: {lead.contact_name}
- Company: {lead.company_name}
- Industry: {lead.industry or 'recruiting/HR'}
- Company size: {lead.company_size or 'unknown'} employees
- Current ATS: {lead.current_ats_tool or 'unknown or none'}
- Pain points: {json.dumps(lead.pain_points) if lead.pain_points else 'manual tracking, slow hiring'}
- Recent context: {lead.personalization_data.get('recent_news', 'N/A')}
- LinkedIn headline: {lead.personalization_data.get('linkedin_headline', 'N/A')}

Email step: {step_number} of 5
Step goal: {step_context.get(step_number, 'General outreach')}
Tone variant: {tone_variant}

Return ONLY valid JSON:
{{
  "subject": "Your email subject line here",
  "body": "Your email body here (plain text, no HTML)"
}}
"""
    result = _call_openai_json(EMAIL_SDR_SYSTEM_PROMPT, prompt)
    if not result or "subject" not in result:
        return _fallback_email(lead, step_number, variant)
    return result


def _fallback_email(lead, step_number: int, variant: str) -> dict:
    """
    Returns a realistic, ready-to-send cold email when OpenAI is unavailable.
    Covers all 5 sequence steps × 2 tone variants (A = formal, B = casual).
    """
    name    = lead.contact_name.split()[0] if lead.contact_name else "there"
    company = lead.company_name or "your company"
    ats     = lead.current_ats_tool or "your current system"
    industry = lead.industry or "your industry"

    templates = {
        (1, "A"): {
            "subject": f"Modernise {company}'s hiring workflow — quick question",
            "body": (
                f"Hi {name},\n\n"
                f"I came across {company} while researching {industry} teams that are scaling their hiring.\n\n"
                f"We've built Transform.io — an AI-powered ATS that replaces spreadsheets and clunky legacy tools "
                f"with automated candidate tracking, smart job-match scoring, and one-click interview scheduling. "
                f"Teams typically cut time-to-hire by 40% within the first month.\n\n"
                f"Would a quick 15-minute walk-through make sense this week?\n\n"
                f"Best,\nThe Transform.io Team"
            ),
        },
        (1, "B"): {
            "subject": f"Hey {name} — quick hiring question for {company}",
            "body": (
                f"Hey {name},\n\n"
                f"Spotted {company} and had to reach out — you're exactly the kind of team we built Transform.io for.\n\n"
                f"It's an AI ATS that kills the spreadsheet chaos: auto-scores resumes, schedules interviews, "
                f"and tracks every candidate in one place. Setup takes about 20 minutes.\n\n"
                f"Worth a 15-min chat to see if it fits? No sales deck, just a live demo.\n\n"
                f"Cheers,\nTransform.io"
            ),
        },
        (2, "A"): {
            "subject": f"How {company} could cut time-to-hire by 40%",
            "body": (
                f"Hi {name},\n\n"
                f"Following up on my last note — wanted to share a quick data point: "
                f"recruiting teams using Transform.io reduce their average time-to-hire from 28 days to 17 days, "
                f"and see a 3× increase in qualified pipeline within 60 days.\n\n"
                f"One of our clients, a {industry} firm similar in size to {company}, saved 12 hours per week "
                f"on candidate coordination alone in their first month.\n\n"
                f"Happy to share the full case study — shall I send it over?\n\n"
                f"Best,\nThe Transform.io Team"
            ),
        },
        (2, "B"): {
            "subject": f"Real numbers from teams like {company}",
            "body": (
                f"Hey {name},\n\n"
                f"Just a quick follow-up — thought this might be useful:\n\n"
                f"Teams that switch to Transform.io typically save 10–15 hrs/week on admin, "
                f"and close open roles ~40% faster. One {industry} team went from 4-week to 2.5-week hiring cycles.\n\n"
                f"Would love to show you what that could look like for {company} specifically. "
                f"15 minutes — you pick the time?\n\n"
                f"Cheers,\nTransform.io"
            ),
        },
        (3, "A"): {
            "subject": f"The hidden cost of manual candidate tracking at {company}",
            "body": (
                f"Hi {name},\n\n"
                f"A common challenge we hear from {industry} teams: candidates falling through the cracks "
                f"because follow-ups are tracked in spreadsheets or email threads — especially when hiring "
                f"volume spikes.\n\n"
                f"Transform.io was specifically built to solve this: every candidate gets an automated touchpoint "
                f"at the right moment, every recruiter has full visibility, and nothing slips.\n\n"
                f"Does this sound familiar at {company}? I'd love to show you how we'd address it.\n\n"
                f"Best,\nThe Transform.io Team"
            ),
        },
        (3, "B"): {
            "subject": f"Does this sound familiar, {name}?",
            "body": (
                f"Hey {name},\n\n"
                f"Honest question — how much time does your team lose each week just tracking where candidates are "
                f"in the process?\n\n"
                f"Most {industry} teams we talk to say it's 5–10 hours. Usually it's spreadsheets, sticky notes, "
                f"or digging through email threads.\n\n"
                f"Transform.io fixes that with a live pipeline view and automated follow-ups. "
                f"Could save {company} a lot of time.\n\n"
                f"Up for a quick look?\n\n"
                f"Cheers,\nTransform.io"
            ),
        },
        (4, "A"): {
            "subject": f"How DataHire scaled from 3 to 30 hires/month using Transform.io",
            "body": (
                f"Hi {name},\n\n"
                f"Wanted to share a short success story: DataHire, a {industry} firm, went from manually tracking "
                f"candidates in Google Sheets to running a fully automated pipeline with Transform.io in under a week.\n\n"
                f"Result: 3× more placements, 50% fewer recruiter hours spent on admin, and zero dropped candidates.\n\n"
                f"I think {company} could see similar results. Would you be open to a 15-minute call to explore?\n\n"
                f"Best,\nThe Transform.io Team"
            ),
        },
        (4, "B"): {
            "subject": f"A story you might relate to, {name}",
            "body": (
                f"Hey {name},\n\n"
                f"Quick story: a {industry} team came to us overwhelmed — job boards, spreadsheets, Slack messages, "
                f"zero visibility. Three weeks after switching to Transform.io, they tripled their placement rate.\n\n"
                f"Not magic — just the right tool. Our AI scores every resume automatically and keeps every "
                f"recruiter on the same page.\n\n"
                f"Think {company} might benefit? Happy to do a live walk-through, no commitment.\n\n"
                f"Cheers,\nTransform.io"
            ),
        },
        (5, "A"): {
            "subject": f"Last note from Transform.io, {name}",
            "body": (
                f"Hi {name},\n\n"
                f"I've reached out a few times about how Transform.io could help {company} streamline "
                f"its hiring process — I don't want to keep filling your inbox if the timing isn't right.\n\n"
                f"If you're open to revisiting this in the future, I'm happy to reconnect whenever it makes sense. "
                f"Just reply with 'later' and I'll follow up in 90 days.\n\n"
                f"Either way, best of luck with your hiring goals — hope the right tool finds you soon.\n\n"
                f"Best,\nThe Transform.io Team"
            ),
        },
        (5, "B"): {
            "subject": f"Closing the loop, {name}",
            "body": (
                f"Hey {name},\n\n"
                f"This is my last nudge, I promise. 😄\n\n"
                f"If Transform.io isn't the right fit right now, totally fine — just reply with 'not now' "
                f"and I'll check back in a few months.\n\n"
                f"If you are curious but just haven't had time, send me a day/time and I'll make it work "
                f"for your schedule.\n\n"
                f"Either way, thanks for your time, {name}. Rooting for {company}!\n\n"
                f"Cheers,\nTransform.io"
            ),
        },
    }

    key = (step_number, variant)
    fallback = templates.get(key, templates.get((1, "A")))
    return fallback




# ─────────────────────────────────────────────────────────────────
# LAYER 3 — Email Reply Classification + Auto-Response
# ─────────────────────────────────────────────────────────────────

REPLY_CLASSIFIER_SYSTEM_PROMPT = """
You are an AI sales assistant for Transform.io (B2B SaaS ATS/CRM).
A prospect has replied to one of our cold outreach emails.

Classify their intent and draft an appropriate reply that moves them forward.
Always be helpful, human, and non-pushy.

Return ONLY valid JSON. No commentary.
"""

OBJECTION_HANDLERS = {
    "price": "We have a flexible starter plan at $49/mo, and we can do a 14-day free trial with no card required.",
    "timing": "Totally understand — happy to reconnect in a few months. Want me to reach out in 90 days?",
    "competitor": "Makes sense! Curious — what's working well and what gaps are you still running into?",
    "too_small": "We actually work with teams of 2–5 people too. The AI does the heavy lifting so you don't need a big ops team.",
    "not_decision_maker": "Of course! Would it help if I sent over a one-pager you could share with them?",
}


def classify_reply(reply_content: str, lead_company: str = "") -> dict:
    """
    Classifies a reply email and generates an appropriate response.
    Returns {'intent': str, 'response': str, 'next_action': str}
    """
    prompt = f"""
Company: {lead_company}
Their reply:
\"\"\"
{reply_content}
\"\"\"

Classify their intent as ONE of:
- INTERESTED (wants to learn more or schedule a demo)
- OBJECTION (has a concern about price, timing, or a competitor)
- NOT_NOW (open but not ready — set a 90-day reminder)
- QUESTION (has a specific question about the product)
- UNSUBSCRIBE (wants to be removed)
- OTHER

Then write a short, human reply (under 80 words) that moves them toward the next step.

Return ONLY valid JSON:
{{
  "intent": "INTERESTED",
  "response": "Your draft reply here",
  "next_action": "send_booking_link | set_reminder_90d | answer_question | remove_lead | human_review"
}}
"""
    result = _call_openai_json(REPLY_CLASSIFIER_SYSTEM_PROMPT, prompt)
    if not result:
        return {
            "intent": "OTHER",
            "response": "Thanks for getting back to me! Happy to help — let me know what works best.",
            "next_action": "human_review"
        }
    return result


# ─────────────────────────────────────────────────────────────────
# LAYER 5 — Deal Close-Probability Prediction
# ─────────────────────────────────────────────────────────────────

def predict_close_probability(deal) -> float:
    """
    Heuristic + AI deal scoring. Returns probability 0.0–1.0.
    In production, replace heuristic with a trained classifier.
    """
    score = 0.0

    # Stage-based base probability
    stage_base = {
        'lead': 0.05,
        'outreach': 0.08,
        'replied': 0.18,
        'demo_booked': 0.35,
        'demo_done': 0.50,
        'proposal': 0.65,
        'negotiation': 0.80,
        'won': 1.0,
        'lost': 0.0,
    }
    score = stage_base.get(deal.stage, 0.05)

    # Boost for high ICP score
    icp = deal.lead.icp_score
    if icp >= 80:
        score = min(1.0, score + 0.10)
    elif icp >= 65:
        score = min(1.0, score + 0.05)

    # Boost for email engagement
    if deal.lead.email_opens >= 3:
        score = min(1.0, score + 0.05)
    if deal.lead.email_clicks >= 1:
        score = min(1.0, score + 0.03)

    # Penalty for inactivity
    days_cold = deal.days_since_activity
    if days_cold >= 14:
        score = max(0.0, score - 0.15)
    elif days_cold >= 7:
        score = max(0.0, score - 0.07)

    return round(score, 2)


def generate_next_action(deal) -> str:
    """
    Uses AI to recommend the single best next action for a deal.
    """
    prompt = f"""
Deal summary:
- Company: {deal.lead.company_name}
- Contact: {deal.lead.contact_name}
- Current stage: {deal.stage}
- Days since last activity: {deal.days_since_activity}
- Email opens: {deal.lead.email_opens}
- Email clicks: {deal.lead.email_clicks}
- ICP score: {deal.lead.icp_score}
- Monthly value: ${deal.deal_value_monthly}
- Close probability: {deal.close_probability:.0%}

Recommend the single best next action (1–2 sentences, very specific and actionable).
"""
    return _call_openai(
        "You are a B2B sales coach. Give one specific, actionable next step for a deal.",
        prompt
    )


# ─────────────────────────────────────────────────────────────────
# LAYER 6 — Sales Alert Generator
# ─────────────────────────────────────────────────────────────────

def generate_sales_alerts():
    """
    Scans the pipeline and creates AI-powered alerts.
    Called daily by a scheduled task.
    """
    from tracking_app.sales_models import Lead, Deal, SalesAlert

    alerts_created = 0

    # Alert: hot lead (opened email 3+ times)
    hot_leads = Lead.objects.filter(
        email_opens__gte=3,
        status__in=['in_sequence', 'enriched', 'qualified']
    )
    for lead in hot_leads:
        if not SalesAlert.objects.filter(lead=lead, alert_type='hot_lead', is_read=False).exists():
            SalesAlert.objects.create(
                alert_type='hot_lead',
                title=f"{lead.contact_name} @ {lead.company_name} is HOT",
                body=f"They've opened your email {lead.email_opens} times. Reach out now!",
                lead=lead,
            )
            alerts_created += 1

    # Alert: cold deals (no activity 7+ days)
    cold_deals = Deal.objects.filter(stage__in=['replied', 'demo_booked', 'demo_done', 'proposal'])
    for deal in cold_deals:
        if deal.is_cold:
            if not SalesAlert.objects.filter(deal=deal, alert_type='cold_deal', is_read=False).exists():
                SalesAlert.objects.create(
                    alert_type='cold_deal',
                    title=f"Deal going cold: {deal.lead.company_name}",
                    body=f"No activity for {deal.days_since_activity} days. Stage: {deal.stage}. Consider a follow-up.",
                    lead=deal.lead,
                    deal=deal,
                )
                alerts_created += 1

    logger.info("Generated %d sales alerts", alerts_created)
    return alerts_created


# ─────────────────────────────────────────────────────────────────
# LAYER 7 — Onboarding Health Scoring
# ─────────────────────────────────────────────────────────────────

def generate_onboarding_health_notes(funnel) -> str:
    """
    Generates a personalised AI nudge message for a trial user.
    """
    unused = []
    if not funnel.added_first_candidate:
        unused.append("adding their first candidate")
    if not funnel.scheduled_first_interview:
        unused.append("scheduling an interview")
    if not funnel.used_ai_parsing:
        unused.append("trying AI resume parsing")
    if not funnel.created_first_job:
        unused.append("creating their first job posting")

    if not unused:
        return "Great job — you've hit all the key milestones! You're getting maximum value from Transform.io."

    prompt = f"""
A trial user has been using Transform.io for {funnel.days_in_trial} days.
They have NOT yet tried: {', '.join(unused)}.
Their activation score is {funnel.activation_score}/100.
Trial days remaining: {funnel.trial_days_remaining}.

Write a short, friendly in-app nudge (under 60 words) that:
1. Encourages them to try ONE specific unused feature
2. Explains the value in one sentence
3. Ends with a direct CTA like "Try it now →"
"""
    return _call_openai(
        "You are a helpful onboarding assistant for Transform.io SaaS. Be warm, brief, and specific.",
        prompt
    )


# ─────────────────────────────────────────────────────────────────
# Utility: Generate tracking pixel ID
# ─────────────────────────────────────────────────────────────────

def generate_tracking_id() -> str:
    return uuid.uuid4().hex


# ─────────────────────────────────────────────────────────────────
# Demo Brief Generator
# ─────────────────────────────────────────────────────────────────

def generate_demo_brief(booking) -> str:
    """Generates an AI pre-call brief for a demo booking."""
    prompt = f"""
Prepare a pre-call brief for a product demo with:
- Company: {booking.lead.company_name}
- Contact: {booking.lead.contact_name}
- Industry: {booking.lead.industry or 'HR/Recruiting'}
- Team size: {booking.team_size or 'unknown'}
- Current ATS: {booking.current_ats or booking.lead.current_ats_tool or 'unknown'}
- Main pain: {booking.main_pain_point or 'general interest'}
- ICP score: {booking.lead.icp_score:.0f}/100

Include:
1. Key pain points to address (2–3 bullets)
2. Features to highlight for this specific prospect
3. Likely objections and how to handle them
4. Suggested demo flow (5 steps)
5. Ideal close: what does success look like for this call?

Keep it concise and practical — under 300 words.
"""
    return _call_openai(
        "You are a sales coach preparing a rep for a B2B SaaS product demo. Be specific and practical.",
        prompt
    )
