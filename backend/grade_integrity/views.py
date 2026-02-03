
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import (
    GradeSource, GradeRecord, GradeConflict, GradeFreeze,
    GradeAmendment, ApprovalWorkflow, GradeAuditLog
)
from .serializers import (
    GradeSourceSerializer, GradeRecordSerializer, GradeConflictSerializer,
    GradeFreezeSerializer, GradeAmendmentSerializer, ApprovalWorkflowSerializer
)
from .services import GradeReconciliationEngine, ApprovalWorkflowEngine, GradingCompletionService
from assessment_core.models import Attempt
from django.utils import timezone


class GradeSourceViewSet(viewsets.ModelViewSet):
    queryset = GradeSource.objects.all()
    serializer_class = GradeSourceSerializer

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return self.queryset.filter(tenant_id=tenant_id)
        return self.queryset


class GradeRecordViewSet(viewsets.ModelViewSet):
    queryset = GradeRecord.objects.all()
    serializer_class = GradeRecordSerializer

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        attempt_id = self.request.query_params.get('attempt_id')
        queryset = self.queryset
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if attempt_id:
            queryset = queryset.filter(attempt_id=attempt_id)
        return queryset


class GradeConflictViewSet(viewsets.ModelViewSet):
    queryset = GradeConflict.objects.all()
    serializer_class = GradeConflictSerializer

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        conflict = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')

        conflict.resolved = True
        conflict.resolved_at = timezone.now()
        conflict.resolution_notes = resolution_notes
        conflict.save()

        # Log the resolution
        GradeAuditLog.objects.create(
            tenant=conflict.tenant,
            actor=request.user,
            action='conflict_resolved',
            resource={'conflict_id': str(conflict.id)},
            grade_related_resource={'resolution_notes': resolution_notes}
        )

        return Response({'status': 'resolved'})


class GradeFreezeViewSet(viewsets.ModelViewSet):
    queryset = GradeFreeze.objects.all()
    serializer_class = GradeFreezeSerializer

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return self.queryset.filter(tenant_id=tenant_id)
        return self.queryset

    def perform_create(self, serializer):
        freeze = serializer.save()
        # Log the freeze
        GradeAuditLog.objects.create(
            tenant=freeze.tenant,
            actor=self.request.user,
            action='grades_frozen',
            resource={'freeze_id': str(freeze.id), 'assessment_id': str(freeze.assessment.id)},
            grade_related_resource={'justification': freeze.justification}
        )


class GradeAmendmentViewSet(viewsets.ModelViewSet):
    queryset = GradeAmendment.objects.all()
    serializer_class = GradeAmendmentSerializer

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return self.queryset.filter(tenant_id=tenant_id)
        return self.queryset

    def perform_create(self, serializer):
        amendment = serializer.save()
        # Create approval workflow
        engine = ApprovalWorkflowEngine(amendment.tenant)
        engine.create_amendment_workflow(amendment)

        # Log the amendment request
        GradeAuditLog.objects.create(
            tenant=amendment.tenant,
            actor=self.request.user,
            action='amendment_requested',
            resource={'amendment_id': str(amendment.id), 'grade_record_id': str(amendment.grade_record.id)},
            grade_related_resource={
                'old_score': str(amendment.old_score),
                'new_score': str(amendment.new_score),
                'justification': amendment.justification
            }
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    queryset = ApprovalWorkflow.objects.all()
    serializer_class = ApprovalWorkflowSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        workflow = self.get_object()
        decision = request.data.get('decision', 'approve')
        comments = request.data.get('comments', '')

        engine = ApprovalWorkflowEngine(workflow.tenant)
        completed = engine.process_approval(workflow, request.user, decision, comments)

        # Log the approval
        GradeAuditLog.objects.create(
            tenant=workflow.tenant,
            actor=request.user,
            action='workflow_completed' if completed else 'workflow_started',
            resource={'workflow_id': str(workflow.id), 'decision': decision},
            grade_related_resource={'comments': comments}
        )

        return Response({'status': 'processed', 'completed': completed})


class ReconciliationViewSet(viewsets.ViewSet):
    """
    ViewSet for grade reconciliation operations.
    """

    @action(detail=False, methods=['post'])
    def reconcile_attempt(self, request):
        attempt_id = request.data.get('attempt_id')
        algorithm = request.data.get('algorithm', 'weighted_average')

        if not attempt_id:
            return Response({'error': 'attempt_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attempt = Attempt.objects.get(id=attempt_id)
        except Attempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        engine = GradeReconciliationEngine(attempt)
        result = engine.reconcile_grades(algorithm)

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        # Create final grade record if reconciliation successful
        tenant = attempt.assessment.course.institution  # Assuming tenant from institution
        final_record = GradeRecord.objects.create(
            tenant=tenant,
            attempt=attempt,
            source=get_object_or_404(GradeSource, name='Reconciliation', tenant=tenant),
            score=result['reconciled_score'],
            max_score=result['max_score'],
            percentage=result['percentage'],
            metadata={'algorithm': algorithm, 'confidence': str(result['confidence'])},
            graded_by=request.user,
            is_final=True
        )

        # Log the reconciliation
        GradeAuditLog.objects.create(
            tenant=tenant,
            actor=request.user,
            action='grade_recorded',
            resource={'record_id': str(final_record.id), 'attempt_id': str(attempt.id)},
            grade_related_resource=result
        )

        return Response({
            'reconciled_grade': GradeRecordSerializer(final_record).data,
            'reconciliation_details': result
        })

    @action(detail=False, methods=['post'])
    def detect_conflicts(self, request):
        attempt_id = request.data.get('attempt_id')

        if not attempt_id:
            return Response({'error': 'attempt_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            attempt = Attempt.objects.get(id=attempt_id)
        except Attempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        engine = GradeReconciliationEngine(attempt)
        conflicts_data = engine.detect_conflicts()

        # Save conflicts to database
        saved_conflicts = []
        for conflict, involved_records in conflicts_data:
            conflict.save()
            conflict.involved_records.set(involved_records)
            saved_conflicts.append(conflict)

            # Log conflict detection
            GradeAuditLog.objects.create(
                tenant=conflict.tenant,
                actor=request.user,
                action='conflict_detected',
                resource={'conflict_id': str(conflict.id), 'attempt_id': str(attempt.id)},
                grade_related_resource={'conflict_type': conflict.conflict_type}
            )

            # Log conflict detection
            GradeAuditLog.objects.create(
                tenant=conflict.tenant,
                actor=request.user,
                action='conflict_detected',
                resource={'conflict_id': str(conflict.id), 'attempt_id': str(attempt.id)},
                grade_related_resource={'conflict_type': conflict.conflict_type}
            )

        return Response({
            'conflicts': GradeConflictSerializer(saved_conflicts, many=True).data
        })

    @action(detail=False, methods=['post'])
    def complete_grading(self, request):
        assessment_id = request.data.get('assessment_id')

        if not assessment_id:
            return Response({'error': 'assessment_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Import here to avoid circular imports
            from assessment_core.models import Assessment
            assessment = Assessment.objects.get(id=assessment_id)
        except Assessment.DoesNotExist:
            return Response({'error': 'Assessment not found'}, status=status.HTTP_404_NOT_FOUND)

        service = GradingCompletionService()
        service.complete_grading_for_assessment(assessment)

        return Response({'status': 'grading completion processed'})
