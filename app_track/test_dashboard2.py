import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
django.setup()

from django.test import Client
from tracking_app.models import User
import traceback

c = Client()
user = User.objects.first()
c.force_login(user)
try:
    response = c.get('/security/dashboard/')
    print("SUCCESS")
except Exception as e:
    import sys
    # enable template debug to get the exact line
    from django.conf import settings
    # Actually just print the full traceback with template info if available
    traceback.print_exc()
