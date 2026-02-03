from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'grade-sources', views.GradeSourceViewSet)
router.register(r'grade-records', views.GradeRecordViewSet)
router.register(r'grade-conflicts', views.GradeConflictViewSet)
router.register(r'grade-freezes', views.GradeFreezeViewSet)
router.register(r'grade-amendments', views.GradeAmendmentViewSet)
router.register(r'approval-workflows', views.ApprovalWorkflowViewSet)
router.register(r'reconciliation', views.ReconciliationViewSet, basename='reconciliation')

urlpatterns = [
    path('', include(router.urls)),
]
