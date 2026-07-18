import os

home_path = '/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app/home.html'
base_path = '/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app/base_public.html'

with open(home_path, 'r') as f:
    lines = f.readlines()

head_nav = lines[:428] # Up to end of nav

# Find footer start
footer_idx = 0
for i, line in enumerate(lines):
    if "<!-- ═══════════════════════════════════════════════════════════" in line and "FOOTER" in lines[i+1]:
        footer_idx = i
        break

if footer_idx == 0:
    for i, line in enumerate(lines):
        if "<footer" in line:
            footer_idx = i
            break

footer_scripts = lines[footer_idx:]

with open(base_path, 'w') as f:
    f.writelines(head_nav)
    f.write("\n{% block content %}\n{% endblock %}\n\n")
    f.writelines(footer_scripts)

print(f"Created {base_path}")
