"""
tracking_app/billing_views.py
─────────────────────────────────────────────────────────────
Stripe billing integration for Transform.io SaaS.

Endpoints:
  /billing/            — Pricing page for tenant admin
  /billing/checkout/   — Create Stripe Checkout session
  /billing/success/    — Post-payment success page
  /billing/portal/     — Stripe Customer Portal (manage subscription)
  /billing/webhook/    — Stripe webhook receiver (confirm payment)
"""

import json
from django.views.decorators.http import require_POST
import logging
import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

# ── Stripe Price IDs (set these in settings after creating plans on Stripe) ─
PLANS = {
    "starter": {
        "name": "Starter Plan",
        "price": "$99",
        "period": "/ month",
        "features": [
            "ATS & Candidate Tracking",
            "CRM & Account Management",
            "Up to 10 users",
            "Email support",
        ],
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_STARTER", ""),
        "color": "#10b981",
    },
    "growth": {
        "name": "Pro Plan",
        "price": "$299",
        "period": "/ month",
        "features": [
            "Everything in Starter",
            "IT Helpdesk & Asset Management",
            "AI Sales Automation",
            "Unified Inbox",
            "Up to 50 users",
            "Priority support",
        ],
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_GROWTH", ""),
        "color": "#00E5FF",
        "popular": True,
    },
    "enterprise": {
        "name": "Enterprise Plan",
        "price": "$799",
        "period": "/ month",
        "features": [
            "Everything in Growth",
            "SOC Threat Dashboard",
            "Executive Analytics",
            "Workflow Automation",
            "Unlimited users",
            "Dedicated account manager",
            "Custom integrations",
        ],
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_ENTERPRISE", ""),
        "color": "#8b5cf6",
    },
}


def _get_stripe():
    """Return configured stripe module or None if keys not set."""
    key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not key:
        return None
    stripe.api_key = key
    
    # Fix for macOS Python SSL certificate verify failures in local dev
    if getattr(settings, "DEBUG", False):
        stripe.verify_ssl_certs = False
        
    return stripe


# ─────────────────────────────────────────────────────────────
# Billing / Pricing Page
# ─────────────────────────────────────────────────────────────

@login_required
def billing_page(request):
    """Display the pricing page with current subscription status."""
    tenant = getattr(request.user, "tenant", None)
    current_plan = "free"

    if tenant:
        try:
            current_plan = tenant.subscription_plan
        except AttributeError:
            current_plan = "free"

    active_plan_obj = None
    if current_plan != "free" and current_plan in PLANS:
        active_plan_obj = PLANS[current_plan]

    context = {
        "page_title": "Billing & Subscription",
        "plans": PLANS,
        "current_plan": current_plan,
        "active_plan": active_plan_obj,
        "tenant": tenant,
        "stripe_pub_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
    }
    return render(request, "tracking_app/billing.html", context)


# ─────────────────────────────────────────────────────────────
# Create Stripe Checkout Session
# ─────────────────────────────────────────────────────────────

@login_required
def create_checkout_session(request, plan_key=None):
    """Create a Stripe Checkout session for the selected plan."""
    if not plan_key:
        plan_key = request.POST.get("plan") or request.GET.get("plan")
        
    if plan_key not in PLANS:
        return JsonResponse({"error": "Invalid plan."}, status=400)

    plan = PLANS[plan_key]
    # Mock checkout instead of Stripe API
    return render(request, "tracking_app/mock_checkout.html", {
        "plan_key": plan_key
    })

@login_required
@require_POST
def mock_checkout_process(request):
    plan_key = request.POST.get("plan_key")
    if plan_key in PLANS:
        tenant = request.user.tenant
        if tenant:
            tenant.subscription_plan = plan_key
            tenant.save()
    return redirect(f"/billing/success/?session_id=mock_session_{plan_key}")


# ─────────────────────────────────────────────────────────────
# Post-Payment Success Page
# ─────────────────────────────────────────────────────────────

@login_required
def billing_success(request):
    session_id = request.GET.get("session_id")
    return render(request, "tracking_app/billing_success.html", {
        "page_title": "Payment Successful",
        "session_id": session_id,
    })


# ─────────────────────────────────────────────────────────────
# Stripe Customer Portal
# ─────────────────────────────────────────────────────────────

@login_required
def billing_portal(request):
    """Redirect tenant admin to Stripe customer portal to manage subscription."""
    stripe_module = _get_stripe()
    if not stripe_module:
        from django.contrib import messages
        messages.error(request, "Stripe is not configured.")
        return redirect("billing-page")

    try:
        tenant = request.user.tenant
        customer_id = getattr(tenant, "stripe_customer_id", None)
        if not customer_id:
            from django.contrib import messages
            messages.error(request, "No active subscription found.")
            return redirect("billing-page")

        portal = stripe_module.billing_portal.Session.create(
            customer=customer_id,
            return_url=request.build_absolute_uri("/billing/"),
        )
        return redirect(portal.url, permanent=False)
    except Exception as e:
        logger.error("Billing portal error: %s", e)
        from django.contrib import messages
        messages.error(request, f"Error accessing portal: {e}")
        return redirect("billing-page")


# ─────────────────────────────────────────────────────────────
# Stripe Webhook Handler
# ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Receive Stripe webhook events and update subscription status.
    Critical events: checkout.session.completed, customer.subscription.deleted
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    stripe_module = _get_stripe()
    if not stripe_module:
        return HttpResponse(status=400)

    try:
        if webhook_secret:
            event = stripe_module.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = json.loads(payload)
    except Exception as e:
        logger.error("Stripe webhook signature error: %s", e)
        return HttpResponse(status=400)

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(data)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_cancelled(data)
        elif event_type == "invoice.payment_failed":
            _handle_payment_failed(data)
    except Exception as e:
        logger.error("Stripe webhook handler error for %s: %s", event_type, e)

    return HttpResponse(status=200)


def _handle_checkout_completed(session):
    from tracking_app.models import Tenant
    tenant_id = session.get("metadata", {}).get("tenant_id")
    plan = session.get("metadata", {}).get("plan", "starter")
    customer_id = session.get("customer")

    if tenant_id:
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            tenant.subscription_plan = plan
            tenant.stripe_customer_id = customer_id
            tenant.save(update_fields=["subscription_plan", "stripe_customer_id"])
            logger.info("Tenant %s upgraded to plan: %s", tenant_id, plan)
        except Tenant.DoesNotExist:
            logger.warning("Tenant %s not found for checkout completion", tenant_id)


def _handle_subscription_cancelled(subscription):
    from tracking_app.models import Tenant
    customer_id = subscription.get("customer")
    try:
        tenant = Tenant.objects.get(stripe_customer_id=customer_id)
        tenant.subscription_plan = "free"
        tenant.save(update_fields=["subscription_plan"])
        logger.info("Tenant %s subscription cancelled", tenant.id)
    except Tenant.DoesNotExist:
        pass


def _handle_payment_failed(invoice):
    logger.warning("Payment failed for customer: %s", invoice.get("customer"))
