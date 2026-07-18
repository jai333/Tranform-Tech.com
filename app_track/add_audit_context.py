import re

with open('tracking_app/views.py', 'r') as f:
    content = f.read()

# Add audit_logs to context in it_ticket_detail
old_context = """    context = {
        'ticket': ticket,
        'comments': comments,
        'page_title': f'Ticket: {ticket.title}',
    }
    return render(request, 'tracking_app/it_ticket_detail.html', context)"""
new_context = """    
    audit_logs = []
    if request.user.is_it_agent:
        audit_logs = ticket.audit_logs.all().order_by('-timestamp')

    context = {
        'ticket': ticket,
        'comments': comments,
        'audit_logs': audit_logs,
        'page_title': f'Ticket: {ticket.title}',
    }
    return render(request, 'tracking_app/it_ticket_detail.html', context)"""

if "audit_logs" not in old_context and "audit_logs =" not in content:
    content = content.replace(old_context, new_context)
    with open('tracking_app/views.py', 'w') as f:
        f.write(content)
    print("Added audit_logs to views context")
else:
    print("Already added.")
