import os

signals_to_add = """
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from threading import local

_thread_locals = local()

def set_current_user(user):
    _thread_locals.user = user

def get_current_user():
    return getattr(_thread_locals, 'user', None)

@receiver(pre_save, sender=ITTicket)
def it_ticket_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = ITTicket.objects.get(pk=instance.pk)
            instance._old_instance = old_instance
        except ITTicket.DoesNotExist:
            instance._old_instance = None
    else:
        instance._old_instance = None

    # Automated Routing (Phase 4)
    if not instance.pk and not instance.assigned_to:
        # It's a new ticket without an assignee, try to route
        try:
            rule = RoutingRule.objects.get(category=instance.category)
            if rule.assign_to:
                instance.assigned_to = rule.assign_to
        except RoutingRule.DoesNotExist:
            pass

@receiver(post_save, sender=ITTicket)
def it_ticket_post_save(sender, instance, created, **kwargs):
    actor = get_current_user() or instance.submitted_by

    # Audit Trail (Phase 6)
    if created:
        TicketAuditLog.objects.create(
            ticket=instance,
            actor=actor,
            field_changed='Created',
            old_value=None,
            new_value='Ticket Opened'
        )
    else:
        old_instance = getattr(instance, '_old_instance', None)
        if old_instance:
            fields_to_track = ['status', 'priority', 'category', 'assigned_to']
            for field in fields_to_track:
                old_val = getattr(old_instance, field)
                new_val = getattr(instance, field)
                if old_val != new_val:
                    # Convert objects to string if needed
                    if field == 'assigned_to':
                        old_val = old_val.username if old_val else 'Unassigned'
                        new_val = new_val.username if new_val else 'Unassigned'
                    
                    TicketAuditLog.objects.create(
                        ticket=instance,
                        actor=actor,
                        field_changed=field,
                        old_value=str(old_val),
                        new_value=str(new_val)
                    )
"""

with open('tracking_app/models.py', 'r') as f:
    content = f.read()

if "def it_ticket_pre_save" not in content:
    with open('tracking_app/models.py', 'a') as f:
        f.write(signals_to_add)
    print("Added signals to models.py")
