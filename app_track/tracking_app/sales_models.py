"""
AI-Powered Automated Sales System — Models
Handles: Lead Intelligence, Email Sequences, Deal Pipeline,
         Demo Bookings, Revenue Dashboard, Onboarding Funnel
"""

from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────
# LAYER 1 — Lead Intelligence
# ─────────────────────────────────────────────────────────────────

class LeadFolder(models.Model):
    """A collection of leads, usually generated from a specific search or campaign."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tenant = models.ForeignKey('tracking_app.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='lead_folders')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Lead(models.Model):
    """A prospective customer discovered or enriched by AI."""

    SOURCE_CHOICES = [
        ('apollo', 'Apollo.io'),
        ('linkedin', 'LinkedIn'),
        ('serp', 'Job Board Scrape'),
        ('manual', 'Manual Entry'),
        ('inbound', 'Inbound (Website)'),
        ('referral', 'Referral'),
        ('google_maps', 'Google Maps Scraper'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('enriched', 'Enriched'),
        ('qualified', 'Qualified'),
        ('in_sequence', 'In Sequence'),
        ('replied', 'Replied'),
        ('demo_booked', 'Demo Booked'),
        ('demo_done', 'Demo Done'),
        ('converted', 'Converted'),
        ('lost', 'Lost'),
        ('unsubscribed', 'Unsubscribed'),
        ('nurture', 'Long-Term Nurture'),
    ]

    # Contact information
    contact_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)  # nullable for Google Maps leads
    linkedin_url = models.URLField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)

    # Company information
    company_name = models.CharField(max_length=200)
    company_size = models.IntegerField(null=True, blank=True, help_text="Number of employees")
    industry = models.CharField(max_length=100, blank=True, null=True)
    company_website = models.URLField(blank=True, null=True)
    company_location = models.CharField(max_length=255, blank=True, null=True)

    # Google Maps extra data
    gmaps_place_id = models.CharField(max_length=200, blank=True, null=True, unique=True)
    gmaps_rating = models.FloatField(null=True, blank=True)
    gmaps_reviews = models.IntegerField(null=True, blank=True)
    gmaps_category = models.CharField(max_length=200, blank=True, null=True)
    gmaps_address = models.TextField(blank=True, null=True)
    gmaps_maps_url = models.URLField(blank=True, null=True)

    # AI-enriched data
    tech_stack = models.JSONField(default=list, help_text="Technologies used by the company")
    pain_points = models.JSONField(default=list, help_text="AI-identified pain points")
    personalization_data = models.JSONField(default=dict, help_text="Data used for email personalization")
    current_ats_tool = models.CharField(max_length=100, blank=True, null=True, help_text="ATS they currently use")

    # AI Scoring
    icp_score = models.FloatField(default=0.0, help_text="Ideal Customer Profile fit score 0-100")
    icp_score_breakdown = models.JSONField(default=dict, help_text="Breakdown of scoring factors")

    # Pipeline
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='manual')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')

    # Activity tracking
    email_opens = models.IntegerField(default=0)
    email_clicks = models.IntegerField(default=0)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    custom_data = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    enriched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-icp_score', '-created_at']
        constraints = [
            # Only enforce email uniqueness when email is not null
            models.UniqueConstraint(
                fields=['email'],
                condition=models.Q(email__isnull=False),
                name='unique_lead_email_when_not_null',
            )
        ]

    tenant = models.ForeignKey('tracking_app.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='%(class)ss')
    folder = models.ForeignKey(LeadFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')

    def __str__(self):
        return f"{self.contact_name} @ {self.company_name} ({self.icp_score:.0f}/100)"

    @property
    def is_hot(self):
        """Lead is hot if high score and recent activity."""
        if self.email_opens >= 3 or self.icp_score >= 80:
            return True
        return False

    @property
    def days_since_activity(self):
        if not self.last_activity_at:
            return None
        return (timezone.now() - self.last_activity_at).days


# ─────────────────────────────────────────────────────────────────
# LAYER 2 — Email Sequence Engine
# ─────────────────────────────────────────────────────────────────

class EmailSequence(models.Model):
    """Defines a multi-step drip email campaign."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class EmailSequenceStep(models.Model):
    """A single email in a sequence, sent after N days."""

    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE, related_name='steps')
    step_number = models.IntegerField()
    delay_days = models.IntegerField(help_text="Days after previous step (or enrollment for step 1)")
    subject_template = models.CharField(max_length=300, help_text="AI prompt or subject template")
    body_template = models.TextField(help_text="AI prompt or body template")
    is_ai_generated = models.BooleanField(default=True, help_text="Use AI to personalise each email")

    class Meta:
        ordering = ['step_number']
        unique_together = ('sequence', 'step_number')

    def __str__(self):
        return f"{self.sequence.name} — Step {self.step_number} (Day +{self.delay_days})"


