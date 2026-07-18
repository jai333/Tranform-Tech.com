import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
django.setup()

from django.test import Client
from tracking_app.models import User

c = Client()
user = User.objects.first()
c.force_login(user)
response = c.get('/security/dashboard/')
print("STATUS CODE:", response.status_code)
if response.status_code == 500:
    print("ERROR RENDERING DASHBOARD")
