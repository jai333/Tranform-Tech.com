from django.urls import path, re_path
from . import consumers

# Using `path` simplifies matching and avoids leading-slash confusion.
websocket_urlpatterns = [
    path('ws/video/<slug:room_name>/', consumers.WebRTCConsumer.as_asgi()),
] 