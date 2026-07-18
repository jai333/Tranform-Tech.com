import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from tracking_app.models import SLAConfiguration

configs = [
    {'priority': 'p1', 'first_response_hours': 0.25, 'resolution_hours': 4.0, 'escalation_priority': None},
    {'priority': 'p2', 'first_response_hours': 1.0, 'resolution_hours': 24.0, 'escalation_priority': 'p1'},
    {'priority': 'p3', 'first_response_hours': 4.0, 'resolution_hours': 72.0, 'escalation_priority': 'p2'},
    {'priority': 'p4', 'first_response_hours': 24.0, 'resolution_hours': 120.0, 'escalation_priority': 'p3'},
]

for conf in configs:
    obj, created = SLAConfiguration.objects.update_or_create(
        priority=conf['priority'],
        defaults=conf
    )
    print(f"{'Created' if created else 'Updated'} SLA config for {conf['priority']}")
