import json
import hmac
import hashlib
import requests
import threading
from django.utils import timezone
from .models import WebhookEndpoint, WebhookLog
import logging

logger = logging.getLogger(__name__)

def _send_webhook_sync(endpoint_id, event_type, payload):
    """
    Synchronous worker to dispatch the webhook. 
    In full production, this would be a Celery task.
    """
    try:
        endpoint = WebhookEndpoint.objects.get(pk=endpoint_id)
        if not endpoint.is_active:
            return

        # Check if event matches
        if endpoint.events != "*":
            allowed_events = [e.strip() for e in endpoint.events.split(",")]
            if event_type not in allowed_events:
                return

        # Prepare payload
        payload_json = json.dumps(payload)
        
        # Create HMAC signature
        signature = hmac.new(
            endpoint.secret_key.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            'Content-Type': 'application/json',
            'X-Transform-Signature': f'sha256={signature}',
            'X-Transform-Event': event_type,
        }

        # Dispatch request
        response = requests.post(endpoint.target_url, data=payload_json, headers=headers, timeout=10)
        
        # Log it
        WebhookLog.objects.create(
            endpoint=endpoint,
            event_type=event_type,
            payload=payload,
            status_code=response.status_code,
            response_body=response.text[:1000]  # truncate huge responses
        )
        
    except Exception as e:
        logger.error(f"Failed to send webhook to {endpoint_id}: {str(e)}")
        # Log failure
        try:
            WebhookLog.objects.create(
                endpoint_id=endpoint_id,
                event_type=event_type,
                payload=payload,
                status_code=None,
                response_body=str(e)[:1000]
            )
        except:
            pass

def dispatch_webhook(tenant, event_type, payload):
    """
    Asynchronously dispatches a webhook to all subscribed endpoints for a tenant.
    Usage:
        dispatch_webhook(user.tenant, "candidate.created", {"id": candidate.id, "name": candidate.name})
    """
    if not tenant:
        return
        
    endpoints = WebhookEndpoint.objects.filter(tenant=tenant, is_active=True)
    
    for endpoint in endpoints:
        # Fire and forget thread (simulate Celery for now to keep dependencies light, but easily upgradeable)
        thread = threading.Thread(target=_send_webhook_sync, args=(endpoint.id, event_type, payload))
        thread.start()
