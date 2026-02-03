from django.db import models

import uuid
from django.utils import timezone
from assessment_core.models import Attempt, User
from iam.models import Tenant, AuditLog


class GradeSource(models.Model):
    """Represents a source of grades (e.g., auto-grader, manual review, etc.)"""
    SOURCE_TYPES = [
        ('auto_grader', 'Auto Grader'),
        ('manual', 'Manual Grading'),
        ('external', 'External System'),
        ('reconciliation', 'Reconciliation Override'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.source_type})"


class GradeRecord(models.Model):
    """Individual grade record from a source"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='grade_records')
    source = models.ForeignKey(GradeSource, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    metadata = models.JSONField(default=dict, blank=True)  # Additional grading info
    graded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    graded_at = models.DateTimeField(default=timezone.now)
    is_final = models.BooleanField(default=False)  # Whether this is the reconciled final grade

    class Meta:
        unique_together = ('attempt', 'source')

    def __str__(self):
        return f"Grade for {self.attempt} from {self.source}: {self.score}/{self.max_score}"


class GradeConflict(models.Model):
    """Detected conflicts between grade records"""
    CONFLICT_TYPES = [
        ('score_discrepancy', 'Score Discrepancy'),
        ('source_conflict', 'Source Conflict'),
        ('anomaly', 'Statistical Anomaly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE)
    conflict_type = models.CharField(max_length=20, choices=CONFLICT_TYPES)
    description = models.TextField()
    involved_records = models.ManyToManyField(GradeRecord, related_name='conflicts')
    severity = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])
    detected_at = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Conflict for {self.attempt}: {self.conflict_type}"


class GradeFreeze(models.Model):
    """Freezing of grades for an assessment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    assessment = models.ForeignKey('assessment_core.Assessment', on_delete=models.CASCADE)
    frozen_at = models.DateTimeField(default=timezone.now)
    frozen_by = models.ForeignKey(User, on_delete=models.CASCADE)
    justification = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)  # Can be unfrozen

    def __str__(self):
        return f"Freeze for {self.assessment} at {self.frozen_at}"


class GradeAmendment(models.Model):
    """Amendments to grades after freeze"""
    AMENDMENT_TYPES = [
        ('correction', 'Correction'),
        ('appeal', 'Appeal'),
        ('administrative', 'Administrative'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    grade_record = models.ForeignKey(GradeRecord, on_delete=models.CASCADE, related_name='amendments')
    amendment_type = models.CharField(max_length=20, choices=AMENDMENT_TYPES)
    old_score = models.DecimalField(max_digits=5, decimal_places=2)
    new_score = models.DecimalField(max_digits=5, decimal_places=2)
    justification = models.TextField()
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='amendment_requests')
    requested_at = models.DateTimeField(default=timezone.now)
    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='amendment_approvals')

    def __str__(self):
        return f"Amendment for {self.grade_record}: {self.old_score} -> {self.new_score}"


class ApprovalWorkflow(models.Model):
    """Approval workflow for amendments"""
    WORKFLOW_TYPES = [
        ('grade_amendment', 'Grade Amendment'),
        ('freeze_override', 'Freeze Override'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    workflow_type = models.CharField(max_length=20, choices=WORKFLOW_TYPES)
    resource_id = models.UUIDField()  # ID of the resource (amendment, freeze, etc.)
    required_approvers = models.JSONField()  # List of role/user IDs that need to approve
    current_step = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ])
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.workflow_type} workflow for {self.resource_id}"


class ApprovalStep(models.Model):
    """Individual steps in an approval workflow"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.CASCADE, related_name='steps')
    step_number = models.IntegerField()
    approver_role = models.CharField(max_length=255)  # Role name or user ID
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        unique_together = ('workflow', 'step_number')

    def __str__(self):
        return f"Step {self.step_number} for {self.workflow}"


# Extend the existing AuditLog for grade-specific actions
class GradeAuditLog(AuditLog):
    """Specialized audit log for grade-related actions"""
    ACTION_TYPES = [
        ('grade_recorded', 'Grade Recorded'),
        ('conflict_detected', 'Conflict Detected'),
        ('conflict_resolved', 'Conflict Resolved'),
        ('grades_frozen', 'Grades Frozen'),
        ('amendment_requested', 'Amendment Requested'),
        ('amendment_approved', 'Amendment Approved'),
        ('workflow_started', 'Workflow Started'),
        ('workflow_completed', 'Workflow Completed'),
    ]

    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    grade_related_resource = models.JSONField(null=True, blank=True)  # Additional grade-specific data

    class Meta:
        db_table = 'grade_audit_log'
