import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
django.setup()

from django.core.mail import send_mail
from django.conf import settings

try:
    send_mail(
        subject='Test SMTP',
        message='This is a test from the ATS CRM app.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['test@example.com'],
        fail_silently=False,
    )
    print("SMTP success!")
except Exception as e:
    print(f"SMTP error: {e}")
