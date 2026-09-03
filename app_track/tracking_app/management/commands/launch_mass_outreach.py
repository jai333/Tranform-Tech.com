from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tracking_app.models import Tenant
from tracking_app.sales_models import Lead, Deal, OutreachCampaign
from tracking_app.tasks import run_autonomous_agent
import random
import uuid

User = get_user_model()

class Command(BaseCommand):
    help = "Simulates importing a large dataset and launching mass AI outreach."

    def add_arguments(self, parser):
        parser.add_argument('--volume', type=int, default=500, help='Number of leads to generate')

    def handle(self, *args, **options):
        volume = options['volume']
        self.stdout.write(f"Initiating MASS OUTREACH for {volume} leads...")

        tenant = Tenant.objects.get(name="Transform-Tech Internal")
        
        # 1. Create a Mass Outreach Campaign
        campaign, _ = OutreachCampaign.objects.get_or_create(
            tenant=tenant,
            name=f"Mass SaaS Consolidation Q3 (Volume: {volume})",
            defaults={
                "goal": "Book 50 Demos by identifying fragmentation pain.",
                "status": "active",
                "channel_email": True,
                "channel_sms": False,
            }
        )

        self.stdout.write(self.style.SUCCESS(f"Created Campaign: {campaign.name}"))

        # 2. Inject high volume of leads
        cities = ["Austin", "Dallas", "Denver", "Chicago", "Seattle", "Atlanta", "NYC", "Miami"]
        industries = ["IT Services", "SaaS", "Staffing", "Accounting", "Logistics"]
        job_titles = ["CEO", "Founder", "COO", "Managing Director", "VP Operations"]

        new_leads = []
        for i in range(volume):
            company_name = f"TechCorp {uuid.uuid4().hex[:6].upper()}"
            first_name = f"Exec{i}"
            lead = Lead(
                tenant=tenant,
                company_name=company_name,
                contact_name=f"{first_name} {random.choice(job_titles)}",
                email=f"founder_{i}@{company_name.lower().replace(' ', '')}.com",
                industry=random.choice(industries),
                company_location=random.choice(cities),
                status="new",
                source="apollo",
                icp_score=random.uniform(70.0, 99.0)
            )
            new_leads.append(lead)
        
        # Bulk create leads
        Lead.objects.bulk_create(new_leads)
        self.stdout.write(self.style.SUCCESS(f"Successfully bulk-inserted {volume} Leads into CRM."))

        # 3. Retrieve them to get IDs, then queue Celery tasks
        inserted_leads = Lead.objects.filter(tenant=tenant, source="apollo", status="new").order_by('-id')[:volume]
        
        deals = []
        for l in inserted_leads:
            deals.append(Deal(tenant=tenant, lead=l, stage="lead", deal_value_annual=random.randint(10000, 50000)))
        Deal.objects.bulk_create(deals)
        self.stdout.write(self.style.SUCCESS(f"Attached Pipeline Deals for forecasting."))

        # 4. Trigger the Autonomous Agent asynchronously
        self.stdout.write("Firing AI Autonomous Sales Agent via Celery...")
        task_count = 0
        for l in inserted_leads:
            run_autonomous_agent.delay(
                lead_id=l.id,
                campaign_id=campaign.id,
                channels=['email'],
                tenant_id=tenant.id
            )
            task_count += 1
            if task_count % 100 == 0:
                self.stdout.write(f"... queued {task_count} agents.")
                
        self.stdout.write(self.style.SUCCESS(f"SUCCESS: {volume} Autonomous Sales Agents have successfully generated and sent emails synchronously!"))
