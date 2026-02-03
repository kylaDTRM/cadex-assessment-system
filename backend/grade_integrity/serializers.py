from rest_framework import serializers
from .models import (
    GradeSource, GradeRecord, GradeConflict, GradeFreeze,
    GradeAmendment, ApprovalWorkflow, ApprovalStep
)


class GradeSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeSource
        fields = '__all__'


class GradeRecordSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    attempt_details = serializers.SerializerMethodField()

    class Meta:
        model = GradeRecord
        fields = '__all__'

    def get_attempt_details(self, obj):
        return {
            'student': obj.attempt.student.username,
            'assessment': obj.attempt.assessment.title,
            'attempt_number': obj.attempt.attempt_number
        }


class GradeConflictSerializer(serializers.ModelSerializer):
    involved_records_details = serializers.SerializerMethodField()

    class Meta:
        model = GradeConflict
        fields = '__all__'

    def get_involved_records_details(self, obj):
        return [{
            'id': record.id,
            'source': record.source.name,
            'score': record.score,
            'graded_at': record.graded_at
        } for record in obj.involved_records.all()]


class GradeFreezeSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)
    frozen_by_name = serializers.CharField(source='frozen_by.username', read_only=True)

    class Meta:
        model = GradeFreeze
        fields = '__all__'


class GradeAmendmentSerializer(serializers.ModelSerializer):
    grade_record_details = serializers.SerializerMethodField()
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = GradeAmendment
        fields = '__all__'

    def get_grade_record_details(self, obj):
        return {
            'attempt': {
                'student': obj.grade_record.attempt.student.username,
                'assessment': obj.grade_record.attempt.assessment.title
            },
            'source': obj.grade_record.source.name,
            'current_score': obj.grade_record.score
        }


class ApprovalStepSerializer(serializers.ModelSerializer):
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = ApprovalStep
        fields = '__all__'


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, read_only=True)
    resource_details = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalWorkflow
        fields = '__all__'

    def get_resource_details(self, obj):
        if obj.workflow_type == 'grade_amendment':
            try:
                amendment = GradeAmendment.objects.get(id=obj.resource_id)
                return {
                    'type': 'amendment',
                    'old_score': amendment.old_score,
                    'new_score': amendment.new_score,
                    'justification': amendment.justification
                }
            except GradeAmendment.DoesNotExist:
                return None
        return None
