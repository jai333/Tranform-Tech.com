import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
django.setup()

from django.test import Client
from tracking_app.models import User
from django.template import Template, Context

user = User.objects.first()
t = Template("{% if incident %}{{ incident.reported_by.get_full_name|default:incident.reported_by.username }}{% endif %}")
try:
    print(t.render(Context({'incident': None})))
except Exception as e:
    print("FAILED on incident.reported_by.username:", type(e))

t2 = Template("{{ inc.assigned_to.get_full_name|default:inc.assigned_to.username }}")
try:
    print(t2.render(Context({'inc': {'assigned_to': None}})))
except Exception as e:
    print("FAILED on inc.assigned_to.username:", type(e))
