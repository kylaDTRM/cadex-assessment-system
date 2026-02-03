from rest_framework import serializers
from .models import (
    IntegrityEvent, IntegrityIncident, RiskRule, Evidence,
    ReviewWorkflow, ReviewStep
)


class IntegrityEventSerializer(serializers.ModelSerializer):
    attempt_details = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = IntegrityEvent
        fields = '__all__'
        read_only_fields = ['id', 'processed', 'processed_at']

    def get_attempt_details(self, obj):
        return {
            'student': obj.attempt.student.username,
            'assessment': obj.attempt.assessment.title,
            'attempt_number': obj.attempt.attempt_number
        }


class IntegrityIncidentSerializer(serializers.ModelSerializer):
    attempt_details = serializers.SerializerMethodField()
    related_events_count = serializers.SerializerMethodField()
    evidence_count = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = IntegrityIncident
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'detected_at']

    def get_attempt_details(self, obj):
        return {
            'student': obj.attempt.student.username,
            'assessment': obj.attempt.assessment.title,
            'student_id': obj.attempt.student.id
        }

    def get_related_events_count(self, obj):
        return obj.related_events.count()

    def get_evidence_count(self, obj):
        return obj.evidence_files.count()


class RiskRuleSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = RiskRule
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class EvidenceSerializer(serializers.ModelSerializer):
    incident_title = serializers.CharField(source='incident.title', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = Evidence
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_at']


class ReviewStepSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)

    class Meta:
        model = ReviewStep
        fields = '__all__'
        read_only_fields = ['id', 'completed_at']


class ReviewWorkflowSerializer(serializers.ModelSerializer):
    incident_title = serializers.CharField(source='incident.title', read_only=True)
    steps = ReviewStepSerializer(many=True, read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    decided_by_name = serializers.CharField(source='decided_by.username', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = ReviewWorkflow
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']


class IntegrityEventIngestionSerializer(serializers.Serializer):
    """Serializer for ingesting proctoring events."""
    proctoring_session_id = serializers.CharField(max_length=255)
    event_type = serializers.ChoiceField(choices=IntegrityEvent.EVENT_TYPES)
    severity = serializers.ChoiceField(choices=IntegrityEvent.SEVERITY_LEVELS, default='low')
    event_data = serializers.JSONField()
    metadata = serializers.JSONField(required=False, default=dict)
    attempt_id = serializers.UUIDField(required=False)  # Optional, can be inferred from session


class RiskScoreCalculationSerializer(serializers.Serializer):
    """Serializer for risk score calculation requests."""
    attempt_id = serializers.UUIDField()
    time_window_hours = serializers.IntegerField(default=24, min_value=1, max_value=168)


class IncidentResolutionSerializer(serializers.Serializer):
    """Serializer for incident resolution."""
    resolution = serializers.ChoiceField(choices=IntegrityIncident.RESOLUTION_CHOICES)
    resolution_notes = serializers.CharField(max_length=1000)
    evidence_retention_policy = serializers.ChoiceField(
        choices=['minimal', 'standard', 'extended', 'permanent'],
        default='standard'
    )


class WorkflowActionSerializer(serializers.Serializer):
    """Serializer for workflow actions."""
    action = serializers.ChoiceField(choices=['start', 'complete', 'escalate', 'assign'])
    notes = serializers.CharField(max_length=500, required=False)
    decision = serializers.CharField(max_length=50, required=False)
    assign_to_user_id = serializers.UUIDField(required=False)
