from django.urls import path
from . import views

app_name = 'video'

urlpatterns = [
    path('video-call/<uuid:room_uuid>/', views.video_call_room, name='video_call'),
] 