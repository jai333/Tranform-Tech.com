import csv, json, os, threading
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

TIER1_TITLES = ["ceo","founder","co-founder","president","owner","cto","cro",
    "vp of sales","head of sales","director of sales","vp of hr","head of talent",
    "head of recruiting","vp of talent acquisition","director of recruiting",
    "vp of it","director of it","coo","managing director","managing partner",
    "chief technology officer","chief revenue officer","vp sales","director of operations"]
TIER2_TITLES = ["director of engineering","recruiting manager","talent acquisition manager",
    "it manager","it director","sales operations manager","sales manager","head of operations"]
SKIP_TITLES = ["software engineer","developer","designer","analyst","accountant",
    "clerk","intern","coordinator","assistant","junior","associate"]
TIER1_INDUSTRIES = ["staffing","recruiting","talent","hr","human resources",
    "it services","managed services","msp","it consulting","saas","software",
    "tech","technology","fintech","edtech","cybersecurity","security"]
TIER2_INDUSTRIES = ["consulting","professional services","accounting","legal",
    "healthcare it","logistics tech","marketing agency","digital agency"]

SEQUENCES = {
    "US": {"name": "US Global Outreach Q4-2026", "goal": "Book demos with US IT, Staffing, SaaS decision makers"},
    "UK": {"name": "UK Expansion Campaign Q4-2026", "goal": "Break into UK market"},
    "RU": {"name": "Russia & CIS Expansion Q4-2026", "goal": "Reach IT, SaaS, staffing firms across Russia and CIS"},
    "IN": {"name": "India Tech Market Q4-2026", "goal": "Target Indian IT services, staffing, SaaS companies"},
    "DEFAULT": {"name": "Global Outreach Q4-2026", "goal": "International lead outreach for Transform-Tech"},
}

def score_lead(row):
    score = 0
    breakdown = {}
    title = (row.get("title") or row.get("job_title") or "").lower().strip()
    industry = (row.get("industry") or "").lower().strip()
    email = (row.get("email") or "").strip()
    linkedin = (row.get("linkedin_url") or row.get("linkedin") or "").strip()
    try:
        headcount = int(str(row.get("employee_count") or "0").replace(",","").split("-")[0].strip() or 0)
    except:
        headcount = 0
    if any(t in title for t in SKIP_TITLES):
        breakdown["title"] = 0
    elif any(t in title for t in TIER1_TITLES):
        score += 30; breakdown["title"] = 30
    elif any(t in title for t in TIER2_TITLES):
        score += 18; breakdown["title"] = 18
    else:
        breakdown["title"] = 0
    if any(i in industry for i in TIER1_INDUSTRIES):
        score += 25; breakdown["industry"] = 25
    elif any(i in industry for i in TIER2_INDUSTRIES):
        score += 15; breakdown["industry"] = 15
    else:
        breakdown["industry"] = 0
    if 15 <= headcount <= 500:
        score += 20; breakdown["headcount"] = 20
    elif 5 <= headcount < 15:
        score += 10; breakdown["headcount"] = 10
    elif 500 < headcount <= 2000:
        score += 8; breakdown["headcount"] = 8
    else:
        breakdown["headcount"] = 0
    if email and "@" in email:
        domain = email.split("@")[1].lower()
        if domain not in ["gmail.com","yahoo.com","hotmail.com","outlook.com","icloud.com","aol.com","protonmail.com","yandex.ru","mail.ru"]:
            score += 15; breakdown["email"] = 15
        else:
            breakdown["email"] = 0
    else:
        breakdown["email"] = 0
    if linkedin and "linkedin.com" in linkedin:
        score += 10; breakdown["linkedin"] = 10
    else:
        breakdown["linkedin"] = 0
    return min(score, 100), breakdown

