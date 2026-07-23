"""
ASGI config for ats_crm_project.
Handles: HTTP, WebSocket (video + notifications + SOC)
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')

import video.routing
import tracking_app.routing

# Combine all WebSocket URL patterns
all_websocket_patterns = (
    video.routing.websocket_urlpatterns
    + tracking_app.routing.websocket_urlpatterns
)

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(all_websocket_patterns)
    ),
})
