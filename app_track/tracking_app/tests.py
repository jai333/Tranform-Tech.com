
from django.test import TestCase
from django.contrib.auth import get_user_model
from tracking_app.models import Tenant, ITTicket

User = get_user_model()

class TenantIsolationTests(TestCase):
    def setUp(self):
        # Create Tenant A
        self.tenant_a = Tenant.objects.create(name="Tenant A", domain="tenanta.com")
        self.user_a = User.objects.create_user(
            username="usera", 
            email="user@tenanta.com", 
            password="password",
            tenant=self.tenant_a
        )
        
        # Create Tenant B
        self.tenant_b = Tenant.objects.create(name="Tenant B", domain="tenantb.com")
        self.user_b = User.objects.create_user(
            username="userb", 
            email="user@tenantb.com", 
            password="password",
            tenant=self.tenant_b
        )
        
        # Create Data for Tenant A
        self.ticket_a = ITTicket.objects.create(
            tenant=self.tenant_a,
            title="Tenant A Ticket",
            description="Private data for A",
            submitted_by=self.user_a
        )
        
        # Create Data for Tenant B
        self.ticket_b = ITTicket.objects.create(
            tenant=self.tenant_b,
            title="Tenant B Ticket",
            description="Private data for B",
            submitted_by=self.user_b
        )

    def test_tenant_a_cannot_see_tenant_b_data(self):
        """
        Verify that when querying records using the tenant filter,
        Tenant A only sees their own data.
        """
        from tracking_app.views import get_tenant_filter
        
        # Simulate Tenant A Request
        tenant_filter_a = get_tenant_filter(self.user_a)
        tickets_a = ITTicket.objects.filter(**tenant_filter_a)
        
        self.assertEqual(tickets_a.count(), 1)
        self.assertEqual(tickets_a.first().title, "Tenant A Ticket")
        self.assertNotIn(self.ticket_b, tickets_a)
        
    def test_tenant_b_cannot_see_tenant_a_data(self):
        """
        Verify that Tenant B only sees their own data.
        """
        from tracking_app.views import get_tenant_filter
        
        # Simulate Tenant B Request
        tenant_filter_b = get_tenant_filter(self.user_b)
        tickets_b = ITTicket.objects.filter(**tenant_filter_b)
        
        self.assertEqual(tickets_b.count(), 1)
        self.assertEqual(tickets_b.first().title, "Tenant B Ticket")
        self.assertNotIn(self.ticket_a, tickets_b)
