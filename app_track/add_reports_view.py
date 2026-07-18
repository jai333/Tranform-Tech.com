import re

reports_view = """
import json
from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta

@login_required
def it_reports(request):
    if not request.user.is_it_agent:
        raise PermissionDenied("Only IT staff can view reports.")
        
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    base_qs = ITTicket.objects.filter(created_at__gte=start_date)
    
    # 1. Volume over time
    volume_data = list(base_qs.extra({'day': "date(created_at)"}).values('day').annotate(count=Count('id')).order_by('day'))
    volume_labels = [str(item['day']) for item in volume_data]
    volume_counts = [item['count'] for item in volume_data]
    
    # 2. Tickets by Category
    category_data = list(base_qs.values('category').annotate(count=Count('id')))
    category_labels = [dict(ITTicket.CATEGORY_CHOICES).get(item['category'], item['category']) for item in category_data]
    category_counts = [item['count'] for item in category_data]
    
    # 3. Agent Performance (MTTR)
    resolved_qs = base_qs.filter(status__in=['resolved', 'closed'], resolved_at__isnull=False)
    
    agent_data = []
    agents = User.objects.filter(role__in=['admin', 'it_agent'])
    for agent in agents:
        agent_tickets = resolved_qs.filter(assigned_to=agent)
        total = agent_tickets.count()
        if total > 0:
            total_time = sum((t.resolved_at - t.created_at).total_seconds() for t in agent_tickets)
            avg_hours = round(total_time / total / 3600, 1)
            agent_data.append({
                'name': agent.get_full_name() or agent.username,
                'resolved_count': total,
                'mttr': avg_hours
            })
            
    # Calculate overall MTTR and SLA Compliance for the period
    overall_mttr = 0
    if resolved_qs.exists():
        total_time = sum((t.resolved_at - t.created_at).total_seconds() for t in resolved_qs)
        overall_mttr = round(total_time / resolved_qs.count() / 3600, 1)
        
    total_tickets = base_qs.count()
    sla_breached = base_qs.filter(sla_status='breached').count()
    compliance_rate = 100
    if total_tickets > 0:
        compliance_rate = round(((total_tickets - sla_breached) / total_tickets) * 100, 1)

    context = {
        'page_title': 'IT Reports & Analytics',
        'days': days,
        'volume_labels': json.dumps(volume_labels),
        'volume_counts': json.dumps(volume_counts),
        'category_labels': json.dumps(category_labels),
        'category_counts': json.dumps(category_counts),
        'agent_data': agent_data,
        'overall_mttr': overall_mttr,
        'compliance_rate': compliance_rate,
        'total_tickets': total_tickets
    }
    return render(request, 'tracking_app/it_reports.html', context)
"""

with open('tracking_app/views.py', 'r') as f:
    content = f.read()

if "def it_reports" not in content:
    with open('tracking_app/views.py', 'a') as f:
        f.write(reports_view)
    print("Added reports view.")
else:
    print("Reports view exists.")
