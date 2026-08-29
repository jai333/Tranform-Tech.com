"""
tracking_app/middleware.py
─────────────────────────────────────────────────────────────
Custom middleware for Transform-Tech

Provides SaaS feature gating based on tenant subscription plan.
"""

from django.shortcuts import redirect
from django.urls import resolve
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

# Feature required by URL namespace
FEATURE_GATES = {
    'it': 'growth',          # IT Helpdesk requires Growth plan
    'sales': 'growth',       # Sales CRM requires Growth plan
    'security': 'enterprise',# SOC Dashboard requires Enterprise plan
    'automation': 'enterprise', # Workflows require Enterprise plan
    'executive': 'enterprise',  # Executive Dash requires Enterprise plan
}

# Plan hierarchy (to check if user has access)
PLAN_LEVELS = {
    'free': 0,
    'starter': 1,
    'growth': 2,
    'enterprise': 3,
}

class FeatureGatingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'tenant') and request.user.tenant:
            current_path = request.path
            
            # Simple path-based gating
            required_plan = None
            if current_path.startswith('/it/'):
                required_plan = FEATURE_GATES['it']
            elif current_path.startswith('/sales/'):
                required_plan = FEATURE_GATES['sales']
            elif current_path.startswith('/security/'):
                required_plan = FEATURE_GATES['security']
            elif current_path.startswith('/automation/'):
                required_plan = FEATURE_GATES['automation']
            elif current_path.startswith('/executive-dashboard/'):
                required_plan = FEATURE_GATES['executive']
                
            if required_plan:
                tenant_plan = request.user.tenant.subscription_plan
                tenant_level = PLAN_LEVELS.get(tenant_plan, 0)
                required_level = PLAN_LEVELS.get(required_plan, 99)
                
                # If plan is insufficient, redirect to billing page
                if tenant_level < required_level:
                    if not request.path.startswith('/billing/'):
                        messages.warning(
                            request, 
                            f"This feature requires the {required_plan.capitalize()} plan. Please upgrade your subscription."
                        )
                        return redirect('billing-page')

        response = self.get_response(request)
        return response
