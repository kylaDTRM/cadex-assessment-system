import uuid
from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    admin_contact = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.name


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    moodle_userid = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    attrs = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.username} ({self.tenant})"


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    builtin = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.tenant})"


class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    EFFECT_CHOICES = [('allow', 'allow'), ('deny', 'deny')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    resource_pattern = models.CharField(max_length=512, null=True, blank=True)
    effect = models.CharField(max_length=10, choices=EFFECT_CHOICES, default='allow')


class RoleBinding(models.Model):
    SUBJECT_CHOICES = [('user', 'user'), ('group', 'group')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    subject_type = models.CharField(max_length=10, choices=SUBJECT_CHOICES)
    subject_id = models.UUIDField()  # user.id or group.id
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    resource_scope = models.CharField(max_length=512, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class AttributePolicy(models.Model):
    EFFECT_CHOICES = [('allow', 'allow'), ('deny', 'deny')]
    POLICY_TYPES = [('simple', 'simple'), ('opa', 'opa')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    policy_type = models.CharField(max_length=10, choices=POLICY_TYPES, default='simple')
    expression = models.TextField()  # interpreted by evaluator
    effect = models.CharField(max_length=10, choices=EFFECT_CHOICES, default='allow')
    created_at = models.DateTimeField(default=timezone.now)


class DelegatedGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    granter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted_delegations')
    grantee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_delegations')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    resource_scope = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    justification = models.TextField(blank=True)
    active = models.BooleanField(default=True)


class TenantPolicy(models.Model):
    """A per-tenant Rego policy source managed in the application and deployable to OPA."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    rego = models.TextField(help_text='Rego source for OPA')
    version = models.CharField(max_length=64, null=True, blank=True)
    last_deployed_at = models.DateTimeField(null=True, blank=True)
    last_deploy_status = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (('tenant', 'name'),)

    def __str__(self):
        return f"{self.name} ({self.tenant})"


# ---------------- Assessment lifecycle models ----------------
class Assessment(models.Model):
    STATE_CHOICES = [
        ('draft', 'Draft'),
        ('in_review', 'InReview'),
        ('approved', 'Approved'),
        ('scheduled', 'Scheduled'),
        ('provisioned', 'Provisioned'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('grading', 'Grading'),
        ('graded', 'Graded'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    description = models.TextField(blank=True)
    current_version = models.ForeignKey('AssessmentVersion', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default='draft')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.title} ({self.state})"

    def submit_for_review(self, author, quorum=1, expiry_seconds=0):
        if self.state != 'draft':
            raise ValueError('Can only submit from draft')
        ver_num = (self.versions.aggregate(models.Max('version_number'))['version_number__max'] or 0) + 1
        ver = AssessmentVersion.objects.create(assessment=self, version_number=ver_num, content_snapshot=self._content_blob(), author=author)
        self.current_version = ver
        self.state = 'in_review'
        self.save()
        ApprovalRequest.create_for_version(ver, quorum=quorum, expiry_seconds=expiry_seconds)
        return ver

    def _content_blob(self):
        return {'title': self.title, 'description': self.description}

    def _ensure_state_transition(self, new_state):
        allowed = {
            'draft': ['in_review'],
            'in_review': ['approved', 'draft'],
            'approved': ['scheduled'],
            'scheduled': ['provisioned'],
            'provisioned': ['active', 'failed'],
            'active': ['completed', 'failed'],
            'completed': ['grading'],
            'grading': ['graded', 'failed'],
            'graded': ['published'],
        }
        if self.state == new_state:
            return
        if self.state not in allowed or new_state not in allowed[self.state]:
            raise ValueError(f'Illegal transition {self.state} -> {new_state}')
        self.state = new_state
        self.save()


class AssessmentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField(default=1)
    content_snapshot = models.JSONField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    hash = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        unique_together = (('assessment', 'version_number'),)


class ApprovalRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(AssessmentVersion, on_delete=models.CASCADE, related_name='approval_requests')
    required_quorum = models.IntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    satisfied = models.BooleanField(default=False)

    @staticmethod
    def create_for_version(version, quorum=1, expiry_seconds=0):
        expires = None
        if expiry_seconds:
            expires = timezone.now() + timezone.timedelta(seconds=expiry_seconds)
        return ApprovalRequest.objects.create(version=version, required_quorum=quorum, expires_at=expires)

    def add_approval(self, approver, decision='approve'):
        if self.expires_at and timezone.now() > self.expires_at:
            raise ValueError('Approval expired')
        Approval.objects.create(request=self, approver=approver, decision=decision)
        approves = self.approvals.filter(decision='approve').count()
        if approves >= self.required_quorum:
            self.satisfied = True
            self.save()
            # automatically transition assessment
            ass = self.version.assessment
            ass._ensure_state_transition('approved')
            ass.save()


class Approval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    decision = models.CharField(max_length=32, choices=[('approve', 'approve'), ('reject', 'reject')], default='approve')
    created_at = models.DateTimeField(default=timezone.now)


class AssessmentLock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='locks')
    lock_type = models.CharField(max_length=32)
    owner = models.CharField(max_length=255)
    acquired_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)


class ExamInstance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment_version = models.ForeignKey(AssessmentVersion, on_delete=models.CASCADE)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=32, default='scheduled')
    proctoring_session_id = models.CharField(max_length=255, null=True, blank=True)
    moodle_resource_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class ExamSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam_instance = models.ForeignKey(ExamInstance, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=32, default='started')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)


class IntegrationRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=64)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class EmergencyAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_requests')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    resource_scope = models.CharField(max_length=512, null=True, blank=True)
    justification = models.TextField()
    approved_by = models.UUIDField(null=True, blank=True)
    approval_method = models.CharField(max_length=10, choices=[('auto', 'auto'), ('manual', 'manual')], default='manual')
    start_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)


class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=255)
    resource = models.JSONField(null=True, blank=True)
    prev_hash = models.CharField(max_length=128, null=True, blank=True)
    hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)


class RevokedToken(models.Model):
    jti = models.CharField(max_length=255, primary_key=True)
    revoked_at = models.DateTimeField(default=timezone.now)
    reason = models.TextField(null=True, blank=True)