class LeadSequenceEnrollment(models.Model):
    """Tracks a lead's progress through an email sequence."""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('replied', 'Replied — Paused'),
        ('unsubscribed', 'Unsubscribed'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='enrollments')
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    current_step = models.IntegerField(default=1)
    next_email_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('lead', 'sequence')

    def __str__(self):
        return f"{self.lead.contact_name} in '{self.sequence.name}' (step {self.current_step})"


class OutreachEmail(models.Model):
    """A single email generated and sent to a lead."""

    VARIANT_CHOICES = [('A', 'Variant A'), ('B', 'Variant B')]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('replied', 'Replied'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='outreach_emails')
    enrollment = models.ForeignKey(LeadSequenceEnrollment, on_delete=models.CASCADE, related_name='emails', null=True)
    step = models.ForeignKey(EmailSequenceStep, on_delete=models.SET_NULL, null=True)
    tenant = models.ForeignKey('tracking_app.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='outreach_emails')

    subject = models.CharField(max_length=300)
    body = models.TextField()
    variant = models.CharField(max_length=1, choices=VARIANT_CHOICES, default='A')
    sender_email = models.EmailField(blank=True, null=True, help_text="Registered tenant sender email address used")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    tracking_pixel_id = models.CharField(max_length=64, unique=True, null=True, blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email to {self.lead.email} — {self.subject[:50]}"


class EmailReply(models.Model):
    """Stores and classifies a reply from a lead."""

    INTENT_CHOICES = [
        ('interested', 'Interested'),
        ('objection', 'Objection'),
        ('not_now', 'Not Right Now'),
        ('question', 'Has a Question'),
        ('unsubscribe', 'Unsubscribe'),
        ('other', 'Other'),
    ]

    email = models.ForeignKey(OutreachEmail, on_delete=models.CASCADE, related_name='replies')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='replies')
    tenant = models.ForeignKey('tracking_app.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='email_replies')

    raw_content = models.TextField()
    ai_intent = models.CharField(max_length=20, choices=INTENT_CHOICES, null=True, blank=True)
    ai_response_draft = models.TextField(blank=True, null=True, help_text="AI-generated reply suggestion")
    ai_response_sent = models.BooleanField(default=False)

    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Reply from {self.lead.email} — intent: {self.ai_intent}"


# ─────────────────────────────────────────────────────────────────
# LAYER 4 — Demo Booking
# ─────────────────────────────────────────────────────────────────

class DemoBooking(models.Model):
    """A scheduled product demonstration with a prospect."""

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
        ('cancelled', 'Cancelled'),
        ('converted', 'Converted to Customer'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='demo_bookings')
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    # Qualification data collected pre-demo
    team_size = models.IntegerField(null=True, blank=True)
    current_ats = models.CharField(max_length=100, blank=True, null=True)
    main_pain_point = models.TextField(blank=True, null=True)
    budget_range = models.CharField(max_length=50, blank=True, null=True)

    # Integration
    calendly_event_id = models.CharField(max_length=200, blank=True, null=True)
    meeting_url = models.URLField(blank=True, null=True)

    # AI-generated content
    ai_prep_notes = models.TextField(blank=True, null=True, help_text="AI-generated call prep brief")
    ai_call_summary = models.TextField(blank=True, null=True, help_text="AI-generated post-call summary")
    recording_url = models.URLField(blank=True, null=True)

    # Follow-up
    follow_up_sent = models.BooleanField(default=False)
    proposal_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Demo with {self.lead.contact_name} @ {self.scheduled_at.strftime('%Y-%m-%d %H:%M')}"


# ─────────────────────────────────────────────────────────────────
# LAYER 5 — Deal Pipeline
# ─────────────────────────────────────────────────────────────────

class Deal(models.Model):
    """A sales opportunity in the pipeline."""

    STAGE_CHOICES = [
        ('lead', 'New Lead'),
        ('outreach', 'Outreach Sent'),
        ('replied', 'Replied'),
        ('demo_booked', 'Demo Booked'),
        ('demo_done', 'Demo Done'),
        ('proposal', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]

    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name='deal')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='lead')

    deal_value_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deal_value_annual = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    close_probability = models.FloatField(default=0.0, help_text="AI-predicted probability 0.0–1.0")
    expected_close_date = models.DateField(null=True, blank=True)
    actual_close_date = models.DateField(null=True, blank=True)

    lost_reason = models.CharField(max_length=200, blank=True, null=True)
    competitor_lost_to = models.CharField(max_length=100, blank=True, null=True)

    ai_next_action = models.TextField(blank=True, null=True, help_text="AI-recommended next step")
    ai_risk_flag = models.CharField(max_length=200, blank=True, null=True, help_text="AI-detected risk")

    last_activity_at = models.DateTimeField(null=True, blank=True)
    tenant = models.ForeignKey('tracking_app.Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='deals')
    custom_data = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-close_probability', '-deal_value_monthly']

    def __str__(self):
        return f"Deal: {self.lead.company_name} — {self.stage} (${self.deal_value_monthly}/mo)"

    @property
    def weighted_value(self):
        return float(self.deal_value_monthly) * self.close_probability

    @property
    def days_since_activity(self):
        if not self.last_activity_at:
            return 999
        return (timezone.now() - self.last_activity_at).days

    @property
    def is_cold(self):
        return self.days_since_activity >= 7 and self.stage not in ('won', 'lost')


class DealActivity(models.Model):
    """Log of all activities on a deal."""

    TYPE_CHOICES = [
        ('email_sent', 'Email Sent'),
        ('email_opened', 'Email Opened'),
        ('email_replied', 'Email Replied'),
        ('demo_booked', 'Demo Booked'),
        ('demo_completed', 'Demo Completed'),
        ('call', 'Phone Call'),
        ('linkedin_dm', 'LinkedIn DM'),
        ('note', 'Note Added'),
        ('stage_changed', 'Stage Changed'),
        ('ai_action', 'AI Action'),
    ]

    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description = models.TextField()
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.activity_type} — {self.deal.lead.company_name}"


# ─────────────────────────────────────────────────────────────────
# LAYER 6 — Revenue Intelligence
# ─────────────────────────────────────────────────────────────────

class SalesDailySnapshot(models.Model):
    """Daily snapshot of key sales metrics for the dashboard."""

    date = models.DateField(unique=True)

    # Volume
    new_leads = models.IntegerField(default=0)
    leads_enriched = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    emails_replied = models.IntegerField(default=0)
    demos_booked = models.IntegerField(default=0)
    demos_completed = models.IntegerField(default=0)
    deals_won = models.IntegerField(default=0)

    # Revenue
    mrr_new = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pipeline_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Snapshot {self.date}"


class SalesAlert(models.Model):
    """AI-generated alerts for the sales dashboard."""

    TYPE_CHOICES = [
        ('hot_lead', '🔥 Hot Lead'),
        ('cold_deal', '⚠️ Deal Going Cold'),
        ('new_batch', '✅ New Leads Ready'),
        ('demo_reminder', '📅 Demo Upcoming'),
        ('reply_received', '💬 Reply Received'),
        ('milestone', '🎉 Milestone'),
    ]

    alert_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True)
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.alert_type}: {self.title}"


