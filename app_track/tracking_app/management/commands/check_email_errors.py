from django.core.management.base import BaseCommand
from tracking_app.outreach_agent import OutreachAgentLog

class Command(BaseCommand):
    help = "Prints the latest outreach agent errors to diagnose email failures."

    def handle(self, *args, **options):
        logs = OutreachAgentLog.objects.filter(level="error").order_by('-created_at')[:10]
        if not logs:
            self.stdout.write(self.style.SUCCESS("No error logs found in the database."))
            return
            
        self.stdout.write(self.style.ERROR("--- LATEST OUTREACH ERRORS ---"))
        for log in logs:
            self.stdout.write(f"[{log.created_at}] Channel: {log.channel} | Message: {log.message}")
