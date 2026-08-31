from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import api_views

router = DefaultRouter()
router.register(r'users', api_views.UserViewSet, basename='api-user')
router.register(r'leads', api_views.LeadViewSet, basename='api-lead')
router.register(r'deals', api_views.DealViewSet, basename='api-deal')
router.register(r'tickets', api_views.ITTicketViewSet, basename='api-ticket')
router.register(r'candidates', api_views.CandidateViewSet, basename='api-candidate')

urlpatterns = [
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    path('', include(router.urls)),
]
