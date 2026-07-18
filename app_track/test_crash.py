import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
import django
django.setup()

from tracking_app.models import User
from django.test import Client

client = Client()
user = User.objects.first()
client.force_login(user)

print("Testing POST to /it/tickets/new/ ...")
response = client.post('/it/tickets/new/', {
    'title': 'Test Crash Ticket',
    'description': 'Description',
    'priority': 'p3',
    'category': 'hardware'
})
print("POST status code:", response.status_code)
if response.status_code == 302:
    print("Redirected to:", response.url)
    print("Following redirect...")
    resp2 = client.get(response.url)
    print("Detail GET status code:", resp2.status_code)
    if resp2.status_code == 500:
        print("ERROR on GET detail:")
        print(resp2.content.decode()[:1000])
elif response.status_code == 500:
    print("ERROR on POST create:")
    print(response.content.decode()[:1000])
