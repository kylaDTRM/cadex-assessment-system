
from django.contrib import admin
from .models import (
    IntegrityEvent, IntegrityIncident, RiskRule, Evidence,
    ReviewWorkflow, ReviewStep
)


@admin.register(IntegrityEvent)
class IntegrityEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'severity', 'attempt', 'timestamp', 'processed']
    list_filter = ['event_type', 'severity', 'processed', 'tenant']
    search_fields = ['attempt__student__username', 'proctoring_session_id']
    readonly_fields = ['id', 'timestamp', 'processed_at']
    ordering = ['-timestamp']


@admin.register(IntegrityIncident)
class IntegrityIncidentAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'risk_level', 'attempt', 'created_at']
    list_filter = ['status', 'risk_level', 'resolution', 'tenant']
    search_fields = ['title', 'attempt__student__username', 'description']
    readonly_fields = ['id', 'created_at', 'detected_at', 'resolved_at']
    ordering = ['-created_at']


@admin.register(RiskRule)
class RiskRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'is_active', 'priority', 'tenant']
    list_filter = ['rule_type', 'is_active', 'tenant']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at']
    ordering = ['-priority', 'name']


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ['evidence_type', 'filename', 'incident', 'uploaded_at']
    list_filter = ['evidence_type', 'auto_delete', 'tenant']
    search_fields = ['filename', 'incident__title']
    readonly_fields = ['id', 'uploaded_at']


@admin.register(ReviewWorkflow)
class ReviewWorkflowAdmin(admin.ModelAdmin):
    list_display = ['workflow_type', 'incident', 'status', 'assigned_to', 'created_at']
    list_filter = ['workflow_type', 'status', 'tenant']
    search_fields = ['incident__title']
    readonly_fields = ['id', 'created_at', 'started_at', 'completed_at']


@admin.register(ReviewStep)
class ReviewStepAdmin(admin.ModelAdmin):
    list_display = ['step_name', 'workflow', 'status', 'assigned_to', 'order']
    list_filter = ['step_type', 'status']
    search_fields = ['step_name', 'workflow__incident__title']
    readonly_fields = ['id', 'completed_at']
    ordering = ['workflow', 'order']
