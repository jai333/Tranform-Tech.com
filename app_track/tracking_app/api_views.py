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

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def global_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return Response({'results': []})

    tenant = request.user.tenant
    if not tenant:
        return Response({'results': []})

    results = []

    leads = Lead.objects.filter(tenant=tenant).filter(
        Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query) | Q(company_name__icontains=query)
    )[:5]
    for l in leads:
        results.append({'type': 'Lead', 'title': l.first_name + ' ' + l.last_name, 'subtitle': l.company_name or '', 'url': '/sales/leads/' + str(l.id) + '/'})

    deals = Deal.objects.filter(tenant=tenant).filter(
        Q(title__icontains=query) | Q(company_name__icontains=query)
    )[:5]
    for d in deals:
        results.append({'type': 'Deal', 'title': d.title, 'subtitle': 'Value: $' + str(d.value), 'url': '/sales/pipeline/'})

    candidates = Candidate.objects.filter(tenant=tenant).filter(
        Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query) | Q(current_job_title__icontains=query)
    )[:5]
    for c in candidates:
        results.append({'type': 'Candidate', 'title': c.first_name + ' ' + c.last_name, 'subtitle': c.current_job_title or '', 'url': '/candidates/' + str(c.id) + '/'})

    tickets = ITTicket.objects.filter(tenant=tenant).filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )[:5]
    for t in tickets:
        results.append({'type': 'IT Ticket', 'title': t.title, 'subtitle': str(t.status) or '', 'url': '/it/tickets/' + str(t.id) + '/'})

    return Response({'results': results})
