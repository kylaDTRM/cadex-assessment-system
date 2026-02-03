from django.test import TestCase
from iam.models import Assessment, ExamInstance, IntegrationRecord
from iam.models import Tenant, User
from django.core.management import call_command
from unittest.mock import patch


class AssessmentLifecycleTests(TestCase):

    def setUp(self):
        self.tenant = Tenant.objects.create(name='T1')
        self.author = User.objects.create(tenant=self.tenant, username='author')
        self.approver = User.objects.create(tenant=self.tenant, username='approver')

    def test_submit_and_approve_quorum(self):
        a = Assessment.objects.create(tenant=self.tenant, title='Test A', description='desc')
        ver = a.submit_for_review(self.author, quorum=1)
        # Ensure an approval request created
        req = ver.approval_requests.first()
        self.assertIsNotNone(req)
        req.add_approval(self.approver, decision='approve')
        req.refresh_from_db()
        a.refresh_from_db()
        self.assertTrue(req.satisfied)
        self.assertEqual(a.state, 'approved')

    @patch('moodle_integration.client.provision_for_assessment')
    @patch('proctoring.adapter.request_session')
    def test_provision_dry_run_command(self, mock_proctor, mock_provision):
        mock_provision.return_value = {'lti_resource_id': 'dry-lti-1', 'grade_item_id': 'dry-grade-1'}
        mock_proctor.return_value = 'dry-proctor-1'
        call_command('provision_dry_run')
        # Ensure IntegrationRecord entries were created
        self.assertTrue(IntegrationRecord.objects.filter(source='moodle').exists())
        self.assertTrue(IntegrationRecord.objects.filter(source='proctoring').exists())
        inst = ExamInstance.objects.first()
        self.assertIsNotNone(inst)
        self.assertEqual(inst.state, 'provisioned')
