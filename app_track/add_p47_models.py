import os

models_to_add = """
class RoutingRule(models.Model):
    category = models.CharField(max_length=50, unique=True, choices=ITTicket.CATEGORY_CHOICES)
    assign_to = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role__in': ['admin', 'it_agent']})

    def __str__(self):
        return f"{self.get_category_display()} -> {self.assign_to}"

class TicketAuditLog(models.Model):
    ticket = models.ForeignKey(ITTicket, on_delete=models.CASCADE, related_name='audit_logs')
    actor = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    field_changed = models.CharField(max_length=50)
    old_value = models.CharField(max_length=255, null=True, blank=True)
    new_value = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket.id} - {self.field_changed} changed at {self.timestamp}"

class KBArticle(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    tags = models.CharField(max_length=255, null=True, blank=True, help_text="Comma-separated tags")
    upvotes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class TicketSurvey(models.Model):
    ticket = models.OneToOneField(ITTicket, on_delete=models.CASCADE, related_name='survey')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Survey for Ticket {self.ticket.id} - {self.rating}/5"

"""

with open('tracking_app/models.py', 'r') as f:
    content = f.read()

if "class RoutingRule" not in content:
    with open('tracking_app/models.py', 'a') as f:
        f.write(models_to_add)
    print("Added new models.")
else:
    print("Models already exist.")
