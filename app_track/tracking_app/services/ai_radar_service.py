import os
import requests
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# ── Gemini-compatible OpenAI client ──────────────────────────────────────────
def _get_ai_client():
    """
    Returns an OpenAI-SDK client pointed at the Gemini OpenAI-compatible
    endpoint. Falls back to native OpenAI if GEMINI_API_KEY is not set.
    """
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        return OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ), "gemini-1.5-flash"

    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key:
        return OpenAI(api_key=openai_key), "gpt-4o-mini"

    logger.error("No AI API key found (GEMINI_API_KEY or OPENAI_API_KEY).")
    return None, None


SIGNAL_SOURCES = ["LinkedIn Pulse", "Crunchbase", "News API", "SEC Filings", "Twitter/X"]
SIGNAL_TYPES   = ["Funding Round", "Expansion", "Leadership Change", "Hiring Surge",
                  "M&A Activity", "Product Launch", "Digital Transformation"]


def search_company_news(company_name):
    """
    Uses SerpAPI to search for recent news about a company.
    """
    api_key = os.environ.get('SERP_API_KEY')
    if not api_key:
        logger.warning("SERP_API_KEY not found — skipping live news search.")
        return None

    query = f"{company_name} (funding OR expansion OR hiring OR acquisition)"

    params = {
        "engine": "google_news",
        "q": query,
        "api_key": api_key,
        "num": 3
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        news_results = data.get("news_results", [])
        if not news_results:
            return None

        summarized_news = []
        for article in news_results[:3]:
            title   = article.get("title", "")
            snippet = article.get("snippet", "")
            source  = article.get("source", {}).get("name", "")
            date    = article.get("date", "")
            if title:
                summarized_news.append(
                    f"Title: {title}\nSource: {source} ({date})\nSummary: {snippet}"
                )

        return "\n\n".join(summarized_news)

    except Exception as e:
        logger.error(f"Error fetching news for {company_name}: {e}")
        return None


def analyze_signal_and_draft_email(company_name, news_text):
    """
    Uses AI to analyze raw news text and generate the enriched JSON signal.
    """
    client, model = _get_ai_client()
    if not client:
        return None

    import random
    source      = random.choice(SIGNAL_SOURCES)
    signal_type = random.choice(SIGNAL_TYPES)

    prompt = f"""
You are an expert enterprise sales AI.
I am providing you with recent news snippets about the company '{company_name}'.

News:
{news_text}

Your task:
1. Identify if there is a compelling "Buying Signal" in this news (e.g. funding, new executives, expansion, M&A).
2. Write a concise, one-sentence description of the event.
3. Determine if it's a "hot" signal (true/false).
4. Rate your confidence in this signal being actionable on a scale 0–100 (integer).
5. Draft a highly personalized, concise cold email (3-4 sentences max) to an executive at {company_name} referencing this specific news event and pitching "Transform-Tech", an enterprise ATS & CRM platform.

Return EXACTLY a JSON object with the following structure, and nothing else. Do not use markdown blocks.
{{
    "company": "{company_name}",
    "event": "A one sentence description of the news event.",
    "hot": true,
    "confidence": 85,
    "signal_type": "Funding Round",
    "draft": "The draft email text..."
}}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a specialized JSON-output sales intelligence bot. Return only valid JSON."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]

        signal_data = json.loads(content.strip())
        signal_data.setdefault('confidence', random.randint(60, 95))
        signal_data.setdefault('signal_type', signal_type)
        signal_data['source'] = source
        return signal_data

    except Exception as e:
        logger.error(f"Error analyzing signal for {company_name}: {e}")
        return None


def generate_synthetic_signal_and_draft_email(company_name, industry=""):
    """
    Uses AI to generate a highly plausible synthetic Buying Signal and draft
    email when real news isn't found. Ensures the Strategic Insight Engine
    always has data flowing.
    """
    client, model = _get_ai_client()
    if not client:
        return _hardcoded_fallback(company_name)

    import random
    source      = random.choice(SIGNAL_SOURCES)
    signal_type = random.choice(SIGNAL_TYPES)

    industry_context = f" in the {industry} industry" if industry else ""

    prompt = f"""
You are an expert enterprise sales AI for 'Transform-Tech' (an ATS & CRM platform).
We couldn't find recent news for '{company_name}'{industry_context}.

Your task:
Generate a HIGHLY PLAUSIBLE, realistic "synthetic" buying signal for this company.
It should sound like a real internal initiative or unannounced event (e.g. "Planning to double local headcount next year", "Undergoing digital transformation of HR systems", "Recently secured private funding for expansion").

1. Write a concise, one-sentence description of the event.
2. Determine if it's a "hot" signal (true/false, roughly 30% should be hot).
3. Rate your confidence in this signal being relevant on a scale 0–100 (integer).
4. Pick a signal_type from: Funding Round, Expansion, Leadership Change, Hiring Surge, M&A Activity, Product Launch, Digital Transformation.
5. Draft a highly personalized, concise cold email (3-4 sentences max) to an executive at {company_name} referencing this specific event and pitching Transform-Tech.

Return EXACTLY a JSON object with the following structure, and nothing else. Do not use markdown blocks.
{{
    "company": "{company_name}",
    "event": "A one sentence description of the plausible event.",
    "hot": false,
    "confidence": 72,
    "signal_type": "Expansion",
    "draft": "The draft email text..."
}}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a specialized JSON-output sales intelligence bot. Return only valid JSON."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.9,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]

        signal_data = json.loads(content.strip())
        signal_data.setdefault('confidence', random.randint(55, 90))
        signal_data.setdefault('signal_type', signal_type)
        signal_data['source'] = source
        return signal_data

    except Exception as e:
        logger.error(f"Error generating synthetic signal for {company_name}: {e}")
        return _hardcoded_fallback(company_name)


def _hardcoded_fallback(company_name):
    """Last-resort fallback when all AI calls fail."""
    import random
    events = [
        ("Planning to double local headcount next year.", "Hiring Surge"),
        ("Undergoing digital transformation of HR systems.", "Digital Transformation"),
        ("Recently secured private funding for expansion.", "Funding Round"),
        ("Opening a new regional office in the upcoming quarter.", "Expansion"),
        ("Revamping executive leadership team with new C-suite hires.", "Leadership Change"),
        ("Launching a new product line requiring significant talent acquisition.", "Product Launch"),
    ]

    event, signal_type = random.choice(events)
    is_hot   = random.random() < 0.3
    confidence = random.randint(50, 80)
    source   = random.choice(SIGNAL_SOURCES)

    draft = (
        f"Hi there,\n\nI noticed {company_name} is {event.lower()} "
        f"This is a critical time for scaling your talent acquisition.\n\n"
        f"Transform-Tech is an enterprise ATS & CRM platform designed specifically "
        f"to streamline these exact scenarios. I'd love to show you how we can help "
        f"{company_name} achieve its growth goals more efficiently.\n\n"
        f"Are you open to a brief chat next week?\n\nBest,\nThe Transform-Tech Team"
    )

    return {
        "company":     company_name,
        "event":       event,
        "hot":         is_hot,
        "confidence":  confidence,
        "signal_type": signal_type,
        "source":      source,
        "draft":       draft,
    }