class Command(BaseCommand):
    help = "Import global leads from CSV, score with ICP engine, launch country campaigns."

    def add_arguments(self, parser):
        parser.add_argument("--csv", type=str, help="Path to CSV file")
        parser.add_argument("--country", type=str, default="US", choices=["US","UK","RU","IN","DEFAULT"])
        parser.add_argument("--min-score", type=int, default=50)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--tenant-name", type=str, default=None)
        parser.add_argument("--deploy-agent", action="store_true")

    def handle(self, *args, **options):
        from tracking_app.sales_models import Lead, OutreachCampaign
        from tracking_app.models import Tenant
        from django.contrib.auth import get_user_model
        User = get_user_model()

        csv_path = options["csv"]
        country = options["country"].upper()
        min_score = options["min_score"]
        dry_run = options["dry_run"]
        deploy_agent = options["deploy_agent"]

        tenant_name = options.get("tenant_name")
        if tenant_name:
            try:
                tenant = Tenant.objects.get(name=tenant_name)
            except Tenant.DoesNotExist:
                raise CommandError(f"Tenant not found: {tenant_name}")
        else:
            su = User.objects.filter(is_superuser=True).first()
            if not su or not su.tenant:
                raise CommandError("No superuser with tenant. Use --tenant-name.")
            tenant = su.tenant

        self.stdout.write(f"Tenant: {tenant.name}")
        if not csv_path:
            raise CommandError("Provide --csv /path/to/leads.csv")
        if not os.path.exists(csv_path):
            raise CommandError(f"Not found: {csv_path}")

        seq = SEQUENCES.get(country, SEQUENCES["DEFAULT"])
        cname = seq['name']
        self.stdout.write(f"Country: {country} | Campaign: {cname}")

        total = hot = warm = cold = skipped = imported = 0
        leads_to_create = []
        hot_emails = []

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = [{k.strip().lower().replace(" ","_"): (v or "").strip() for k,v in row.items()} for row in reader]

        self.stdout.write(f"Read {len(rows)} rows from CSV.")

        for row in rows:
            total += 1
            score, breakdown = score_lead(row)
            tier = "hot" if score >= 70 else ("warm" if score >= 50 else "cold")
            if tier == "hot": hot += 1
            elif tier == "warm": warm += 1
            else: cold += 1

            if score < min_score:
                skipped += 1
                continue

            if dry_run:
                icon = "FIRE" if tier == "hot" else "WARM"
                fn=row.get("first_name",""); ln=row.get("last_name",""); cn=row.get("company_name",""); tt=row.get("title","")
                self.stdout.write(f"  {icon} [{score}/100] {fn} {ln} @ {cn} ({tt})")
                continue

            first = row.get("first_name","") or row.get("firstname","")
            last = row.get("last_name","") or row.get("lastname","")
            contact_name = f"{first} {last}".strip() or row.get("name","Unknown")
            email = row.get("email","").strip()
            phone = row.get("phone","").strip()
            if not email and not phone:
                skipped += 1; continue
            if email and Lead.objects.filter(email=email).exists():
                skipped += 1; continue
            location = ", ".join([p for p in [row.get("city",""), row.get("state",""), row.get("country","")] if p])
            lead = Lead(
                tenant=tenant, contact_name=contact_name, email=email or None, phone=phone or None,
                company_name=row.get("company_name","") or row.get("company",""),
                industry=row.get("industry",""),
                linkedin_url=row.get("linkedin_url","") or row.get("linkedin","") or None,
                company_location=location, source="apollo", status="new",
                icp_score=float(score), icp_score_breakdown=breakdown,
                notes=("Title: " + row.get("title","") + " | Country: " + country),
            )
            leads_to_create.append(lead)
            if tier == "hot" and email:
                hot_emails.append(email)

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY RUN: {hot} hot, {warm} warm, {cold} cold."))
            return

        with transaction.atomic():
            Lead.objects.bulk_create(leads_to_create, ignore_conflicts=True)
            imported = len(leads_to_create)
        self.stdout.write(self.style.SUCCESS(f"Imported {imported} leads."))

        cseq_name = seq["name"]; cseq_goal = seq["goal"]
        campaign, created = OutreachCampaign.objects.get_or_create(
            tenant=tenant, name=cseq_name,
            defaults={"goal": cseq_goal, "status": "active", "channel_email": True, "channel_sms": False}
        )
        seqn = seq["name"]; self.stdout.write(self.style.SUCCESS(f"Campaign: {seqn} ({'created' if created else 'exists'})"))

        if deploy_agent and hot_emails:
            from tracking_app.tasks import run_autonomous_agent
            hot_db = Lead.objects.filter(tenant=tenant, email__in=hot_emails).order_by("-id")
            self.stdout.write(f"Deploying agent for {hot_db.count()} HOT leads...")
            for lead in hot_db:
                t = threading.Thread(target=run_autonomous_agent, kwargs={"lead_id": lead.id, "channels": ["email"], "tenant_id": tenant.id})
                t.daemon = True; t.start()
                lead.status = "in_sequence"; lead.save(update_fields=["status"])
            self.stdout.write(self.style.SUCCESS(f"Agents launched: {hot_db.count()}"))

        self.stdout.write(self.style.SUCCESS(f"""
{'='*50}
  IMPORT COMPLETE
{'='*50}
  Country: {country} | Hot: {hot} | Warm: {warm} | Cold: {cold}
  Imported: {imported} leads
  Next: https://transform-tech.com/sales/
{'='*50}"""))