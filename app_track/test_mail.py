import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from tracking_app.models import Tenant
from tracking_app.sales_models import Lead, OutreachEmail

tenant, _ = Tenant.objects.get_or_create(name='TestTenant', mail_registered_email='test@example.com')

print("Testing update_mail_config...")
try:
    tenant.mail_sender_name = 'Test Sender'
    tenant.mail_reply_to = 'reply@example.com'
    tenant.mail_smtp_host = 'smtp.test.com'
    tenant.mail_smtp_port = 587
    tenant.mail_smtp_username = 'user'
    tenant.mail_smtp_password = 'password'
    tenant.mail_use_tls = True
    tenant.mail_auto_sync = True
    tenant.mail_integration_status = 'connected'
    tenant.save()
    print("update_mail_config success!")
except Exception as e:
    print(f"update_mail_config error: {type(e).__name__} - {e}")

print("\nTesting test_send...")
try:
    from django.utils import timezone
    test_lead, _ = Lead.objects.get_or_create(
        email=tenant.mail_registered_email,
        defaults={'contact_name': f"Self Verification ({tenant.name})", 'company_name': tenant.name, 'tenant': tenant}
    )
    if not test_lead.tenant:
        test_lead.tenant = tenant
        test_lead.save()
    
    OutreachEmail.objects.create(
        lead=test_lead,
        tenant=tenant,
        sender_email=tenant.mail_registered_email,
        subject="✨ [Transform-Tech] Verification: Tenant Mail Integration Active!",
        body=f"Hello {tenant.name} Team...",
        status='sent',
        sent_at=timezone.now()
    )
    print("test_send success!")
except Exception as e:
    print(f"test_send error: {type(e).__name__} - {e}")
