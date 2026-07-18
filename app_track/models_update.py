import re

with open('tracking_app/models.py', 'r') as f:
    content = f.read()

# Add SLAConfiguration model
sla_model_code = """
class SLAConfiguration(models.Model):
    priority = models.CharField(max_length=10, unique=True, choices=ITTicket.PRIORITY_CHOICES)
    first_response_hours = models.FloatField(help_text="Hours until first response is required")
    resolution_hours = models.FloatField(help_text="Hours until full resolution is required")
    escalation_priority = models.CharField(max_length=10, null=True, blank=True, choices=ITTicket.PRIORITY_CHOICES, help_text="Priority to bump to if breached")
    
    def __str__(self):
        return f"SLA config for {self.get_priority_display()}"
"""

# Insert before ITTicketComment
content = content.replace("class ITTicketComment(models.Model):", sla_model_code + "\n\nclass ITTicketComment(models.Model):")

# Update ITTicket model fields
fields_to_add = """
    sla_status = models.CharField(max_length=20, default='healthy', choices=[
        ('healthy', 'Healthy'),
        ('at_risk', 'At Risk'),
        ('breached', 'Breached')
    ])
    first_response_due_at = models.DateTimeField(null=True, blank=True)
    first_responded_at = models.DateTimeField(null=True, blank=True)
    resolve_due_at = models.DateTimeField(null=True, blank=True)
"""

# We'll replace the old sla_due_at field with the new fields
content = content.replace("    sla_due_at = models.DateTimeField(null=True, blank=True)", fields_to_add)

# Update ITTicket.save method
new_save_method = """
    def save(self, *args, **kwargs):
        from django.utils import timezone
        from datetime import timedelta
        
        is_new = self.pk is None
        
        # Determine SLA times if new or priority changed
        if is_new or (self.pk and hasattr(self, '_original_priority') and self._original_priority != self.priority):
            try:
                sla_config = SLAConfiguration.objects.get(priority=self.priority)
                
                # If creating or priority upgraded, recalculate SLAs
                now = timezone.now()
                if not self.first_response_due_at or not self.first_responded_at:
                    self.first_response_due_at = now + timedelta(hours=sla_config.first_response_hours)
                
                self.resolve_due_at = now + timedelta(hours=sla_config.resolution_hours)
                
                # Reset SLA status if it was breached but priority upgraded
                if self.sla_status == 'breached':
                    self.sla_status = 'healthy'
                    
            except SLAConfiguration.DoesNotExist:
                # Fallback if configs aren't seeded yet
                sla_hours_map = {'p1': 4, 'p2': 24, 'p3': 72, 'p4': 120}
                hours = sla_hours_map.get(self.priority, 24)
                self.resolve_due_at = timezone.now() + timedelta(hours=hours)

        # First response tracking
        if self.pk and not self.first_responded_at and self.status != 'open':
            self.first_responded_at = timezone.now()

        # Auto-stamp resolved_at
        if self.status in ['resolved', 'closed'] and not self.resolved_at:
            self.resolved_at = timezone.now()
        # Clear resolved_at if reopened
        if self.status in ['open', 'in_progress'] and self.resolved_at:
            self.resolved_at = None
        # Pause SLA clock when put on hold
        if self.status == 'on_hold' and not self.sla_paused_at:
            self.sla_paused_at = timezone.now()

        super().save(*args, **kwargs)
"""

# Replace the save method
# We need to find the def save(self, *args, **kwargs): and everything until def is_sla_breached(self):
pattern = r'    def save\(self, \*args, \*\*kwargs\):.*?    def is_sla_breached\(self\):'
content = re.sub(pattern, new_save_method.strip('\n') + '\n\n    def is_sla_breached(self):', content, flags=re.DOTALL)

with open('tracking_app/models.py', 'w') as f:
    f.write(content)
