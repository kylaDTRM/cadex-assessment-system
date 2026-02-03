from django.contrib import admin
from .models import Tenant, User, Role, Permission, RolePermission, RoleBinding, DelegatedGrant, EmergencyAccess, AuditLog, RevokedToken, TenantPolicy


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'tenant', 'email')
    search_fields = ('username', 'email')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tenant', 'builtin')


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'role', 'permission', 'resource_pattern', 'effect')


@admin.register(RoleBinding)
class RoleBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'subject_type', 'subject_id', 'role', 'resource_scope', 'expires_at')


@admin.register(DelegatedGrant)
class DelegatedGrantAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'granter', 'grantee', 'permission', 'expires_at', 'active')


@admin.register(EmergencyAccess)
class EmergencyAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'requester', 'permission', 'expires_at', 'consumed')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'actor', 'action', 'created_at')
    readonly_fields = ('id', 'tenant', 'actor', 'action', 'resource', 'prev_hash', 'hash', 'created_at')


@admin.register(RevokedToken)
class RevokedTokenAdmin(admin.ModelAdmin):
    list_display = ('jti', 'revoked_at')
    readonly_fields = ('jti', 'revoked_at', 'reason')




@admin.register(TenantPolicy)
class TenantPolicyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tenant', 'version', 'last_deployed_at', 'last_deploy_status')
    readonly_fields = ('last_deployed_at', 'last_deploy_status')
    search_fields = ('name', 'tenant__name')
    actions = ['deploy_to_opa']

    def deploy_to_opa(self, request, queryset):
        from iam.opa_client import OPAClient
        from django.utils import timezone
        for policy in queryset:
            path = f"tenant_{policy.tenant.id}_{policy.name}"
            try:
                OPAClient.push_policy(path, policy.rego)
                policy.last_deployed_at = timezone.now()
                policy.last_deploy_status = 'ok'
                policy.save()
                self.message_user(request, f"Deployed {policy.name} -> {path}")
            except Exception as e:
                policy.last_deploy_status = f"error: {str(e)[:200]}"
                policy.save()
                self.message_user(request, f"Failed to deploy {policy.name}: {e}", level='error')
    deploy_to_opa.short_description = 'Deploy selected policies to OPA'
