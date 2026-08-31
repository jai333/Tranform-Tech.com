from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Tenant, ITTicket, ITAsset, Candidate
from .sales_models import Lead, Deal, Account

User = get_user_model()

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'domain', 'primary_color', 'logo_url', 'portal_domain']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'can_view_sales', 'can_view_ats', 'can_view_it', 'can_view_executive']

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']

class DealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deal
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']

class ITTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = ITTicket
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']
