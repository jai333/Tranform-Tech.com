import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from django.test import Client
from tracking_app.models import User, Tenant
from tracking_app.billing_views import _get_stripe

stripe = _get_stripe()
print("Stripe configured:", stripe is not None)
if stripe:
    print("API Key:", stripe.api_key)

user = User.objects.first()
if not user:
    print("No user found")
else:
    c = Client()
    c.force_login(user)
    response = c.post('/billing/checkout/', {'plan': 'growth'})
    print(f"Status code: {response.status_code}")
    print(f"Content: {response.content}")
    print(f"Redirect URL: {response.url if response.status_code == 302 else 'N/A'}")
