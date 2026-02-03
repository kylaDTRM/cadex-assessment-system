from rest_framework import viewsets, permissions
from .models import Assessment, Attempt
from .serializers import AssessmentSerializer, AttemptSerializer


class AssessmentViewSet(viewsets.ModelViewSet):
    """API endpoint that allows assessments to be viewed or edited."""
    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class AttemptViewSet(viewsets.ModelViewSet):
    """API endpoint that allows attempts to be viewed or edited."""
    queryset = Attempt.objects.all()
    serializer_class = AttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
