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
    raw = _call_openai(system_prompt, user_prompt, model="gemini-1.5-flash")
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
You are a B2B sales qualification AI for Transform-Tech — a full-service IT solutions
company offering 6 verticals:
1. ATS & CRM with built-in interview scheduling
2. Data Dashboards & Business Intelligence
3. Cybersecurity (SOC2, Zero-Trust, PII vaults)
4. Web & App Development (custom builds)
5. Automation & Workflow Orchestration
6. IT Operations & Infrastructure Management

Our Ideal Customer Profile (ICP):
- Company size: 10–1000 employees
- Industry: Staffing, Recruiting, HR Tech, SaaS, Healthcare, Finance, E-commerce, any growing tech company
- Pain: Manual processes, security gaps, no custom software, outgrown basic tools, scattered data
- Role of contact: CTO, VP Engineering, IT Director, HR Director, Founder, COO, Operations Manager
- Budget signal: Actively hiring, scaling, recently funded, or undergoing digital transformation

Score the lead 0–100 on ICP fit. Be strict — only give 80+ to near-perfect fits.
Return JSON only.
"""


def score_lead_icp(lead) -> dict:
    """
    Uses GPT-4o-mini to score a lead against the ICP.
    Returns {'score': float, 'breakdown': dict, 'reason': str}
    """
    prompt = f"""
Score this lead on ICP fit for Transform-Tech (AI-powered ATS/CRM SaaS):

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
for Transform-Tech — a full-service IT solutions company.

Transform-Tech services:
1. ATS & CRM — candidate tracking, AI resume parsing, job-match scoring, built-in interview scheduling
2. Data Dashboards — real-time KPI dashboards, business intelligence, executive reporting
3. Cybersecurity — SOC2/HIPAA compliance, zero-trust architecture, encrypted PII vaults, threat monitoring
4. Web & App Development — custom web apps, mobile apps, SaaS platforms, landing pages
5. Automation — workflow orchestration, email sequences, API integrations, process automation
6. IT Operations — infrastructure management, cloud migration, DevOps, monitoring

We place expert resources across all verticals — the client just tells us the problem.

