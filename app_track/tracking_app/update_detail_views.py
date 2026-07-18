import re

with open('views.py', 'r') as f:
    content = f.read()

# Update threat_incident_detail to save IoC fields
target_post = """        if new_status:
            incident.status = new_status"""

replace_post = """        source_ip = request.POST.get('source_ip', '')
        malicious_domain = request.POST.get('malicious_domain', '')
        file_hash = request.POST.get('file_hash', '')
        if source_ip: incident.source_ip = source_ip
        if malicious_domain: incident.malicious_domain = malicious_domain
        if file_hash: incident.file_hash = file_hash
        if new_status:
            incident.status = new_status"""

if "source_ip = request.POST.get('source_ip" not in content:
    content = content.replace(target_post, replace_post)

with open('views.py', 'w') as f:
    f.write(content)
