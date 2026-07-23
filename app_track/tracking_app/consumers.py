"""
tracking_app/consumers.py
─────────────────────────────────────────────────────────────
Django Channels WebSocket consumers:
  - NotificationConsumer  : Real-time bell icon updates
  - SOCLiveFeedConsumer   : Live threat radar + SOC events
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Each authenticated user gets their own notification channel group.
    Group name: notifications_<user_id>
    Pushes: ticket updates, SLA breaches, AI alerts, mentions.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user_id = user.id
        self.group_name = f"notifications_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send unread count on connect
        unread = await self._get_unread_count(user)
        await self.send(text_data=json.dumps({
            "type": "init",
            "unread_count": unread,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle messages FROM the browser (e.g. mark-read)."""
        try:
            data = json.loads(text_data)
            action = data.get("action")
            if action == "mark_read":
                await self._mark_all_read(self.scope["user"])
                await self.send(text_data=json.dumps({"type": "unread_count", "count": 0}))
        except Exception as e:
            logger.error("NotificationConsumer receive error: %s", e)

    # ── Event handlers (called by channel_layer.group_send) ──────
    async def notification_message(self, event):
        """Relay a notification pushed from a signal/task."""
        await self.send(text_data=json.dumps({
            "type": "notification",
            "title": event.get("title", "New Notification"),
            "body": event.get("body", ""),
            "url": event.get("url", "#"),
            "icon": event.get("icon", "bx bx-bell"),
            "color": event.get("color", "#00E5FF"),
        }))

    async def unread_count(self, event):
        await self.send(text_data=json.dumps({
            "type": "unread_count",
            "count": event.get("count", 0),
        }))

    @database_sync_to_async
    def _get_unread_count(self, user):
        try:
            from .sales_models import SalesAlert
            from .models import ITTicket
            alerts = SalesAlert.objects.filter(is_read=False).count()
            tickets = ITTicket.objects.filter(
                assignee=user, status__in=["open", "in_progress"]
            ).count()
            return alerts + tickets
        except Exception:
            return 0

    @database_sync_to_async
    def _mark_all_read(self, user):
        try:
            from .sales_models import SalesAlert
            SalesAlert.objects.filter(is_read=False).update(is_read=True)
        except Exception:
            pass


class SOCLiveFeedConsumer(AsyncWebsocketConsumer):
    """
    Broadcasts live security events to all SOC dashboard viewers.
    Group name: soc_feed
    Pushes: new threat incidents, severity changes, radar blip data.
    """

    GROUP = "soc_feed"

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.GROUP, self.channel_name)
        await self.accept()

        # Send last 5 incidents on connect
        incidents = await self._get_recent_incidents()
        await self.send(text_data=json.dumps({
            "type": "init",
            "incidents": incidents,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP, self.channel_name)

    async def receive(self, text_data):
        pass  # SOC feed is read-only from browser

    # ── Event handler pushed from signals ────────────────────────
    async def soc_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "incident",
            "id": event.get("id"),
            "title": event.get("title"),
            "severity": event.get("severity"),
            "threat_type": event.get("threat_type"),
            "timestamp": event.get("timestamp"),
        }))

    @database_sync_to_async
    def _get_recent_incidents(self):
        try:
            from .models import ThreatIncident
            incidents = ThreatIncident.objects.order_by("-detected_at")[:5]
            return [
                {
                    "id": i.id,
                    "title": i.title,
                    "severity": i.severity,
                    "threat_type": i.threat_type,
                    "timestamp": i.detected_at.isoformat() if i.detected_at else "",
                }
                for i in incidents
            ]
        except Exception:
            return []
