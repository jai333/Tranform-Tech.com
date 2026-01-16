import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from tracking_app.models import Interview
from channels.db import database_sync_to_async

class WebRTCConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'video_{self.room_name}'

        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        interview, allowed = await self._get_interview_and_permission(user, self.room_name)

        if not allowed:
            await self.close(code=4001)
            return

        if interview is None:
            await self.close()
            return

        # Store user info for chat messages
        self.user_display_name = user.get_full_name() or user.username
        self.user_id = user.id

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive_json(self, content):
        message_type = content.get('type')
        
        if message_type == 'chat':
            # Handle chat messages
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': content.get('message', ''),
                    'sender_name': self.user_display_name,
                    'sender_id': self.user_id,
                    'timestamp': content.get('timestamp')
                }
            )
        else:
            # Handle WebRTC signaling messages
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signal_message',
                    'message': content,
                    'sender_channel_name': self.channel_name
                }
            )

    async def signal_message(self, event):
        # Do not send message back to sender (already has)
        if self.channel_name != event['sender_channel_name']:
            await self.send_json(event['message'])

    async def chat_message(self, event):
        # Send chat message to WebSocket
        await self.send_json({
            'type': 'chat',
            'message': event['message'],
            'sender_name': event['sender_name'],
            'sender_id': event['sender_id'],
            'timestamp': event['timestamp']
        })

    @database_sync_to_async
    def _get_interview_and_permission(self, user, room_name):
        try:
            interview = Interview.objects.select_related('candidate', 'application', 'user').get(meeting_url__icontains=room_name)
        except Interview.DoesNotExist:
            return None, False

        applicant_user = None
        if hasattr(interview, 'application') and interview.application_id:
            applicant_user = getattr(interview.application, 'applicant', None)

        candidate_email_match = (user.email and interview.candidate.email and user.email.lower() == interview.candidate.email.lower())

        allowed = (
            (interview.user_id and interview.user_id == user.id) or
            user.username == interview.interviewer or
            (applicant_user and user.id == applicant_user.id) or
            candidate_email_match or
            getattr(user, 'is_admin_role', False) or
            user.is_staff
        )

        return interview, allowed 