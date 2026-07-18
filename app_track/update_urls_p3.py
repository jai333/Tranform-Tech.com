import re

with open('tracking_app/urls.py', 'r') as f:
    content = f.read()

if "it/admin/settings/" not in content:
    content = content.replace(
        "path('it/assets/<int:pk>/', views.it_asset_detail, name='it-asset-detail'),",
        "path('it/assets/<int:pk>/', views.it_asset_detail, name='it-asset-detail'),\n    path('it/admin/settings/', views.it_admin_settings, name='it-admin-settings'),"
    )
    with open('tracking_app/urls.py', 'w') as f:
        f.write(content)
    print("Added it_admin_settings to urls")
