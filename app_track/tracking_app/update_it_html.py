with open('templates/tracking_app/it_helpdesk.html', 'r') as f:
    content = f.read()

target = """        <div class="it-stats">
            <div class="stat-pill"><i class="bx bx-loader-circle" style="color:#f59e0b"></i> Active: <strong>{{ total_open }}</strong></div>
            <div class="stat-pill"><i class="bx bx-check-circle" style="color:#10b981"></i> Resolved: <strong>{{ total_resolved }}</strong></div>
            <div class="stat-pill" id="live-clock"><i class="bx bx-time" style="color:#00E5FF"></i> <strong id="clock-val">--:--:--</strong></div>
        </div>"""

replace = """        <div class="it-stats">
            <div class="stat-pill"><i class="bx bx-loader-circle" style="color:#f59e0b"></i> Active: <strong>{{ total_open }}</strong></div>
            <div class="stat-pill"><i class="bx bx-check-circle" style="color:#10b981"></i> Resolved: <strong>{{ total_resolved }}</strong></div>
            <div class="stat-pill"><i class="bx bx-timer" style="color:#6366f1"></i> MTTR: <strong>{{ mttr_hours }}h</strong></div>
            <div class="stat-pill"><i class="bx bx-shield-check" style="color:#00E5FF"></i> SLA Met: <strong>{{ sla_compliance_rate }}%</strong></div>
            <div class="stat-pill" id="live-clock"><i class="bx bx-time" style="color:var(--apple-text-secondary)"></i> <strong id="clock-val">--:--:--</strong></div>
        </div>"""

if "MTTR" not in content:
    content = content.replace(target, replace)
    with open('templates/tracking_app/it_helpdesk.html', 'w') as f:
        f.write(content)
    print("Updated it_helpdesk.html")
