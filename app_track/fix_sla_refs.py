import re

# 1. tracking_app/models.py
with open('tracking_app/models.py', 'r') as f:
    content = f.read()

content = content.replace("self.sla_due_at and timezone.now() > self.sla_due_at", "self.resolve_due_at and timezone.now() > self.resolve_due_at")
content = content.replace("if not self.sla_due_at:", "if not self.resolve_due_at:")
content = content.replace("delta = self.sla_due_at - timezone.now()", "delta = self.resolve_due_at - timezone.now()")

with open('tracking_app/models.py', 'w') as f:
    f.write(content)

# 2. tracking_app/admin.py
with open('tracking_app/admin.py', 'r') as f:
    content = f.read()

content = content.replace("'sla_due_at'", "'resolve_due_at'")

with open('tracking_app/admin.py', 'w') as f:
    f.write(content)

# 3. tracking_app/views.py
with open('tracking_app/views.py', 'r') as f:
    content = f.read()

content = content.replace("t.sla_due_at and t.resolved_at <= t.sla_due_at", "t.resolve_due_at and t.resolved_at <= t.resolve_due_at")
content = content.replace("ticket.sla_due_at", "ticket.resolve_due_at")

with open('tracking_app/views.py', 'w') as f:
    f.write(content)

# 4. tracking_app/templates/tracking_app/it_ticket_detail.html
with open('tracking_app/templates/tracking_app/it_ticket_detail.html', 'r') as f:
    content = f.read()

content = content.replace("ticket.sla_due_at", "ticket.resolve_due_at")

with open('tracking_app/templates/tracking_app/it_ticket_detail.html', 'w') as f:
    f.write(content)

