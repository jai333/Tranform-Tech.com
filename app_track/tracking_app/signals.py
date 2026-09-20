
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .sales_models import Lead, Deal
from .models import ITTicket, Candidate
from .event_bus import dispatch_event

def serialize_instance(instance):
    try:
        data = model_to_dict(instance)
        # Convert non-serializable fields if needed (like datetime)
        return data
    except Exception:
        return {'id': instance.id}

@receiver(post_save, sender=Lead)
def lead_post_save(sender, instance, created, **kwargs):
    event_type = 'lead.created' if created else 'lead.updated'
    if hasattr(instance, 'tenant'):
        dispatch_event(instance.tenant, event_type, serialize_instance(instance))

@receiver(post_save, sender=Deal)
def deal_post_save(sender, instance, created, **kwargs):
    event_type = 'deal.created' if created else 'deal.updated'
    if hasattr(instance, 'tenant'):
        dispatch_event(instance.tenant, event_type, serialize_instance(instance))

@receiver(post_save, sender=ITTicket)
def ticket_post_save(sender, instance, created, **kwargs):
    event_type = 'ticket.created' if created else 'ticket.updated'
    if hasattr(instance, 'tenant'):
        dispatch_event(instance.tenant, event_type, serialize_instance(instance))

@receiver(post_save, sender=Candidate)
def candidate_post_save(sender, instance, created, **kwargs):
    event_type = 'candidate.created' if created else 'candidate.updated'
    if hasattr(instance, 'tenant'):
        dispatch_event(instance.tenant, event_type, serialize_instance(instance))

from allauth.account.signals import user_signed_up
from .models import Tenant

@receiver(user_signed_up)
def populate_profile(request, user, **kwargs):
    user.can_view_ats = True
    user.can_view_sales = True
    user.can_view_it = True
    user.can_view_executive = True
    user.role = 'admin'
    tenant_name = f"{user.username or user.email}'s Workspace"
    tenant = Tenant.objects.create(name=tenant_name, subscription_plan='free')
    user.tenant = tenant
    user.save()

