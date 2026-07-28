from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def paid_required(view_func):
    """
    Decorator for views that checks that the user's tenant has an active paid subscription.
    If the user is an admin or staff, they bypass this check.
    If the user's tenant is on a 'free' plan, redirects to the billing page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Admins or users with explicit permissions bypass the paywall
        if user.is_staff or user.is_superuser or user.is_admin_role or user.can_view_it or user.can_view_ats or user.can_view_sales or user.can_view_executive:
            return view_func(request, *args, **kwargs)
            
        # Ensure user has a tenant
        if not user.tenant:
            messages.warning(request, "You must initialize a workspace first.")
            return redirect('register')
            
        # Check if the tenant is paid
        if not user.tenant.is_paid:
            messages.info(request, "This dashboard is a premium feature. Please upgrade your workspace to access it.")
            return redirect('billing-page')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def require_ats_access(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.can_view_ats):
            messages.error(request, "You do not have permission to access the ATS Module.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def require_sales_access(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.can_view_sales):
            messages.error(request, "You do not have permission to access the Sales Module.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def require_it_access(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.can_view_it):
            messages.error(request, "You do not have permission to access the IT Helpdesk.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def require_executive_access(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.can_view_executive):
            messages.error(request, "You do not have permission to access the Executive Dashboard.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def require_tier(min_tier):
    """
    Checks if the user's tenant meets the minimum required tier.
    Order: free < starter < growth < enterprise
    """
    tiers = {'free': 0, 'starter': 1, 'growth': 2, 'enterprise': 3}
    
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser or request.user.is_staff or request.user.is_admin_role or request.user.can_view_it or request.user.can_view_ats or request.user.can_view_sales or request.user.can_view_executive:
                return view_func(request, *args, **kwargs)
                
            tenant = request.user.tenant
            if not tenant:
                messages.warning(request, "You must initialize a workspace first.")
                return redirect('register')
                
            current_tier = tenant.subscription_plan or 'free'
            if tiers.get(current_tier, 0) < tiers.get(min_tier, 0):
                messages.warning(request, f"This feature requires the {min_tier.title()} tier. Please ask your administrator to upgrade.")
                return redirect('billing-page')
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
