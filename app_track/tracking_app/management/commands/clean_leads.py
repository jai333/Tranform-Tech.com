from django.core.management.base import BaseCommand
from tracking_app.sales_models import Lead, Deal
from django.db.models import Count

class Command(BaseCommand):
    help = "Cleans up fake/mock leads and removes duplicates."

    def handle(self, *args, **options):
        # 1. Delete Mock Leads (TechCorp / founder_)
        mock_leads = Lead.objects.filter(email__startswith="founder_", company_name__startswith="TechCorp")
        mock_count = mock_leads.count()
        mock_leads.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {mock_count} mock/test leads."))

        # 2. Deduplicate Leads based on email
        emails = Lead.objects.values('email').annotate(count=Count('id')).filter(count__gt=1)
        dup_count = 0
        for e in emails:
            email_val = e['email']
            # Keep the first one, delete the rest
            duplicates = Lead.objects.filter(email=email_val).order_by('id')
            first_id = duplicates.first().id
            deleted, _ = Lead.objects.filter(email=email_val).exclude(id=first_id).delete()
            dup_count += deleted
            
        self.stdout.write(self.style.SUCCESS(f"Deleted {dup_count} duplicate leads."))
        self.stdout.write(self.style.SUCCESS("Database is now clean and ready for real outreach."))
