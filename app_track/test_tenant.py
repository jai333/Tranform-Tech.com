import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
django.setup()

from tracking_app.models import User, Tenant
from tracking_app.views import get_tenant_filter

# Find a tenant
tenant = Tenant.objects.first()
if tenant:
    # Create or get a user
    user, _ = User.objects.get_or_create(username='tenant_user', email='tenant@example.com')
    user.tenant = tenant
    user.save()
    
    # Test the filter
    filters = get_tenant_filter(user)
    print(f"Filters for tenant user: {filters}")
    
    # Test an admin user
    admin_user = User.objects.filter(is_superuser=True).first()
    if admin_user:
        filters = get_tenant_filter(admin_user)
        print(f"Filters for admin user: {filters}")
else:
    print("No tenant found.")
