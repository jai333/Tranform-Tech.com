import re

with open('views.py', 'r') as f:
    content = f.read()

# 1. Update it_helpdesk_list
it_helpdesk_target = """    columns = {s: list(base_qs.filter(status=s)) for s in statuses}
    context = {"""

it_helpdesk_replace = """    columns = {s: list(base_qs.filter(status=s)) for s in statuses}

    # Calculate MTTR and SLA Compliance for resolved tickets
    resolved_tickets = base_qs.filter(status__in=['resolved', 'closed']).exclude(resolved_at__isnull=True)
    total_resolved_count = resolved_tickets.count()
    
    mttr_hours = 0
    sla_compliance_rate = 100
    
    if total_resolved_count > 0:
        total_time = sum((t.resolved_at - t.created_at).total_seconds() for t in resolved_tickets)
        mttr_hours = round((total_time / total_resolved_count) / 3600, 1)
        
        sla_met_count = sum(1 for t in resolved_tickets if t.sla_due_at and t.resolved_at <= t.sla_due_at)
        sla_compliance_rate = round((sla_met_count / total_resolved_count) * 100)

    context = {"""

if "mttr_hours = 0" not in content:
    content = content.replace(it_helpdesk_target, it_helpdesk_replace)

it_helpdesk_context_target = """        'total_resolved': base_qs.filter(status__in=['resolved', 'closed']).count(),
        'priority_choices': ITTicket.PRIORITY_CHOICES,"""

it_helpdesk_context_replace = """        'total_resolved': base_qs.filter(status__in=['resolved', 'closed']).count(),
        'mttr_hours': mttr_hours,
        'sla_compliance_rate': sla_compliance_rate,
        'priority_choices': ITTicket.PRIORITY_CHOICES,"""

if "'mttr_hours': mttr_hours" not in content:
    content = content.replace(it_helpdesk_context_target, it_helpdesk_context_replace)


# 2. Update threat_dashboard
threat_stats_target = """        'by_severity': list(ThreatIncident.objects.values('severity').annotate(n=Count('id')).order_by('-n')),
    }"""

threat_stats_replace = """        'by_severity': list(ThreatIncident.objects.values('severity').annotate(n=Count('id')).order_by('-n')),
        'avg_cvss': round(ThreatIncident.objects.exclude(status__in=['resolved', 'false_positive']).aggregate(Avg('cvss_score'))['cvss_score__avg'] or 0.0, 1),
        'top_ips': list(ThreatIncident.objects.exclude(source_ip__isnull=True).exclude(source_ip='').values('source_ip').annotate(n=Count('id')).order_by('-n')[:5]),
    }"""

if "'avg_cvss':" not in content:
    content = content.replace(threat_stats_target, threat_stats_replace)

# 3. Update auto-transition logic in it_ticket_update_status
auto_transition_target = """                if prev_assigned != new_assignee:
                    ticket.assigned_to = new_assignee
                    # Email the newly assigned person"""

auto_transition_replace = """                if prev_assigned != new_assignee:
                    ticket.assigned_to = new_assignee
                    if ticket.status == 'open':
                        ticket.status = 'in_progress'
                    # Email the newly assigned person"""

if "if ticket.status == 'open':" not in content:
    content = content.replace(auto_transition_target, auto_transition_replace)


with open('views.py', 'w') as f:
    f.write(content)

print("Updated views.py")
