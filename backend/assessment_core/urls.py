from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssessmentViewSet, AttemptViewSet

router = DefaultRouter()
router.register(r'assessments', AssessmentViewSet)
router.register(r'attempts', AttemptViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
