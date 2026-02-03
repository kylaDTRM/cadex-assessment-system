from django.core.management.base import BaseCommand
from django.utils import timezone
from iam.models import TenantPolicy
from iam.opa_client import OPAClient


class Command(BaseCommand):
    help = 'Deploy all TenantPolicy objects to configured OPA instance'

    def handle(self, *args, **options):
        base = OPAClient._base_url()
        if not base:
            self.stderr.write('OPA_URL not configured; aborting')
            return

        policies = TenantPolicy.objects.select_related('tenant').all()
        count = 0
        for p in policies:
            path = f"tenant_{p.tenant.id}_{p.name}"
            try:
                OPAClient.push_policy(path, p.rego)
                p.last_deployed_at = timezone.now()
                p.last_deploy_status = 'ok'
                p.save()
                self.stdout.write(self.style.SUCCESS(f"Deployed {p.name} for tenant {p.tenant.name} -> {path}"))
                count += 1
            except Exception as e:
                p.last_deploy_status = f"error: {str(e)[:200]}"
                p.save()
                self.stderr.write(self.style.ERROR(f"Failed to deploy {p.name} for tenant {p.tenant.name}: {e}"))
        self.stdout.write(f"Processed {count} policies")
