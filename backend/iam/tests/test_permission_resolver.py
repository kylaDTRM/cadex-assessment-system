from django.test import TestCase
from iam.models import Tenant, User, Role, Permission, RolePermission, RoleBinding, DelegatedGrant
from iam.services import PermissionResolver
from django.utils import timezone
from datetime import timedelta


class PermissionResolverTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Test Uni')
        self.user = User.objects.create(tenant=self.tenant, username='alice')
        self.role = Role.objects.create(tenant=self.tenant, name='instructor')
        self.perm = Permission.objects.create(name='grade.write')
        RolePermission.objects.create(role=self.role, permission=self.perm, effect='allow')
        RoleBinding.objects.create(tenant=self.tenant, subject_type='user', subject_id=self.user.id, role=self.role)

    def test_allow_by_role(self):
        self.assertTrue(PermissionResolver.has_permission(self.user, 'grade.write', resource={'id': 'course:101'}))

    def test_denied_by_expired_binding(self):
        RoleBinding.objects.create(tenant=self.tenant, subject_type='user', subject_id=self.user.id, role=self.role, expires_at=timezone.now()-timedelta(days=1))
        self.assertTrue(PermissionResolver.has_permission(self.user, 'grade.write', resource={'id': 'course:101'}))

    def test_delegated_grant(self):
        # Use a different permission
        p2 = Permission.objects.create(name='assessment.create')
        DelegatedGrant.objects.create(tenant=self.tenant, granter=self.user, grantee=self.user, permission=p2, expires_at=timezone.now()+timedelta(days=1))
        self.assertTrue(PermissionResolver.has_permission(self.user, 'assessment.create'))
