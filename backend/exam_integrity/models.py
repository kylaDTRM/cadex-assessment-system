
import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from assessment_core.models import Attempt
from iam.models import Tenant

User = get_user_model()


class IntegrityEvent(models.Model):
    """
    Raw proctoring signals and integrity events.
    Separated from grade data for privacy and compliance.
    """

    EVENT_TYPES = [
        ('face_not_visible', 'Face Not Visible'),
        ('multiple_faces', 'Multiple Faces Detected'),
        ('tab_switch', 'Tab/Window Switch'),
        ('copy_paste', 'Copy/Paste Detected'),
        ('external_device', 'External Device Detected'),
        ('audio_anomaly', 'Audio Anomaly'),
        ('network_issue', 'Network Connectivity Issue'),
        ('suspicious_behavior', 'Suspicious Behavior'),
        ('system_integrity', 'System Integrity Check'),
        ('custom', 'Custom Event'),
    ]

    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    # Event metadata
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='low')
    timestamp = models.DateTimeField(default=timezone.now)

    # Proctoring context
    proctoring_session_id = models.CharField(max_length=255)
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='integrity_events')

    # Event data
    event_data = models.JSONField(help_text='Raw event data from proctoring system')
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional metadata')

    # Evidence
    screenshot_url = models.URLField(blank=True, null=True)
    video_clip_url = models.URLField(blank=True, null=True)
    audio_clip_url = models.URLField(blank=True, null=True)

    # Processing status
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'attempt', 'event_type']),
            models.Index(fields=['processed', 'severity']),
        ]

    def __str__(self):
        return f"{self.event_type} for {self.attempt} at {self.timestamp}"


class IntegrityIncident(models.Model):
    """
    Escalated incidents that require review.
    Created from patterns of integrity events.
    """

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('escalated', 'Escalated'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    RESOLUTION_CHOICES = [
        ('no_violation', 'No Violation Found'),
        ('minor_violation', 'Minor Violation'),
        ('major_violation', 'Major Violation'),
        ('exam_invalidated', 'Exam Invalidated'),
        ('further_investigation', 'Requires Further Investigation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    # Incident details
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    # Related entities
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='integrity_incidents')
    related_events = models.ManyToManyField(IntegrityEvent, related_name='incidents')

    # Risk assessment
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    risk_level = models.CharField(max_length=20, choices=[
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')
    ], default='low')

    # Incident lifecycle
    created_at = models.DateTimeField(default=timezone.now)
    detected_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Resolution
    resolution = models.CharField(max_length=50, choices=RESOLUTION_CHOICES, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='resolved_incidents')

    # Evidence retention
    evidence_retention_until = models.DateTimeField(null=True, blank=True)
    evidence_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'risk_level']),
            models.Index(fields=['attempt', 'status']),
        ]

    def __str__(self):
        return f"Incident: {self.title} ({self.status})"


class RiskRule(models.Model):
    """
    Rule-based risk scoring configuration.
    """

    RULE_TYPES = [
        ('event_count', 'Event Count Threshold'),
        ('event_pattern', 'Event Pattern Matching'),
        ('severity_weighted', 'Severity Weighted Scoring'),
        ('time_window', 'Time Window Analysis'),
        ('custom', 'Custom Rule'),
    ]

    OPERATORS = [
        ('gt', 'Greater Than'),
        ('gte', 'Greater Than or Equal'),
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('eq', 'Equal'),
        ('contains', 'Contains'),
        ('regex', 'Regex Match'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)

    # Rule conditions
    event_type = models.CharField(max_length=50, choices=IntegrityEvent.EVENT_TYPES, null=True, blank=True)
    operator = models.CharField(max_length=20, choices=OPERATORS)
    threshold_value = models.CharField(max_length=255)  # Can be number, string, or JSON

    # Rule parameters
    parameters = models.JSONField(default=dict, help_text='Additional rule parameters')

    # Scoring
    base_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    score_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.00)

    # Rule status
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)  # Higher priority rules processed first

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-priority', 'name']
        unique_together = ('tenant', 'name')

    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class Evidence(models.Model):
    """
    Evidence files with retention policies.
    """

    EVIDENCE_TYPES = [
        ('screenshot', 'Screenshot'),
        ('video', 'Video Clip'),
        ('audio', 'Audio Clip'),
        ('log', 'System Log'),
        ('network', 'Network Capture'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    # Evidence details
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES)
    filename = models.CharField(max_length=255)
    file_url = models.URLField()
    file_size = models.PositiveIntegerField()  # in bytes

    # Related entities
    incident = models.ForeignKey(IntegrityIncident, on_delete=models.CASCADE, related_name='evidence_files')
    event = models.ForeignKey(IntegrityEvent, null=True, blank=True, on_delete=models.SET_NULL)

    # Retention policy
    retention_policy = models.CharField(max_length=50, default='standard')
    retention_until = models.DateTimeField()
    auto_delete = models.BooleanField(default=True)

    # Metadata
    checksum = models.CharField(max_length=128, blank=True)  # SHA-256
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.evidence_type}: {self.filename}"


class ReviewWorkflow(models.Model):
    """
    Incident review and escalation workflows.
    """

    WORKFLOW_TYPES = [
        ('incident_review', 'Incident Review'),
        ('escalation', 'Escalation'),
        ('appeal', 'Appeal Process'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    workflow_type = models.CharField(max_length=20, choices=WORKFLOW_TYPES)
    incident = models.ForeignKey(IntegrityIncident, on_delete=models.CASCADE, related_name='workflows')

    # Workflow configuration
    required_reviewers = models.JSONField(help_text='List of required reviewer roles/users')
    escalation_rules = models.JSONField(default=dict, help_text='Escalation conditions and actions')

    # Workflow state
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_step = models.CharField(max_length=100, default='initial_review')
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)

    # Results
    decision = models.CharField(max_length=50, null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='workflow_decisions')

    class Meta:
        ordering = ['-created_at']
        unique_together = ('incident', 'workflow_type')

    def __str__(self):
        return f"{self.workflow_type} for {self.incident}"


class ReviewStep(models.Model):
    """
    Individual steps in a review workflow.
    """

    STEP_TYPES = [
        ('review', 'Review'),
        ('approval', 'Approval'),
        ('escalation', 'Escalation'),
        ('notification', 'Notification'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(ReviewWorkflow, on_delete=models.CASCADE, related_name='steps')

    step_name = models.CharField(max_length=100)
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Assignment
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    assigned_role = models.CharField(max_length=100, blank=True)

    # Step configuration
    instructions = models.TextField(blank=True)
    required_actions = models.JSONField(default=list)
    time_limit_hours = models.IntegerField(null=True, blank=True)

    # Results
    completed_at = models.DateTimeField(null=True, blank=True)
    decision = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(blank=True)

    # Ordering
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'step_name']
        unique_together = ('workflow', 'order')

    def __str__(self):
        return f"{self.step_name} ({self.status})"
