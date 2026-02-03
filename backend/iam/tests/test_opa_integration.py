import unittest
from django.test import TestCase
from django.conf import settings
from iam.opa_client import OPAClient
from iam.models import Tenant, User, AttributePolicy, Permission
from iam.services import PermissionResolver
import time


@unittest.skipUnless(settings.OPA_URL, 'OPA_URL not configured')
class OPAIntegrationTest(TestCase):

    def test_opa_policy_allows(self):
        # push a simple policy that allows grade.write for users in dept 'CS'
        policy = '''package tenant.policies

default allow = false

allow {
    input.user.attrs.dept == "CS"
    input.permission == "grade.write"
}
'''
        # push policy
        OPAClient.push_policy('tenant_policies', policy)

        tenant = Tenant.objects.create(name='OPA University')
        user = User.objects.create(tenant=tenant, username='charlie', attrs={'dept': 'CS'})
        Permission.objects.create(name='grade.write')
        # register an ABAC policy pointing to OPA
        AttributePolicy.objects.create(tenant=tenant, name='opa_grade_policy', policy_type='opa', expression='tenant/policies/allow', effect='allow')

        # OPA may take a brief moment to compile; retry evaluation for a short time
        allowed = False
        for _ in range(10):
            allowed = PermissionResolver.has_permission(user, 'grade.write', resource={})
            if allowed:
                break
            time.sleep(0.5)
        self.assertTrue(allowed)

    def test_opa_policy_denies(self):
        # same policy as above
        # ensure user with different dept is denied
        tenant = Tenant.objects.create(name='OPA University 2')
        user = User.objects.create(tenant=tenant, username='dave', attrs={'dept': 'MATH'})
        Permission.objects.create(name='grade.write')
        AttributePolicy.objects.create(tenant=tenant, name='opa_grade_policy2', policy_type='opa', expression='tenant/policies/allow', effect='allow')

        # No allowed attributes -> should be denied
        denied = PermissionResolver.has_permission(user, 'grade.write', resource={})
        self.assertFalse(denied)
