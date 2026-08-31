
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import ITTicket

@login_required
def client_portal(request):
    if request.user.role != "client":
        return redirect("standard-ops-dashboard")
        
    tenant = request.user.tenant
    
    # Clients can only see tickets they submitted
    my_tickets = ITTicket.objects.filter(tenant=tenant, submitted_by=request.user).order_by("-created_at") if hasattr(ITTicket, "created_at") else ITTicket.objects.filter(tenant=tenant, submitted_by=request.user).order_by("-id")
    
    context = {
        "tickets": my_tickets,
        "tenant": tenant,
    }
    return render(request, "tracking_app/client_portal.html", context)
