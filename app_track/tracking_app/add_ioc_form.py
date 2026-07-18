with open('templates/tracking_app/threat_dashboard.html', 'r') as f:
    content = f.read()

target_form = """                    <select name="status" style="width:100%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:9px 12px;color:#fff;font-size:0.85rem;outline:none;font-family:inherit;margin-bottom:1rem">
                        {% for val, label in status_choices %}
                        <option value="{{ val }}" {% if incident.status == val %}selected{% endif %}>{{ label }}</option>
                        {% endfor %}
                    </select>"""

replace_form = """                    <select name="status" style="width:100%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:9px 12px;color:#fff;font-size:0.85rem;outline:none;font-family:inherit;margin-bottom:1rem">
                        {% for val, label in status_choices %}
                        <option value="{{ val }}" {% if incident.status == val %}selected{% endif %}>{{ label }}</option>
                        {% endfor %}
                    </select>
                    
                    <label style="display:block;font-size:0.72rem;color:rgba(255,255,255,0.4);margin-bottom:6px;text-transform:uppercase">CVSS Score (0-10)</label>
                    <input type="number" step="0.1" name="cvss_score" value="{{ incident.cvss_score|default:'' }}" style="width:100%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:9px 12px;color:#fff;font-size:0.85rem;outline:none;font-family:inherit;margin-bottom:1rem">
                    
                    <label style="display:block;font-size:0.72rem;color:rgba(255,255,255,0.4);margin-bottom:6px;text-transform:uppercase">Source IP</label>
                    <input type="text" name="source_ip" value="{{ incident.source_ip|default:'' }}" style="width:100%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:9px 12px;color:#fff;font-size:0.85rem;outline:none;font-family:inherit;margin-bottom:1rem">
                    
                    <label style="display:block;font-size:0.72rem;color:rgba(255,255,255,0.4);margin-bottom:6px;text-transform:uppercase">Malicious Domain</label>
                    <input type="text" name="malicious_domain" value="{{ incident.malicious_domain|default:'' }}" style="width:100%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:9px 12px;color:#fff;font-size:0.85rem;outline:none;font-family:inherit;margin-bottom:1rem">
                    
                    <label style="display:block;font-size:0.72rem;color:rgba(255,255,255,0.4);margin-bottom:6px;text-transform:uppercase">File Hash (MD5/SHA256)</label>
                    <input type="text" name="file_hash" value="{{ incident.file_hash|default:'' }}" style="width:100%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:9px 12px;color:#fff;font-size:0.85rem;outline:none;font-family:inherit;margin-bottom:1rem">"""

if 'name="cvss_score"' not in content:
    content = content.replace(target_form, replace_form)

with open('templates/tracking_app/threat_dashboard.html', 'w') as f:
    f.write(content)

# Now update details list in views.py
with open('views.py', 'r') as f:
    views_content = f.read()

target_details = """        ('Assigned To', incident.assigned_to.get_full_name() if incident.assigned_to else '—'),
        ('Time Active (hrs)', str(incident.time_to_contain_hours() or '—')),
    ]"""

replace_details = """        ('Assigned To', incident.assigned_to.get_full_name() if incident.assigned_to else '—'),
        ('Time Active (hrs)', str(incident.time_to_contain_hours() or '—')),
        ('CVSS Score', str(incident.cvss_score) if incident.cvss_score else '—'),
        ('Source IP', incident.source_ip or '—'),
        ('Malicious Domain', incident.malicious_domain or '—'),
        ('File Hash', incident.file_hash or '—'),
    ]"""

if "'CVSS Score'" not in views_content:
    views_content = views_content.replace(target_details, replace_details)

with open('views.py', 'w') as f:
    f.write(views_content)
