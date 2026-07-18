import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

client = Client()
client.force_login(user)

for url in ['/it/tickets/new/', '/security/incident/new/']:
    try:
        resp = client.post(url, {
            'title': 'Test',
            'description': 'Test',
            'priority': 'p3',
            'category': 'other',
            'severity': 'low'
        })
        print(f"POST {url} returned {resp.status_code}")
        if resp.status_code == 500:
            print("500 ERROR found on", url)
            print(resp.content.decode('utf-8')[:2000])
    except Exception as e:
        import traceback
        print(f"CRASH on {url}:")
        traceback.print_exc()

