import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
# Get first user
user = User.objects.first()
if not user:
    print("No users found!")
    exit(1)

client = Client()
client.force_login(user)

for url in ['/it-helpdesk/', '/soc-dashboard/']:
    try:
        resp = client.get(url)
        print(f"{url} returned {resp.status_code}")
        if resp.status_code == 500:
            print("500 ERROR CONTENT:")
            print(resp.content.decode('utf-8')[:1000])
    except Exception as e:
        import traceback
        print(f"CRASH on {url}:")
        traceback.print_exc()

