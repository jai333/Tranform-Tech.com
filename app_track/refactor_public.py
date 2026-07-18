import os
import re

files_to_refactor = [
    'public_ats.html',
    'public_crm.html',
    'public_ai.html',
    'public_workflow.html',
    'public_telemetry.html',
    'public_blog.html',
    'industry_tech.html',
    'industry_health.html',
    'industry_exec.html',
    'role_agency.html',
    'role_internal.html',
    'role_manager.html'
]

base_dir = '/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app'

for filename in files_to_refactor:
    filepath = os.path.join(base_dir, filename)
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r') as f:
        content = f.read()

    # Extract <style>...</style> block
    style_match = re.search(r'(<style>.*?</style>)', content, re.DOTALL)
    style_block = style_match.group(1) if style_match else ''

    # Find the start of the main content
    header_match = re.search(r'<header class="container[^>]*>', content)
    if not header_match:
        print(f"Skipping {filename}, no header container found.")
        continue
    start_idx = header_match.start()

    # Find the footer
    footer_match = re.search(r'<footer[^>]*>', content)
    if not footer_match:
        print(f"Skipping {filename}, no footer found.")
        continue
    end_idx = footer_match.start()

    main_content = content[start_idx:end_idx]

    # Replace images based on filename
    if filename == 'public_ats.html':
        main_content = main_content.replace('ats_dashboard.png', 'full_application_showcase_1780489286010.png')
    elif filename == 'public_crm.html':
        main_content = main_content.replace('crm_dashboard.png', 'sales_dashboard_preview_1783116803313.png')
    elif filename == 'public_workflow.html':
        main_content = main_content.replace('analytics_dashboard.png', 'automation_mockup_1776112570610.png')
    elif filename == 'public_telemetry.html':
        main_content = main_content.replace('analytics_dashboard.png', 'dashboard_mockup_1776111945145.png')
    elif filename == 'public_ai.html':
        # Add the ai pipeline image since it has none
        ai_img_html = '<div class="bento-image-wrapper border-glow" style="margin-top:40px;"><img src="{% static \'tracking_app/assets/ai_pipeline_preview_1779365868569.png\' %}" alt="AI Pipeline" style="width:100%; border-radius:12px;"></div>'
        main_content = main_content.replace('</section>', f'{ai_img_html}\n    </section>')
    else:
        # For industry/roles
        main_content = main_content.replace('analytics_dashboard.png', 'full_application_showcase_1780489286010.png')

    new_content = "{% extends 'tracking_app/base_public.html' %}\n{% load static %}\n{% block content %}\n"
    if style_block:
        new_content += style_block + "\n"
    
    new_content += main_content + "{% endblock %}\n"

    with open(filepath, 'w') as f:
        f.write(new_content)

    print(f"Refactored {filename}")
