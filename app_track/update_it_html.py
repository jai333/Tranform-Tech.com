with open('tracking_app/templates/tracking_app/it_helpdesk.html', 'r') as f:
    content = f.read()

# 1. Update SLA Breached Button
old_btn = '<button class="filter-btn" onclick="filterTickets(\'sla\', this)"><i class="bx bx-time-five"></i> SLA Breached</button>'
new_btn = '<button class="filter-btn" onclick="filterTickets(\'sla\', this)"><i class="bx bx-time-five"></i> SLA Breached <span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239,68,68,0.5); border-radius: 10px; padding: 2px 6px; font-size: 0.75rem; margin-left: 4px;">{{ breached_count }}</span></button>'
content = content.replace(old_btn, new_btn)

# 2. Update data-sla attribute
content = content.replace(
    'data-sla="{% if ticket.is_sla_breached %}1{% else %}0{% endif %}"',
    'data-sla="{% if ticket.sla_status == \'breached\' %}1{% else %}0{% endif %}"'
)

# 3. Update the ticket meta spans for SLA
# In Open column:
old_open_span = """{% if ticket.is_sla_breached %}<span class="sla-breach"><i class="bx bx-time-five bx-tada"></i> SLA Breached</span>
                    {% else %}<span style="color:#10b981; font-size:0.65rem;"><i class="bx bx-check-shield"></i> SLA OK</span>{% endif %}"""

new_span = """{% if ticket.sla_status == 'breached' %}<span class="sla-breach"><i class="bx bx-time-five bx-tada"></i> SLA Breached</span>
                    {% elif ticket.sla_status == 'at_risk' %}<span class="sla-warning" style="color: #f59e0b; font-size: 0.65rem; font-weight: 600; text-transform: uppercase; background: rgba(245,158,11,0.1); padding: 2px 6px; border-radius: 4px;"><i class="bx bx-error"></i> At Risk</span>
                    {% else %}<span style="color:#10b981; font-size:0.65rem;"><i class="bx bx-check-shield"></i> SLA OK</span>{% endif %}"""

content = content.replace(old_open_span, new_span)

# In other columns where it just had {% if ticket.is_sla_breached %}<span class="sla-breach">...</span>{% endif %}
old_other_span = "{% if ticket.is_sla_breached %}<span class=\"sla-breach\"><i class=\"bx bx-time-five bx-tada\"></i> SLA Breached</span>{% endif %}"
content = content.replace(old_other_span, new_span)

with open('tracking_app/templates/tracking_app/it_helpdesk.html', 'w') as f:
    f.write(content)
