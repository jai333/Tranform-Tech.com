import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from django.apps import apps
from django.db import models

with open('datadump.json', 'r') as f:
    data = json.load(f)

for obj in data:
    try:
        app_label, model_name = obj['model'].split('.')
        model = apps.get_model(app_label, model_name)
    except Exception:
        continue

    for field_name, value in obj.get('fields', {}).items():
        if isinstance(value, str):
            try:
                field = model._meta.get_field(field_name)
                if isinstance(field, models.CharField) and field.max_length:
                    if len(value) > field.max_length:
                        print(f"Truncating {model_name}.{field_name} (length {len(value)} > {field.max_length})")
                        obj['fields'][field_name] = value[:field.max_length]
            except Exception:
                pass

with open('datadump.json', 'w') as f:
    json.dump(data, f, indent=4)
print("Fixed datadump in place!")
