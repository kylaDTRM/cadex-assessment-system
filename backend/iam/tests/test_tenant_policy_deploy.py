from django.test import TestCase
from unittest.mock import patch
from iam.models import Tenant, TenantPolicy


class TenantPolicyDeployTest(TestCase):

    @patch('iam.management.commands.deploy_opa_policies.OPAClient')
    def test_deploy_command_pushes_policies(self, mock_opa_client):
        t = Tenant.objects.create(name='Test T')
        TenantPolicy.objects.create(tenant=t, name='policy1', rego='package x\nallow = true')

        # Run command
        from django.core.management import call_command
        call_command('deploy_opa_policies')

        # Ensure push_policy called with expected path and source
        mock_opa_client.push_policy.assert_called()
        args, kwargs = mock_opa_client.push_policy.call_args
        self.assertIn('policy1', args[0])
        self.assertIn('package x', args[1])
