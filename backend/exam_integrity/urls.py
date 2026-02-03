from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'events', views.IntegrityEventViewSet)
router.register(r'incidents', views.IntegrityIncidentViewSet)
router.register(r'risk-rules', views.RiskRuleViewSet)
router.register(r'evidence', views.EvidenceViewSet)
router.register(r'workflows', views.ReviewWorkflowViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
