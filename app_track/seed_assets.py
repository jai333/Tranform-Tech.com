import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from tracking_app.models import ITAsset
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()

assets = [
    {
        'asset_tag': 'ASSET-001',
        'name': 'MacBook Pro M3 Max (14-inch)',
        'asset_type': 'laptop',
        'status': 'active',
        'owner': admin,
        'purchase_date': date(2023, 10, 15)
    },
    {
        'asset_tag': 'ASSET-002',
        'name': 'ThinkPad X1 Carbon Gen 11',
        'asset_type': 'laptop',
        'status': 'active',
        'owner': admin,
        'purchase_date': date(2024, 1, 10)
    },
    {
        'asset_tag': 'SRV-DB-01',
        'name': 'Primary Database Server (Ubuntu 22.04)',
        'asset_type': 'server',
        'status': 'active',
        'owner': None,
        'purchase_date': date(2021, 5, 20)
    },
    {
        'asset_tag': 'NET-SW-01',
        'name': 'Cisco Catalyst 9300 Switch',
        'asset_type': 'network',
        'status': 'active',
        'owner': None,
        'purchase_date': date(2022, 11, 5)
    },
    {
        'asset_tag': 'LIC-O365-01',
        'name': 'Office 365 E5 Enterprise License',
        'asset_type': 'license',
        'status': 'active',
        'owner': admin,
        'purchase_date': date(2023, 12, 1)
    }
]

for asset_data in assets:
    obj, created = ITAsset.objects.update_or_create(
        asset_tag=asset_data['asset_tag'],
        defaults=asset_data
    )
    print(f"{'Created' if created else 'Updated'} Asset {obj.asset_tag}")

print("Seeding complete.")
