from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from .models import Tenant, ITTicket, Candidate
from .sales_models import Lead, Deal
from .api_serializers import (
    TenantSerializer, UserSerializer, LeadSerializer,
    DealSerializer, ITTicketSerializer, CandidateSerializer
)

User = get_user_model()

class TenantIsolatingViewSet(viewsets.ModelViewSet):
    """Base ViewSet that automatically filters by tenant and assigns tenant on creation."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Strict isolation: Only return objects for the user's tenant
        if not self.request.user.tenant:
            return self.queryset.none()
        return self.queryset.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        # Automatically assign the tenant to the new object
        serializer.save(tenant=self.request.user.tenant)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.tenant:
            return self.queryset.none()
        return self.queryset.filter(tenant=self.request.user.tenant)


class LeadViewSet(TenantIsolatingViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer


class DealViewSet(TenantIsolatingViewSet):
    queryset = Deal.objects.all()
    serializer_class = DealSerializer


class ITTicketViewSet(TenantIsolatingViewSet):
    queryset = ITTicket.objects.all()
    serializer_class = ITTicketSerializer


class CandidateViewSet(TenantIsolatingViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
