from django.core.management.base import BaseCommand
from iam.models import AuditLog
import json

class Command(BaseCommand):
    help = 'Export audit logs as JSON lines for a tenant or all'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=str, help='tenant id')
        parser.add_argument('--outfile', type=str, help='file to write', default='audit_export.jsonl')

    def handle(self, *args, **options):
        qs = AuditLog.objects.all()
        if options.get('tenant'):
            qs = qs.filter(tenant__id=options['tenant'])
        with open(options['outfile'], 'w') as fh:
            for a in qs.order_by('id'):
                obj = {
                    'id': a.id,
                    'tenant': str(a.tenant_id),
                    'actor': str(a.actor_id) if a.actor_id else None,
                    'action': a.action,
                    'resource': a.resource,
                    'prev_hash': a.prev_hash,
                    'hash': a.hash,
                    'created_at': a.created_at.isoformat()
                }
                fh.write(json.dumps(obj) + '\n')
        self.stdout.write(self.style.SUCCESS('Exported audit logs'))
