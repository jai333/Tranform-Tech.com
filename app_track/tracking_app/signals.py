from django.db.models.signals import post_save
from django.dispatch import receiver
import json
from .models import Candidate, Job, ITTicket
from .webhooks import dispatch_webhook

@receiver(post_save, sender=Candidate)
def webhook_candidate_saved(sender, instance, created, **kwargs):
    if not hasattr(instance, 'tenant') or not instance.tenant:
        return
        
    event_type = "candidate.created" if created else "candidate.updated"
    payload = {
        "id": instance.id,
        "first_name": instance.first_name,
        "last_name": instance.last_name,
        "email": instance.email,
    }
    dispatch_webhook(instance.tenant, event_type, payload)

@receiver(post_save, sender=Job)
def webhook_job_saved(sender, instance, created, **kwargs):
    if not hasattr(instance, 'tenant') or not instance.tenant:
        return
        
    event_type = "job.created" if created else "job.updated"
    payload = {
        "id": instance.id,
        "title": instance.title,
        "department": instance.department,
        "location": instance.location,
        "status": instance.status,
    }
    dispatch_webhook(instance.tenant, event_type, payload)

@receiver(post_save, sender=ITTicket)
def webhook_ticket_saved(sender, instance, created, **kwargs):
    if not hasattr(instance, 'tenant') or not instance.tenant:
        return
        
    event_type = "ticket.created" if created else "ticket.updated"
    payload = {
        "id": instance.id,
        "title": instance.title,
        "priority": instance.priority,
        "status": instance.status,
    }
    dispatch_webhook(instance.tenant, event_type, payload)
