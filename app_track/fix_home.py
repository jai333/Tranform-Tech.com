import re

# --- Fix base_public.html ---
with open('tracking_app/templates/tracking_app/base_public.html', 'r') as f:
    content = f.read()

# Change yellow color to cyan
content = content.replace("icon.style.color = '#f59e0b';", "icon.style.color = '#00E5FF';")

# Add preventDefault to theme toggle
content = content.replace("toggle.addEventListener('click', () => {", "toggle.addEventListener('click', (e) => {\n            e.preventDefault();")

with open('tracking_app/templates/tracking_app/base_public.html', 'w') as f:
    f.write(content)

# --- Fix home.html ---
with open('tracking_app/templates/tracking_app/home.html', 'r') as f:
    content = f.read()

# Replace IT Helpdesk image
content = content.replace(
    "src=\"{% static 'tracking_app/assets/dashboard_mockup_1776111945145.png' %}\"", 
    "src=\"{% static 'tracking_app/assets/it_helpdesk_realistic.jpg' %}\""
)

# Fix Security Section Color (Red to Indigo)
# 1. Label tag
content = content.replace(
    '<div class="label-tag label-red" style="color: #ef4444; border-color: rgba(239,68,68,0.25); background: rgba(239,68,68,0.06);">CYBERSECURITY</div>',
    '<div class="label-tag label-indigo" style="color: #6366f1; border-color: rgba(99,102,241,0.25); background: rgba(99,102,241,0.06);">CYBERSECURITY</div>'
)

# 2. Checkmarks
content = content.replace('class="sc-check sc-red"', 'class="sc-check sc-indigo"')

# 3. Add .sc-indigo to style if missing (or replace sc-red css)
if '.sc-red {' in content:
    content = content.replace('.sc-red { background: rgba(239,68,68,0.1); color: #ef4444; }', '.sc-red { background: rgba(239,68,68,0.1); color: #ef4444; }\n.sc-indigo { background: rgba(99,102,241,0.1); color: #818cf8; }')

# 4. Update showcase button from red to indigo
content = content.replace('btn-showcase-red', 'btn-showcase-indigo')

# 5. Add btn-showcase-indigo css
if '.btn-showcase-indigo' not in content:
    css_to_add = """
.btn-showcase-indigo { background: linear-gradient(135deg, #6366f1, #4f46e5) !important; box-shadow: 0 4px 20px rgba(99,102,241,0.3) !important; }
.btn-showcase-indigo:hover { box-shadow: 0 8px 32px rgba(99,102,241,0.5) !important; }
"""
    content = content.replace('.btn-showcase-red:hover { box-shadow: 0 8px 32px rgba(239,68,68,0.5) !important; }', 
                              '.btn-showcase-red:hover { box-shadow: 0 8px 32px rgba(239,68,68,0.5) !important; }' + css_to_add)

with open('tracking_app/templates/tracking_app/home.html', 'w') as f:
    f.write(content)
