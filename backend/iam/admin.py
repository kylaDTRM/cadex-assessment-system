from django.contrib import admin
from .models import Tenant, User, Role, Permission, RolePermission, RoleBinding, DelegatedGrant, EmergencyAccess, AuditLog, RevokedToken


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
