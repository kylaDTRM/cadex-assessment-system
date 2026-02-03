
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    IntegrityEvent, IntegrityIncident, RiskRule, Evidence,
    ReviewWorkflow
)
from .serializers import (
    IntegrityEventSerializer, IntegrityIncidentSerializer, RiskRuleSerializer,
    EvidenceSerializer, ReviewWorkflowSerializer, IntegrityEventIngestionSerializer,
    RiskScoreCalculationSerializer, IncidentResolutionSerializer, WorkflowActionSerializer
)
from .services import (
    IntegrityEventIngestionService, RiskScoringService,
    IncidentManagementService, EvidenceRetentionService
)
from iam.models import Tenant


class IntegrityEventViewSet(viewsets.ModelViewSet):
    queryset = IntegrityEvent.objects.all()
    serializer_class = IntegrityEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        tenant_id = self.request.query_params.get('tenant_id')
        attempt_id = self.request.query_params.get('attempt_id')
        processed = self.request.query_params.get('processed')

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if attempt_id:
            queryset = queryset.filter(attempt_id=attempt_id)
        if processed is not None:
            queryset = queryset.filter(processed=processed.lower() == 'true')

        return queryset

    @action(detail=False, methods=['post'])
    def ingest(self, request):
        """Ingest a proctoring event."""
        serializer = IntegrityEventIngestionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get tenant (in real implementation, this would be from authentication)
        tenant = self._get_tenant_from_request(request)

        service = IntegrityEventIngestionService()
        try:
            attempt = None
            if 'attempt_id' in serializer.validated_data:
                from assessment_core.models import Attempt
                attempt = get_object_or_404(Attempt, id=serializer.validated_data['attempt_id'])

            event = service.ingest_event(
                tenant=tenant,
                proctoring_session_id=serializer.validated_data['proctoring_session_id'],
                event_type=serializer.validated_data['event_type'],
                event_data=serializer.validated_data['event_data'],
                attempt=attempt,
                severity=serializer.validated_data.get('severity', 'low'),
                metadata=serializer.validated_data.get('metadata', {})
            )

            return Response(IntegrityEventSerializer(event).data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _get_tenant_from_request(self, request):
        """Get tenant from request - placeholder implementation."""
        # In real implementation, this would be from user authentication/tenant context
        tenant = Tenant.objects.first()
        if not tenant:
            tenant = Tenant.objects.create(name="Default Tenant")
        return tenant


class IntegrityIncidentViewSet(viewsets.ModelViewSet):
    queryset = IntegrityIncident.objects.all()
    serializer_class = IntegrityIncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        tenant_id = self.request.query_params.get('tenant_id')
        status_filter = self.request.query_params.get('status')
        risk_level = self.request.query_params.get('risk_level')

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)

        return queryset

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an incident."""
        incident = self.get_object()
        serializer = IncidentResolutionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = IncidentManagementService(incident.tenant)
        resolved_incident = service.resolve_incident(
            incident=incident,
            resolution=serializer.validated_data['resolution'],
            notes=serializer.validated_data['resolution_notes'],
            resolved_by=request.user
        )

        # Set evidence retention
        retention_service = EvidenceRetentionService(incident.tenant)
        retention_service.set_retention_policy(
            incident,
            serializer.validated_data.get('evidence_retention_policy', 'standard')
        )

        return Response(IntegrityIncidentSerializer(resolved_incident).data)

    @action(detail=True, methods=['post'])
    def calculate_risk(self, request, pk=None):
        """Calculate risk score for an incident's attempt."""
        incident = self.get_object()
        serializer = RiskScoreCalculationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = RiskScoringService(incident.tenant)
        risk_data = service.calculate_risk_score(
            attempt=incident.attempt,
            time_window_hours=serializer.validated_data.get('time_window_hours', 24)
        )

        return Response(risk_data)


class RiskRuleViewSet(viewsets.ModelViewSet):
    queryset = RiskRule.objects.all()
    serializer_class = RiskRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        tenant_id = self.request.query_params.get('tenant_id')
        is_active = self.request.query_params.get('is_active')

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        # Set tenant from request context
        tenant = self._get_tenant_from_request(self.request)
        serializer.save(tenant=tenant)

    def _get_tenant_from_request(self, request):
        """Get tenant from request - placeholder implementation."""
        tenant = Tenant.objects.first()
        if not tenant:
            tenant = Tenant.objects.create(name="Default Tenant")
        return tenant


class EvidenceViewSet(viewsets.ModelViewSet):
    queryset = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        tenant_id = self.request.query_params.get('tenant_id')
        incident_id = self.request.query_params.get('incident_id')

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if incident_id:
            queryset = queryset.filter(incident_id=incident_id)

        return queryset

    @action(detail=False, methods=['post'])
    def cleanup_expired(self, request):
        """Clean up expired evidence files."""
        tenant = self._get_tenant_from_request(request)
        service = EvidenceRetentionService(tenant)
        deleted_count = service.cleanup_expired_evidence()

        return Response({'deleted_count': deleted_count})

    def _get_tenant_from_request(self, request):
        """Get tenant from request - placeholder implementation."""
        tenant = Tenant.objects.first()
        if not tenant:
            tenant = Tenant.objects.create(name="Default Tenant")
        return tenant


class ReviewWorkflowViewSet(viewsets.ModelViewSet):
    queryset = ReviewWorkflow.objects.all()
    serializer_class = ReviewWorkflowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        tenant_id = self.request.query_params.get('tenant_id')
        status_filter = self.request.query_params.get('status')
        workflow_type = self.request.query_params.get('workflow_type')

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if workflow_type:
            queryset = queryset.filter(workflow_type=workflow_type)

        return queryset

    @action(detail=True, methods=['post'])
    def perform_action(self, request, pk=None):
        """Perform an action on a workflow."""
        workflow = self.get_object()
        serializer = WorkflowActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        decision = serializer.validated_data.get('decision')

        if action == 'start':
            workflow.status = 'in_progress'
            workflow.started_at = timezone.now()
            workflow.assigned_to = request.user
            workflow.save()

        elif action == 'complete':
            workflow.status = 'completed'
            workflow.completed_at = timezone.now()
            workflow.decision = decision
            workflow.decision_notes = notes
            workflow.decided_by = request.user
            workflow.save()

        elif action == 'assign':
            assign_to_id = serializer.validated_data.get('assign_to_user_id')
            if assign_to_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                workflow.assigned_to = get_object_or_404(User, id=assign_to_id)
                workflow.save()

        return Response(ReviewWorkflowSerializer(workflow).data)
