import re

# 1. Update base.html to add IT Admin Settings link
with open('tracking_app/templates/tracking_app/base.html', 'r') as f:
    content = f.read()

admin_link = """                    {% if user.is_it_admin %}
                    <li><a href="{% url 'it-admin-settings' %}" class="{% if '/it/admin/' in request.path %}active{% endif %}"><i class="fa-solid fa-gear"></i> IT Admin Settings</a></li>
                    {% endif %}"""

if "it-admin-settings" not in content:
    content = content.replace(
        "<li><a href=\"{% url 'service-addons' %}\"",
        admin_link + "\n                    <li><a href=\"{% url 'service-addons' %}\""
    )
    with open('tracking_app/templates/tracking_app/base.html', 'w') as f:
        f.write(content)

# 2. Update it_helpdesk.html
with open('tracking_app/templates/tracking_app/it_helpdesk.html', 'r') as f:
    content = f.read()

# Hide MTTR / SLA / Breached counter for End Users
if "{% if not user.is_it_enduser %}" not in content:
    content = content.replace(
        """<div class="summary-card">
            <div class="summary-label">MTTR</div>
            <div class="summary-value">{{ mttr_hours }}h</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">SLA Compliance</div>
            <div class="summary-value">{{ sla_compliance_rate }}%</div>
        </div>""",
        """{% if not user.is_it_enduser %}
        <div class="summary-card">
            <div class="summary-label">MTTR</div>
            <div class="summary-value">{{ mttr_hours }}h</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">SLA Compliance</div>
            <div class="summary-value">{{ sla_compliance_rate }}%</div>
        </div>
        {% endif %}"""
    )
    
    content = content.replace(
        """<button class="filter-btn" onclick="filterTickets('sla', this)"><i class="bx bx-time-five"></i> SLA Breached""",
        """{% if not user.is_it_enduser %}<button class="filter-btn" onclick="filterTickets('sla', this)"><i class="bx bx-time-five"></i> SLA Breached"""
    )
    content = content.replace(
        """</span></button>
        <button class="filter-btn" """,
        """</span></button>{% endif %}
        <button class="filter-btn" """
    )
    
    with open('tracking_app/templates/tracking_app/it_helpdesk.html', 'w') as f:
        f.write(content)

# 3. Update it_ticket_detail.html
with open('tracking_app/templates/tracking_app/it_ticket_detail.html', 'r') as f:
    content = f.read()

if "{% if not user.is_it_enduser %}" not in content:
    # Hide SLA Countdown
    content = content.replace(
        """<!-- SLA Countdown Bar -->
    {% if ticket.status not in 'resolved,closed,on_hold' %}""",
        """<!-- SLA Countdown Bar -->
    {% if not user.is_it_enduser and ticket.status not in 'resolved,closed,on_hold' %}"""
    )
    
    # Hide Internal Note Toggle (Wait, it's already guarded by {% if user.is_staff or user.is_admin_role %})
    # We will update that to {% if user.is_it_agent %}
    content = content.replace(
        """{% if user.is_staff or user.is_admin_role %}
                                <label class="internal-toggle">""",
        """{% if user.is_it_agent %}
                                <label class="internal-toggle">"""
    )
    
    # Hide Update Ticket Form for End Users
    content = content.replace(
        """<!-- Update Ticket Form -->
            {% if user.is_staff or user.is_admin_role or ticket.submitted_by == user %}""",
        """<!-- Update Ticket Form -->
            {% if user.is_it_agent %}"""
    )

    with open('tracking_app/templates/tracking_app/it_ticket_detail.html', 'w') as f:
        f.write(content)

print("Templates updated successfully.")