# ─────────────────────────────────────────────────────────────────
# LAYER 7 — Onboarding Funnel
# ─────────────────────────────────────────────────────────────────

class OnboardingFunnel(models.Model):
    """Tracks a trial user's onboarding progress and activation."""

    PLAN_CHOICES = [
        ('trial', 'Free Trial'),
        ('starter', 'Starter ($49/mo)'),
        ('growth', 'Growth ($99/mo)'),
        ('pro', 'Pro ($199/mo)'),
        ('enterprise', 'Enterprise'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.OneToOneField('tracking_app.User', on_delete=models.CASCADE, related_name='onboarding')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial')
    trial_started_at = models.DateTimeField(auto_now_add=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Activation milestones (each True = they hit the milestone)
    added_first_candidate = models.BooleanField(default=False)
    scheduled_first_interview = models.BooleanField(default=False)
    used_ai_parsing = models.BooleanField(default=False)
    created_first_job = models.BooleanField(default=False)
    invited_team_member = models.BooleanField(default=False)

    # Computed activation score 0-100
    activation_score = models.IntegerField(default=0)

    # AI nudge tracking
    last_nudge_sent_at = models.DateTimeField(null=True, blank=True)
    nudge_count = models.IntegerField(default=0)
    ai_health_notes = models.TextField(blank=True, null=True)

    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Onboarding: {self.user.username} — {self.plan}"

    def compute_activation_score(self):
        """Recalculate activation score based on milestones."""
        milestones = [
            self.added_first_candidate,
            self.scheduled_first_interview,
            self.used_ai_parsing,
            self.created_first_job,
            self.invited_team_member,
        ]
        score = sum(20 for m in milestones if m)
        self.activation_score = score
        return score

    @property
    def days_in_trial(self):
        return (timezone.now() - self.trial_started_at).days

    @property
    def trial_days_remaining(self):
        if self.trial_ends_at:
            remaining = (self.trial_ends_at - timezone.now()).days
            return max(0, remaining)
        return None


# ─────────────────────────────────────────────────────────────────
# LAYER 8 — B2B Account & Contact Management
# ─────────────────────────────────────────────────────────────────

class Account(models.Model):
    """A B2B client company / prospect organisation."""
    INDUSTRY_CHOICES = [
        ('technology',    'Technology'),
        ('finance',       'Finance & Banking'),
        ('healthcare',    'Healthcare'),
        ('retail',        'Retail & E-commerce'),
        ('manufacturing', 'Manufacturing'),
        ('consulting',    'Consulting'),
        ('media',         'Media & Advertising'),
        ('education',     'Education'),
        ('real_estate',   'Real Estate'),
        ('other',         'Other'),
    ]
    SIZE_CHOICES = [
        ('1-10',     '1–10 employees'),
        ('11-50',    '11–50 employees'),
        ('51-200',   '51–200 employees'),
        ('201-1000', '201–1,000 employees'),
        ('1000+',    '1,000+ employees'),
    ]
    name           = models.CharField(max_length=255)
    industry       = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, blank=True)
    website        = models.URLField(blank=True, null=True)
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    employee_count = models.CharField(max_length=20, choices=SIZE_CHOICES, blank=True)
    phone          = models.CharField(max_length=30, blank=True)
    address        = models.TextField(blank=True)
    description    = models.TextField(blank=True)
    owner          = models.ForeignKey('tracking_app.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_accounts')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    tenant = models.ForeignKey('tracking_app.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='%(class)ss')

    def __str__(self):
        return self.name


class AccountContact(models.Model):
    """A key stakeholder or buyer persona at a B2B account."""
    account    = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='contacts')
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)
    title      = models.CharField(max_length=255, blank=True)
    email      = models.EmailField(blank=True)
    phone      = models.CharField(max_length=30, blank=True)
    linkedin   = models.URLField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    notes      = models.TextField(blank=True)
    tenant     = models.ForeignKey('tracking_app.Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='account_contacts')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} @ {self.account.name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class AccountActivity(models.Model):
    """Log calls, emails, demos, notes against a B2B account."""
    TYPE_CHOICES = [
        ('call',      'Phone Call'),
        ('email',     'Email'),
        ('meeting',   'Meeting'),
        ('demo',      'Product Demo'),
        ('follow_up', 'Follow-up'),
        ('note',      'Note'),
    ]
    account       = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='account_activities')
    contact       = models.ForeignKey(AccountContact, on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='call')
    subject       = models.CharField(max_length=255)
    notes         = models.TextField(blank=True)
    performed_by  = models.ForeignKey('tracking_app.User', on_delete=models.SET_NULL, null=True, related_name='account_activities')
    created_at    = models.DateTimeField(auto_now_add=True)
    due_date      = models.DateField(null=True, blank=True)
    completed     = models.BooleanField(default=False)
    tenant        = models.ForeignKey('tracking_app.Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='account_activities_log')

    def __str__(self):
        return f"{self.get_activity_type_display()} – {self.subject}"


# -----------------------------------------------------------------
# LAYER 9 — Autonomous AI Sales Outreach Agent
# -----------------------------------------------------------------

class OutreachCampaign(models.Model):
    """A named outreach campaign grouping multiple agent-driven runs."""
    STATUS_CHOICES = [
        ("draft",    "Draft"),
        ("active",   "Active"),
        ("paused",   "Paused"),
        ("complete", "Complete"),
        ("archived", "Archived"),
    ]
    PERSONALIZATION_CHOICES = [
        ("quick",    "Quick (Fast, template-based)"),
        ("standard", "Standard (AI-personalized per lead)"),
        ("deep",     "Deep (Research + multi-signal context)"),
    ]

    name        = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    goal        = models.CharField(max_length=300, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    channel_email = models.BooleanField(default=True)
    channel_sms   = models.BooleanField(default=True)
    channel_call  = models.BooleanField(default=False)
    personalization_level = models.CharField(max_length=20, choices=PERSONALIZATION_CHOICES, default="standard")
    enroll_in_sequence = models.BooleanField(default=True)
    sequence_days = models.JSONField(default=list)
    leads_targeted   = models.IntegerField(default=0)
    emails_sent      = models.IntegerField(default=0)
    sms_sent         = models.IntegerField(default=0)
    calls_initiated  = models.IntegerField(default=0)
    replies_received = models.IntegerField(default=0)
    demos_booked     = models.IntegerField(default=0)
    tenant     = models.ForeignKey("tracking_app.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="outreach_campaigns")
    created_by = models.ForeignKey("tracking_app.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def reply_rate(self):
        if self.emails_sent == 0:
            return 0.0
        return round(self.replies_received / self.emails_sent * 100, 1)


class AgentOutreachRun(models.Model):
    """A single autonomous outreach execution for one lead across all channels."""
    STATUS_CHOICES = [
        ("queued",    "Queued"),
        ("running",   "Running"),
        ("completed", "Completed"),
        ("partial",   "Partial (some channels failed)"),
        ("failed",    "Failed"),
        ("skipped",   "Skipped"),
    ]
    CHANNEL_STATUS = [
        ("pending",   "Pending"),
        ("sent",      "Sent"),
        ("initiated", "Initiated"),
        ("completed", "Completed"),
        ("no_answer", "No Answer"),
        ("failed",    "Failed"),
        ("skipped",   "Skipped"),
    ]

    campaign = models.ForeignKey(OutreachCampaign, on_delete=models.CASCADE, related_name="runs", null=True, blank=True)
    lead     = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="agent_runs")
    tenant   = models.ForeignKey("tracking_app.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="agent_runs")
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    icp_score   = models.FloatField(default=0.0)
    skip_reason = models.CharField(max_length=300, blank=True, null=True)

    email_enabled = models.BooleanField(default=True)
    email_subject = models.CharField(max_length=400, blank=True)
    email_body    = models.TextField(blank=True)
    email_status  = models.CharField(max_length=20, default="pending", choices=CHANNEL_STATUS)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_opened  = models.BooleanField(default=False)
    email_clicked = models.BooleanField(default=False)
    email_replied = models.BooleanField(default=False)

    sms_enabled = models.BooleanField(default=True)
    sms_body    = models.TextField(blank=True)
    sms_status  = models.CharField(max_length=20, default="pending", choices=CHANNEL_STATUS)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    sms_sid     = models.CharField(max_length=100, blank=True, null=True)

    call_enabled          = models.BooleanField(default=False)
    call_script           = models.TextField(blank=True)
    call_status           = models.CharField(max_length=20, default="pending", choices=CHANNEL_STATUS)
    call_sid              = models.CharField(max_length=100, blank=True, null=True)
    call_initiated_at     = models.DateTimeField(null=True, blank=True)
    call_duration_seconds = models.IntegerField(default=0)

    sequence_enrolled = models.BooleanField(default=False)
    sequence_step     = models.IntegerField(default=0)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    started_at        = models.DateTimeField(null=True, blank=True)
    completed_at      = models.DateTimeField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AgentRun -> {self.lead.contact_name} @ {self.lead.company_name} [{self.status}]"

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class OutreachAgentLog(models.Model):
    """Time-series brain log powering the real-time Command Center activity feed."""
    LEVEL_CHOICES = [
        ("info",    "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error",   "Error"),
        ("ai",      "AI Decision"),
    ]
    CHANNEL_CHOICES = [
        ("email",  "Email"),
        ("sms",    "SMS"),
        ("call",   "Call"),
        ("system", "System"),
        ("ai",     "AI"),
    ]

    run    = models.ForeignKey(AgentOutreachRun, on_delete=models.CASCADE, related_name="logs", null=True, blank=True)
    lead   = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_logs")
    tenant = models.ForeignKey("tracking_app.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="agent_logs")
    level   = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="info")
    channel = models.CharField(max_length=20, blank=True, choices=CHANNEL_CHOICES)
    message = models.TextField()
    meta    = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        lead_str = self.lead.contact_name if self.lead else "-"
        return f"[{self.level.upper()}] {lead_str}: {self.message[:80]}"
