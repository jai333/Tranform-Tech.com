"""
tracking_app/routing.py
WebSocket URL patterns for the tracking_app.
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/notifications/", consumers.NotificationConsumer.as_asgi()),
    path("ws/soc/", consumers.SOCLiveFeedConsumer.as_asgi()),
]
