from assessment_core.models import Attempt
from decimal import Decimal
from grade_integrity.models import GradeSource, GradeRecord, GradeAuditLog
from iam.models import Tenant


class AutoGrader:
    def grade_attempt(self, attempt_id):
        attempt = Attempt.objects.get(id=attempt_id)
        total_score = Decimal('0.00')
        max_score = Decimal('0.00')

        for response in attempt.responses.all():
            question = response.question
            max_score += question.points

            if question.question_type == 'MCQ':
                selected = response.response_data.get('selected')
                for option in question.options or []:
                    if option.get('text') == selected and option.get('correct'):
                        points = question.points
                        break
                else:
                    points = Decimal('0.00')
            else:
                points = Decimal('0.00')

            response.points_awarded = points
            response.save()
            total_score += points

        attempt.raw_score = total_score
        attempt.max_score = max_score
        attempt.percentage = (total_score / max_score * 100) if max_score > 0 else 0
        attempt.status = 'GRADED'
        attempt.save()

        # Create grade record for auto-grader
        self._create_auto_grade_record(attempt, total_score, max_score)

        return {
            'score': float(total_score),
            'max_score': float(max_score),
            'percentage': float(attempt.percentage)
        }

    def _create_auto_grade_record(self, attempt, score, max_score):
        """Create a grade record for the auto-grader source"""
        try:
            # Get or create tenant for the institution
            institution = attempt.assessment.course.institution
            tenant, created = Tenant.objects.get_or_create(
                name=institution.name,
                defaults={'admin_contact': {'institution_id': str(institution.id)}}
            )

            source, created = GradeSource.objects.get_or_create(
                tenant=tenant,
                name='Auto Grader',
                defaults={
                    'source_type': 'auto_grader',
                    'description': 'Automated grading system'
                }
            )

            # Create grade record
            percentage = (score / max_score * 100) if max_score > 0 else Decimal('0.00')
            grade_record = GradeRecord.objects.create(
                tenant=tenant,
                attempt=attempt,
                source=source,
                score=score,
                max_score=max_score,
                percentage=percentage,
                metadata={'auto_graded': True},
                graded_at=attempt.submitted_at or attempt.started_at
            )

            # Log the grading
            GradeAuditLog.objects.create(
                tenant=tenant,
                action='grade_recorded',
                resource={'record_id': str(grade_record.id), 'attempt_id': str(attempt.id)},
                grade_related_resource={
                    'source': 'auto_grader',
                    'score': str(score),
                    'max_score': str(max_score)
                }
            )

        except Exception as e:
            # Log error but don't fail the grading
            print(f"Error creating grade record: {e}")
            pass