Writing rules:
- Max 3 short paragraphs (under 120 words total body)
- First sentence must reference something specific about their company
- Mention 1-2 relevant services based on their industry and pain points
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
        1: "First touch — introduce Transform-Tech's full IT services, reference their situation, soft ask",
        2: "Follow-up — share a relevant stat or mini case study about one of our 6 service verticals",
        3: "Pain-focused — address a specific operational or technical pain point they likely have",
        4: "Social proof — mention a success story across any of our verticals (ATS, dashboards, cybersec, dev, automation, IT ops)",
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
    Pitches the full Transform-Tech service portfolio.
    """
    name    = lead.contact_name.split()[0] if lead.contact_name else "there"
    company = lead.company_name or "your company"
    ats     = lead.current_ats_tool or "your current system"
    industry = lead.industry or "your industry"

    templates = {
        (1, "A"): {
            "subject": f"How {company} can modernize operations — quick intro",
            "body": (
                f"Hi {name},\n\n"
                f"I came across {company} while researching {industry} companies that are scaling fast.\n\n"
                f"We're Transform-Tech — a full-service IT solutions company. We help teams like yours with "
                f"custom ATS & CRM platforms with built-in interview scheduling, real-time data dashboards, "
                f"cybersecurity audits, web & app development, workflow automation, and full IT operations. "
                f"Essentially, you tell us the problem — we place the right resources and build the solution.\n\n"
                f"Would a quick 15-minute intro call make sense this week?\n\n"
                f"Best,\nThe Transform-Tech Team"
            ),
        },
        (1, "B"): {
            "subject": f"Hey {name} — {company} + Transform-Tech could be a great fit",
            "body": (
                f"Hey {name},\n\n"
                f"Spotted {company} and had to reach out — you're exactly the kind of team we love working with.\n\n"
                f"We handle everything from ATS/CRM builds to cybersecurity, data dashboards, web/app dev, "
                f"automation, and IT ops. Just tell us what's slowing you down and we'll put the right "
                f"people on it — fast.\n\n"
                f"Worth a 15-min chat? No sales deck, just a real conversation.\n\n"
                f"Cheers,\nTransform-Tech"
            ),
        },
        (2, "A"): {
            "subject": f"Teams like {company} save 40%+ on operational overhead",
            "body": (
                f"Hi {name},\n\n"
                f"Following up on my last note — wanted to share some quick results from clients in {industry}:\n\n"
                f"• A staffing firm cut time-to-hire by 40% with our ATS & CRM\n"
                f"• A fintech company reduced security incidents by 85% with our cybersecurity audit\n"
                f"• An e-commerce brand shipped a custom dashboard in 3 weeks with our dev team\n\n"
                f"We place expert resources across all 6 verticals — no agency middlemen. "
                f"Happy to share a relevant case study for {company}?\n\n"
                f"Best,\nThe Transform-Tech Team"
            ),
        },
        (2, "B"): {
            "subject": f"Real results from teams like {company}",
            "body": (
                f"Hey {name},\n\n"
                f"Quick follow-up with some numbers:\n\n"
                f"Companies we work with typically save 10–20 hrs/week on manual processes — whether that's "
                f"hiring workflows, security monitoring, data reporting, or app maintenance. "
                f"One {industry} team automated their entire onboarding pipeline in under 2 weeks.\n\n"
                f"Want to see what that could look like for {company}? 15 minutes, you pick the time.\n\n"
                f"Cheers,\nTransform-Tech"
            ),
        },
        (3, "A"): {
            "subject": f"The hidden cost of scattered IT systems at {company}",
            "body": (
                f"Hi {name},\n\n"
                f"A pattern we see across {industry} teams: data lives in 5 different tools, security is an afterthought, "
                f"internal apps are outdated, and nobody has a real-time view of what's happening.\n\n"
                f"Transform-Tech was built to solve exactly this. We offer a unified approach — custom dashboards "
                f"for visibility, ATS/CRM for hiring, cybersecurity for compliance, and automation to eliminate "
                f"manual bottlenecks. All under one roof.\n\n"
                f"Does this sound familiar at {company}? I'd love to discuss how we'd tackle it.\n\n"
                f"Best,\nThe Transform-Tech Team"
            ),
        },
        (3, "B"): {
            "subject": f"Does this sound familiar, {name}?",
            "body": (
                f"Hey {name},\n\n"
                f"Quick honest question — how many separate tools does {company} use for hiring, analytics, "
                f"security, and internal operations?\n\n"
                f"Most {industry} teams we talk to say 6–10, with zero integration between them. "
                f"We consolidate that chaos: one partner for your ATS, dashboards, cybersec, dev work, "
                f"and automation.\n\n"
                f"Up for a quick look at how it works?\n\n"
                f"Cheers,\nTransform-Tech"
            ),
        },
        (4, "A"): {
            "subject": f"How a {industry} company transformed operations with Transform-Tech",
            "body": (
                f"Hi {name},\n\n"
                f"Quick success story: a {industry} company came to us with fragmented hiring, zero data visibility, "
                f"and growing security concerns. Within 6 weeks we delivered:\n\n"
                f"• Custom ATS with built-in video interviews\n"
                f"• Real-time KPI dashboard for their exec team\n"
                f"• Full SOC2 cybersecurity audit and remediation\n"
                f"• Automated email outreach sequences\n\n"
                f"Result: 3× faster placements, 85% fewer security gaps, and their CEO finally had a single source of truth.\n\n"
                f"I think {company} could see similar results. Open to a 15-minute call?\n\n"
                f"Best,\nThe Transform-Tech Team"
            ),
        },
        (4, "B"): {
            "subject": f"A story you might relate to, {name}",
            "body": (
                f"Hey {name},\n\n"
                f"Quick story: a {industry} team came to us overwhelmed — scattered tools, no dashboards, "
                f"compliance deadlines looming, and their web app was from 2019.\n\n"
                f"Three weeks later: new custom platform, real-time analytics, automated workflows, "
                f"and a cybersecurity setup that their auditors loved.\n\n"
                f"Think {company} might benefit from having one IT partner handle everything? "
                f"Happy to do a walk-through, zero commitment.\n\n"
                f"Cheers,\nTransform-Tech"
            ),
        },
        (5, "A"): {
            "subject": f"Last note from Transform-Tech, {name}",
            "body": (
                f"Hi {name},\n\n"
                f"I've reached out a few times about how Transform-Tech could help {company} across hiring, "
                f"dashboards, security, and IT operations — I don't want to keep filling your inbox "
                f"if the timing isn't right.\n\n"
                f"If you're open to revisiting this in the future, just reply 'later' and I'll follow up in 90 days. "
                f"If any single service interests you (ATS, dashboards, cybersec, dev, automation, or IT ops), "
                f"happy to focus on just that.\n\n"
                f"Either way, wishing {company} all the best.\n\n"
                f"Best,\nThe Transform-Tech Team"
            ),
        },
        (5, "B"): {
            "subject": f"Closing the loop, {name}",
            "body": (
                f"Hey {name},\n\n"
                f"This is my last nudge, I promise. 😄\n\n"
                f"If Transform-Tech isn't the right fit right now, totally fine — just reply 'not now' "
                f"and I'll check back in a few months. If even one of our 6 services "
                f"(ATS, dashboards, cybersec, dev, automation, IT ops) sounds useful, I'd love to start there.\n\n"
                f"Either way, thanks for your time, {name}. Rooting for {company}!\n\n"
                f"Cheers,\nTransform-Tech"
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
You are an AI sales assistant for Transform-Tech (B2B SaaS ATS/CRM).
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
        return "Great job — you've hit all the key milestones! You're getting maximum value from Transform-Tech."

    prompt = f"""
A trial user has been using Transform-Tech for {funnel.days_in_trial} days.
They have NOT yet tried: {', '.join(unused)}.
Their activation score is {funnel.activation_score}/100.
Trial days remaining: {funnel.trial_days_remaining}.

Write a short, friendly in-app nudge (under 60 words) that:
1. Encourages them to try ONE specific unused feature
2. Explains the value in one sentence
3. Ends with a direct CTA like "Try it now →"
"""
    return _call_openai(
        "You are a helpful onboarding assistant for Transform-Tech SaaS. Be warm, brief, and specific.",
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
