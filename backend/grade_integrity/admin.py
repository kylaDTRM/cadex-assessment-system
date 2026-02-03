from django.contrib import admin

from .models import (
    GradeSource, GradeRecord, GradeConflict, GradeFreeze,
    GradeAmendment, ApprovalWorkflow, ApprovalStep, GradeAuditLog
)


@admin.register(GradeSource)
class GradeSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'tenant', 'is_active']
    list_filter = ['source_type', 'is_active', 'tenant']
    search_fields = ['name', 'description']


@admin.register(GradeRecord)
class GradeRecordAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'source', 'score', 'max_score', 'percentage', 'is_final', 'graded_at']
    list_filter = ['source__source_type', 'is_final', 'tenant']
    search_fields = ['attempt__student__username', 'attempt__assessment__title']
    readonly_fields = ['id', 'graded_at']


@admin.register(GradeConflict)
class GradeConflictAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'conflict_type', 'severity', 'detected_at', 'resolved']
    list_filter = ['conflict_type', 'severity', 'resolved', 'tenant']
    search_fields = ['attempt__student__username', 'description']
    readonly_fields = ['id', 'detected_at']


@admin.register(GradeFreeze)
class GradeFreezeAdmin(admin.ModelAdmin):
    list_display = ['assessment', 'frozen_at', 'frozen_by', 'is_active']
    list_filter = ['is_active', 'tenant']
    search_fields = ['assessment__title', 'justification']
    readonly_fields = ['id', 'frozen_at']


@admin.register(GradeAmendment)
class GradeAmendmentAdmin(admin.ModelAdmin):
    list_display = ['grade_record', 'amendment_type', 'old_score', 'new_score', 'approved', 'requested_at']
    list_filter = ['amendment_type', 'approved', 'tenant']
    search_fields = ['grade_record__attempt__student__username', 'justification']
    readonly_fields = ['id', 'requested_at', 'approved_at']


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = ['workflow_type', 'resource_id', 'status', 'created_at', 'expires_at']
    list_filter = ['workflow_type', 'status', 'tenant']
    search_fields = ['resource_id']
    readonly_fields = ['id', 'created_at']


@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'step_number', 'approver_role', 'approved', 'approved_at']
    list_filter = ['approved', 'approver_role']
    search_fields = ['workflow__resource_id']
    readonly_fields = ['id', 'approved_at']


@admin.register(GradeAuditLog)
class GradeAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'actor', 'action', 'created_at']
    list_filter = ['action_type', 'tenant']
    search_fields = ['actor__username', 'action', 'resource']
    readonly_fields = ['id', 'hash', 'prev_hash', 'created_at']
