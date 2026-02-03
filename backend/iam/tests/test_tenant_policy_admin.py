from django.test import TestCase, RequestFactory
from iam.models import Tenant, TenantPolicy, User
from iam.admin import TenantPolicyAdmin
from unittest.mock import patch


class TenantPolicyAdminTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='T1')
        self.user = User.objects.create(tenant=self.tenant, username='admin')
        self.policy = TenantPolicy.objects.create(tenant=self.tenant, name='p1', rego='package x\nallow = true')
        self.rf = RequestFactory()

    @patch('iam.opa_client.OPAClient')
    def test_deploy_action_calls_opa(self, mock_opa):
        req = self.rf.post('/admin/')
        req.user = self.user
        # Add messages storage to request so admin.message_user works in tests
        # Lightweight messages stub (avoid session middleware in tests)
        class _StubMessages:
            def add(self, level, message, extra_tags=''):
                return None
        setattr(req, '_messages', _StubMessages())
        admin = TenantPolicyAdmin(TenantPolicy, admin_site=None)
        admin.deploy_to_opa(req, TenantPolicy.objects.filter(id=self.policy.id))
        mock_opa.push_policy.assert_called()
