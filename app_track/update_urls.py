import re

with open('tracking_app/urls.py', 'r') as f:
    content = f.read()

if "it/assets/" not in content:
    content = content.replace(
        "path('it/tickets/<int:pk>/', views.it_ticket_detail, name='it-ticket-detail'),",
        "path('it/tickets/<int:pk>/', views.it_ticket_detail, name='it-ticket-detail'),\n    path('it/assets/<int:pk>/', views.it_asset_detail, name='it-asset-detail'),"
    )
    with open('tracking_app/urls.py', 'w') as f:
        f.write(content)
    print("Added it_asset_detail to urls")
