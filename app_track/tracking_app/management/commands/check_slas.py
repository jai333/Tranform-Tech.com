from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from tracking_app.models import ITTicket, SLAConfiguration, ITTicketComment

class Command(BaseCommand):
    help = 'Checks open IT Tickets for SLA warnings and breaches, auto-escalates if necessary.'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # 1. Flag "At Risk" Tickets (80% threshold)
        open_tickets = ITTicket.objects.exclude(status__in=['resolved', 'closed']).exclude(sla_status='breached')
        
        at_risk_count = 0
        breached_count = 0
        
        for ticket in open_tickets:
            is_breached = False
            is_at_risk = False
            
            # Check First Response SLA
            if not ticket.first_responded_at and ticket.first_response_due_at:
                if now > ticket.first_response_due_at:
                    is_breached = True
                else:
                    duration = ticket.first_response_due_at - ticket.created_at
                    elapsed = now - ticket.created_at
                    if elapsed.total_seconds() > (duration.total_seconds() * 0.8):
                        is_at_risk = True

            # Check Resolution SLA
            if not is_breached and ticket.resolve_due_at:
                if now > ticket.resolve_due_at:
                    is_breached = True
                else:
                    duration = ticket.resolve_due_at - ticket.created_at
                    elapsed = now - ticket.created_at
                    if elapsed.total_seconds() > (duration.total_seconds() * 0.8):
                        is_at_risk = True

            # Process state changes
            if is_breached and ticket.sla_status != 'breached':
                self._escalate_ticket(ticket)
                breached_count += 1
            elif is_at_risk and ticket.sla_status == 'healthy':
                ticket.sla_status = 'at_risk'
                ticket.save(update_fields=['sla_status'])
                ITTicketComment.objects.create(
                    ticket=ticket,
                    author=ticket.submitted_by,
                    body="⚠️ **System Alert**: This ticket has reached 80% of its SLA window and is currently at risk of breaching.",
                    is_internal=True
                )
                at_risk_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully checked SLAs. {at_risk_count} marked at risk. {breached_count} escalated.'))

        # 2. Check for Unassigned Tickets older than 30 minutes
        unassigned_threshold = now - timedelta(minutes=30)
        unassigned_tickets = ITTicket.objects.filter(
            assigned_to__isnull=True,
            status='open',
            created_at__lt=unassigned_threshold
        )
        
        unassigned_warn_count = 0
        for ticket in unassigned_tickets:
            # Check if we already warned
            has_warning = ticket.comments.filter(body__contains="System Alert: This ticket has been unassigned").exists()
            if not has_warning:
                ITTicketComment.objects.create(
                    ticket=ticket,
                    author=ticket.submitted_by,
                    body="⚠️ **System Alert**: This ticket has been unassigned for more than 30 minutes. Please assign an agent immediately.",
                    is_internal=True
                )
                unassigned_warn_count += 1
                
        if unassigned_warn_count > 0:
            self.stdout.write(self.style.WARNING(f'Warned on {unassigned_warn_count} unassigned tickets.'))

    def _escalate_ticket(self, ticket):
        ticket.sla_status = 'breached'
        
        try:
            config = SLAConfiguration.objects.get(priority=ticket.priority)
            old_priority = ticket.get_priority_display()
            if config.escalation_priority:
                ticket._original_priority = ticket.priority
                ticket.priority = config.escalation_priority
                
            ticket.save()
            
            msg = f"🚨 **SLA BREACH DETECTED** 🚨\n\nThis ticket has breached its SLA threshold. It has been automatically escalated from {old_priority} to {ticket.get_priority_display()}."
            ITTicketComment.objects.create(
                ticket=ticket,
                author=ticket.submitted_by,
                body=msg,
                is_internal=True
            )
        except SLAConfiguration.DoesNotExist:
            ticket.save(update_fields=['sla_status'])
