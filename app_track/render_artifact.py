import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

request = RequestFactory().get('/sales/leads/google-maps/')
request.user = AnonymousUser()

# Render gmaps_scraper.html
try:
    html = render_to_string('tracking_app/sales/gmaps_scraper.html', request=request)
    with open('preview_generated_gmaps.html', 'w') as f:
        f.write(html)
    print("Successfully rendered preview_generated_gmaps.html")
except Exception as e:
    print(f"Error rendering gmaps_scraper.html: {e}")

# Render dashboard to show base.html
try:
    html2 = render_to_string('tracking_app/sales/dashboard.html', request=request)
    with open('preview_generated_sales_dashboard.html', 'w') as f:
        f.write(html2)
    print("Successfully rendered preview_generated_sales_dashboard.html")
except Exception as e:
    print(f"Error rendering dashboard: {e}")
