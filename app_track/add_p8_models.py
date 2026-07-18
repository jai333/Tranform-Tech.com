import os

models_to_add = """
class TicketMacro(models.Model):
    title = models.CharField(max_length=100)
    response_text = models.TextField()
    auto_status = models.CharField(max_length=20, choices=ITTicket.STATUS_CHOICES, null=True, blank=True)
    auto_priority = models.CharField(max_length=10, choices=ITTicket.PRIORITY_CHOICES, null=True, blank=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class TicketWorkLog(models.Model):
    ticket = models.ForeignKey(ITTicket, on_delete=models.CASCADE, related_name='work_logs')
    agent = models.ForeignKey('User', on_delete=models.CASCADE)
    time_spent_minutes = models.PositiveIntegerField(help_text="Time spent in minutes")
    date = models.DateField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent.username} - {self.time_spent_minutes}m on Ticket {self.ticket.id}"

"""

with open('tracking_app/models.py', 'r') as f:
    content = f.read()

if "class TicketMacro" not in content:
    with open('tracking_app/models.py', 'a') as f:
        f.write(models_to_add)
    print("Added Macro and WorkLog models.")
else:
    print("Models already exist.")
