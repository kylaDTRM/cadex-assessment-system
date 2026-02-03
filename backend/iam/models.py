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
