import re

with open('tracking_app/views.py', 'r') as f:
    content = f.read()

old_context = """    context = {
        'columns': columns,
        'total_open': base_qs.filter(status__in=['open', 'in_progress', 'on_hold', 'pending_user']).count(),
        'total_resolved': base_qs.filter(status__in=['resolved', 'closed']).count(),
        'mttr_hours': mttr_hours,
        'sla_compliance_rate': sla_compliance_rate,
        'priority_choices': ITTicket.PRIORITY_CHOICES,
        'category_choices': ITTicket.CATEGORY_CHOICES,
        'page_title': 'IT Helpdesk',
    }"""

new_context = """    context = {
        'columns': columns,
        'total_open': base_qs.filter(status__in=['open', 'in_progress', 'on_hold', 'pending_user']).count(),
        'total_resolved': base_qs.filter(status__in=['resolved', 'closed']).count(),
        'breached_count': base_qs.filter(sla_status='breached').count(),
        'mttr_hours': mttr_hours,
        'sla_compliance_rate': sla_compliance_rate,
        'priority_choices': ITTicket.PRIORITY_CHOICES,
        'category_choices': ITTicket.CATEGORY_CHOICES,
        'page_title': 'IT Helpdesk',
    }"""

if old_context in content:
    content = content.replace(old_context, new_context)
    with open('tracking_app/views.py', 'w') as f:
        f.write(content)
        print("Updated it_helpdesk_list context")
else:
    print("Could not find old_context")
