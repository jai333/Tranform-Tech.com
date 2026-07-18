import os

home_path = '/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app/home.html'

with open(home_path, 'r') as f:
    lines = f.readlines()

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

new_lines = ["{% extends 'tracking_app/base_public.html' %}\n", "{% block content %}\n"]
# from after nav to before footer
new_lines.extend(lines[428:footer_idx])
new_lines.append("{% endblock %}\n")

with open(home_path, 'w') as f:
    f.writelines(new_lines)

print("Refactored home.html")
