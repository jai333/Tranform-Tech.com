
import openai
from django.conf import settings
from .sales_models import Deal
from .models import ITTicket
import json
import logging

def predict_deal_churn(deal_id):
    try:
        deal = Deal.objects.get(id=deal_id)
        tenant = getattr(deal, "tenant", None)
        
        domain = deal.lead.email.split("@")[-1] if deal.lead.email else ""
        if not domain or domain in ["gmail.com", "yahoo.com", "hotmail.com"]:
            return
            
        tickets = ITTicket.objects.filter(
            tenant=tenant,
            submitted_by__email__icontains="@" + domain
        ).order_by("-id")[:10]
        
        if not tickets.exists():
            deal.churn_risk_score = 0
            deal.churn_risk_level = "low"
            deal.churn_analysis_summary = "No recent IT tickets. Account appears healthy."
            deal.save(update_fields=["churn_risk_score", "churn_risk_level", "churn_analysis_summary"])
            return
            
        ticket_summaries = []
        for t in tickets:
            ticket_summaries.append(f"- Priority: {t.get_priority_display()}, Status: {t.get_status_display()}, Issue: {t.title}")
            
        ticket_str = "\n".join(ticket_summaries)
        
        prompt = f"""
        You are a highly advanced AI Churn Predictor for an Enterprise OS.
        We have a client whose domain is {domain}. Their contract value is ${deal.deal_value_annual}.
        
        Here are their recent IT Support tickets:
        {ticket_str}
        
        Analyze these tickets. Are they experiencing critical, recurring platform issues that indicate they are frustrated and might cancel their contract (churn)?
        
        Respond ONLY with a JSON object in this exact format:
        {{
            "risk_score": 75,
            "risk_level": "high",
            "analysis": "They have had 3 critical server outages in the past month. High risk of churn."
        }}
        """
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a predictive churn AI. Always respond in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        deal.churn_risk_score = result.get("risk_score", 0)
        deal.churn_risk_level = result.get("risk_level", "low")
        deal.churn_analysis_summary = result.get("analysis", "")
        deal.save(update_fields=["churn_risk_score", "churn_risk_level", "churn_analysis_summary"])
        
    except Exception as e:
        logging.error(f"Churn Prediction Error: {e}")
