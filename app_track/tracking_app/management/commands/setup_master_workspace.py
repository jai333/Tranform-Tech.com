
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tracking_app.models import Tenant, AutomationRule, ITTicket, Candidate
from tracking_app.sales_models import Lead, Deal
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = "Provisions the Transform-Tech Master Workspace for internal dogfooding."

    def handle(self, *args, **kwargs):
        self.stdout.write("Initializing Transform-Tech Master Workspace...")

        # 1. Create the Master Tenant
        tenant, created = Tenant.objects.get_or_create(
            domain="transform-tech.com",
            defaults={
                "name": "Transform-Tech Internal",
                "subscription_plan": "enterprise",
                "custom_field_schema": {
                    "Lead": [
                        {"name": "Target ARR", "type": "number", "required": False},
                        {"name": "Current Tech Stack", "type": "text", "required": False}
                    ]
                }
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Tenant: {tenant.name}"))
        else:
            self.stdout.write(f"Tenant {tenant.name} already exists.")

        # 2. Create the Master Admin User
        admin_email = "jai@transform-tech.com"
        admin_user, admin_created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "username": "jaisukhwal",
                "first_name": "Jai",
                "last_name": "Sukhwal",
                "is_staff": True,
                "is_superuser": True,
                "role": "admin",
                "tenant": tenant,
            }
        )
        if admin_created:
            admin_user.set_password("Admin123!Transform")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created Master Admin: {admin_email}"))

        # 3. Inject Demo Leads
        leads_data = [
            {"first_name": "Alice", "last_name": "Johnson", "company": "Acme IT Solutions", "email": "alice@acmeit.com"},
            {"first_name": "Robert", "last_name": "Chen", "company": "Global BPO Partners", "email": "robert@globalbpo.com"},
            {"first_name": "Samantha", "last_name": "Wright", "company": "NextGen SaaS", "email": "swright@nextgensaas.io"}
        ]
        for ld in leads_data:
            lead, l_created = Lead.objects.get_or_create(
                email=ld["email"],
                tenant=tenant,
                defaults={
                    "contact_name": ld["first_name"] + " " + ld["last_name"],
                    "company_name": ld["company"],
                    "status": "new",
                    
                    "custom_data": {"Target ARR": 50000, "Current Tech Stack": "Salesforce, Zendesk"}
                }
            )
            if l_created:
                cname = ld["company"]
                Deal.objects.create(
                    tenant=tenant,
                    lead=lead,
                    deal_value_annual=50000,
                    stage="proposal"
                )

        self.stdout.write(self.style.SUCCESS("Injected Demo Leads & Deals."))

        # 4. Inject Demo Candidates
        candidates_data = [
            {"first_name": "Michael", "last_name": "Scott", "email": "mscott@example.com", "title": "Senior Python Engineer"},
            {"first_name": "Pam", "last_name": "Beesly", "email": "pbeesly@example.com", "title": "Customer Success Manager"}
        ]
        for cd in candidates_data:
            title = cd["title"]
            Candidate.objects.get_or_create(
                email=cd["email"],
                tenant=tenant,
                defaults={
                    "first_name": cd["first_name"],
                    "last_name": cd["last_name"],
                    
                    "resume": f"Experienced {title}."
                }
            )
            
        self.stdout.write(self.style.SUCCESS("Injected Demo Candidates."))

        # 5. Create Workflow Automation Rule
        rule, r_created = AutomationRule.objects.get_or_create(
            tenant=tenant,
            name="Auto-Welcome New Leads",
            defaults={
                "trigger_type": "lead_created",
                "conditions": {},
                "actions": [
                    {"action_type": "send_email", "template_name": "Welcome to Transform-Tech"}
                ],
                "is_active": True
            }
        )
        if r_created:
            self.stdout.write(self.style.SUCCESS("Activated Visual Workflow Automation: Auto-Welcome New Leads."))

        self.stdout.write(self.style.SUCCESS("MASTER WORKSPACE PROVISIONING COMPLETE!"))
        self.stdout.write("Login: jai@transform-tech.com")
        self.stdout.write("Password: Admin123!Transform")

