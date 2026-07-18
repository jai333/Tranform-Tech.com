import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
import django
django.setup()

from tracking_app.models import User
from django.test import Client

client = Client()
user = User.objects.filter(is_staff=True).first()
if user:
    client.force_login(user)

print("Testing GET to /api/search/?q=a ...")
response = client.get('/api/search/?q=a')
print("Status code:", response.status_code)
if response.status_code == 200:
    print(response.content.decode()[:1000])
else:
    print("ERROR:", response.content.decode()[:1000])
