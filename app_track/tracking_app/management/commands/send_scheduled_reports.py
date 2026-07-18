from django.core.management.base import BaseCommand
from django.utils import timezone
from tracking_app.models import ScheduledReport

class Command(BaseCommand):
    help = 'Sends active scheduled reports'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        reports = ScheduledReport.objects.filter(is_active=True)
        
        if not reports.exists():
            self.stdout.write('No active reports to send.')
            return

        for report in reports:
            self.stdout.write(self.style.SUCCESS(f'Generating report: {report.name} ({report.report_type})'))
            self.stdout.write(f'Sending to: {report.recipients}')
            
            report.last_sent = now
            
            # Update next_send based on frequency
            if report.frequency == 'daily':
                report.next_send = now + timezone.timedelta(days=1)
            elif report.frequency == 'weekly':
                report.next_send = now + timezone.timedelta(days=7)
            elif report.frequency == 'monthly':
                report.next_send = now + timezone.timedelta(days=30)
                
            report.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully sent report {report.name}'))
