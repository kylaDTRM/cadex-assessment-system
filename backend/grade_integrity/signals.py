from django.db.models.signals import post_save
from django.dispatch import receiver
from assessment_core.models import Attempt
from .services import GradeReconciliationEngine
from .models import GradeRecord, GradeSource, GradeAuditLog
from iam.models import Tenant


@receiver(post_save, sender=Attempt)
def handle_attempt_graded(sender, instance, created, **kwargs):
    """
    Automatically trigger grade reconciliation when an attempt is marked as graded.
    """
    if instance.status == 'GRADED' and not created:
        # Check if we already have a final grade record
        if not GradeRecord.objects.filter(attempt=instance, is_final=True).exists():
            try:
                # Get tenant
                institution = instance.assessment.course.institution
                tenant = Tenant.objects.filter(name=institution.name).first()
                if not tenant:
                    tenant = Tenant.objects.create(
                        name=institution.name,
                        admin_contact={'institution_id': str(institution.id)}
                    )

                # Get or create reconciliation source
                source, _ = GradeSource.objects.get_or_create(
                    tenant=tenant,
                    name='Reconciliation',
                    defaults={
                        'source_type': 'reconciliation',
                        'description': 'Automatic reconciliation on grading'
                    }
                )

                # Run reconciliation
                engine = GradeReconciliationEngine(instance)
                result = engine.reconcile_grades()

                if 'error' not in result:
                    # Create final grade record
                    final_record = GradeRecord.objects.create(
                        tenant=tenant,
                        attempt=instance,
                        source=source,
                        score=result['reconciled_score'],
                        max_score=result['max_score'],
                        percentage=result['percentage'],
                        metadata={
                            'algorithm': result['algorithm'],
                            'confidence': str(result['confidence']),
                            'auto_reconciled': True
                        },
                        is_final=True
                    )

                    # Log the reconciliation
                    GradeAuditLog.objects.create(
                        tenant=tenant,
                        action='grade_recorded',
                        resource={'record_id': str(final_record.id), 'attempt_id': str(instance.id)},
                        grade_related_resource=result
                    )

            except Exception as e:
                # Log error but don't prevent the save
                print(f"Error in automatic reconciliation: {e}")
                pass
