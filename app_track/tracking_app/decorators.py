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
        
        # Admins bypass the paywall
        if user.is_staff or user.is_superuser or user.is_admin_role:
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
