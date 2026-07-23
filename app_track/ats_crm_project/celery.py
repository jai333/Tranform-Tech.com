"""
ats_crm_project/celery.py
─────────────────────────────────────────────────────────────
Celery application entrypoint for Transform.io.
Broker: Redis (localhost:6379/0)
Result backend: django-celery-results (stores in DB)
Beat scheduler: django-celery-beat (schedule stored in DB, editable via admin)
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")

app = Celery("ats_crm_project")

# Read config from Django settings with CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all INSTALLED_APPS
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
