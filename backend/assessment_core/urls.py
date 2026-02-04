from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssessmentViewSet, AttemptViewSet
from .sync_views import SyncAttemptView, SyncChangesView, SyncAckView

router = DefaultRouter()
router.register(r'assessments', AssessmentViewSet)
router.register(r'attempts', AttemptViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # Offline sync endpoints
    path('sync/attempts/', SyncAttemptView.as_view(), name='sync-attempts'),
    path('sync/changes/', SyncChangesView.as_view(), name='sync-changes'),
    path('sync/ack/', SyncAckView.as_view(), name='sync-ack'),
]
