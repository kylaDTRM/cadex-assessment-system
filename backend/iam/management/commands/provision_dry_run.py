from django.core.management.base import BaseCommand
from django.utils import timezone
from iam.models import Assessment, ExamInstance, IntegrationRecord
from moodle_integration import client as moodle_client
from proctoring import adapter as proctor_adapter


class Command(BaseCommand):
    help = 'Dry-run provision an example assessment (no external calls when --dry-run)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', dest='dry_run', default=True)

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        # Use IAM User model
        from iam.models import User, Tenant
        admin = User.objects.first()
        if not admin:
            tenant = Tenant.objects.first() or Tenant.objects.create(name='default')
            admin = User.objects.create(username='sysadmin', tenant=tenant)

        # Create a simple assessment
        a = Assessment.objects.create(tenant=admin.tenant, title='DR Test Assessment', description='Auto-provision test')
        ver = a.submit_for_review(admin)
        # Simulate approval
        req = ver.approval_requests.first()
        req.add_approval(admin, decision='approve')
        # Move to scheduled
        a._ensure_state_transition('scheduled')
        a.save()

        # Provisioning
        self.stdout.write('Provisioning assessment (dry_run=%s)' % dry_run)
        prov = moodle_client.provision_for_assessment(ver, dry_run=dry_run)
        instance = ExamInstance.objects.create(assessment_version=ver, scheduled_start=timezone.now(), scheduled_end=timezone.now(), moodle_resource_id=prov.get('lti_resource_id'))
        IntegrationRecord.objects.create(source='moodle', payload=prov)

        proc_sid = proctor_adapter.request_session(instance, dry_run=dry_run)
        instance.proctoring_session_id = proc_sid
        instance.state = 'provisioned'
        instance.save()
        IntegrationRecord.objects.create(source='proctoring', payload={'session_id': proc_sid})

        self.stdout.write(self.style.SUCCESS(f'Provisioned exam instance {instance.id}'))
