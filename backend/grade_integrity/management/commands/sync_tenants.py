from django.core.management.base import BaseCommand
from assessment_core.models import Institution
from iam.models import Tenant


class Command(BaseCommand):
    help = 'Sync institutions to tenants for grade integrity system'

    def handle(self, *args, **options):
        institutions = Institution.objects.all()
        created_count = 0
        updated_count = 0

        for institution in institutions:
            tenant, created = Tenant.objects.get_or_create(
                name=institution.name,
                defaults={
                    'admin_contact': {
                        'institution_id': str(institution.id),
                        'code': institution.code
                    }
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created tenant: {tenant.name}')
                )
            else:
                updated_count += 1
                # Update admin_contact if needed
                if not tenant.admin_contact or 'institution_id' not in tenant.admin_contact:
                    tenant.admin_contact = tenant.admin_contact or {}
                    tenant.admin_contact['institution_id'] = str(institution.id)
                    tenant.admin_contact['code'] = institution.code
                    tenant.save()
                    self.stdout.write(
                        self.style.WARNING(f'Updated tenant: {tenant.name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Sync complete: {created_count} created, {updated_count} updated'
            )
        )
