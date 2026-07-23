import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
django.setup()

from django.test import RequestFactory
from tracking_app.models import User
from tracking_app.sales_views import sales_dashboard

factory = RequestFactory()
request = factory.get('/sales/dashboard/')
# create user
user = User.objects.first()
request.user = user

try:
    response = sales_dashboard(request)
    print("Success:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
