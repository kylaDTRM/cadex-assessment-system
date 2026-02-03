from decimal import Decimal, ROUND_HALF_UP
from statistics import mean, stdev
from typing import List, Dict, Tuple
from .models import GradeRecord, GradeConflict, GradeSource, ApprovalWorkflow, ApprovalStep, GradeAmendment, GradeFreeze
from django.utils import timezone
from iam.models import User
from assessment_core.models import Attempt


class GradingCompletionService:
    """
    Service to handle grading completion and trigger reconciliation.
    """

    def complete_grading_for_assessment(self, assessment):
        """
        Called when grading is complete for an assessment.
        Triggers reconciliation for all attempts.
        """
        attempts = Attempt.objects.filter(assessment=assessment, status='GRADED')

        for attempt in attempts:
            self._reconcile_attempt_grades(attempt)

        # Optionally freeze grades after reconciliation
        # self._freeze_assessment_grades(assessment)

    def _reconcile_attempt_grades(self, attempt):
        """
        Reconcile grades for a single attempt.
        """
        engine = GradeReconciliationEngine(attempt)
        result = engine.reconcile_grades()

        if 'error' not in result:
            # Create final reconciled grade record
            tenant = self._get_tenant_for_attempt(attempt)
            if tenant:
                source, _ = GradeSource.objects.get_or_create(
                    tenant=tenant,
                    name='Reconciliation',
                    defaults={
                        'source_type': 'reconciliation',
                        'description': 'Final reconciled grade'
                    }
                )

                final_record = GradeRecord.objects.create(
                    tenant=tenant,
                    attempt=attempt,
                    source=source,
                    score=result['reconciled_score'],
                    max_score=result['max_score'],
                    percentage=result['percentage'],
                    metadata={'algorithm': result['algorithm'], 'confidence': str(result['confidence'])},
                    is_final=True
                )

                # Update attempt with final grade
                attempt.raw_score = final_record.score
                attempt.max_score = final_record.max_score
                attempt.percentage = final_record.percentage
                attempt.save()

    def _get_tenant_for_attempt(self, attempt):
        """
        Get tenant for an attempt based on institution.
        """
        from iam.models import Tenant
        institution = attempt.assessment.course.institution
        try:
            return Tenant.objects.get(name=institution.name)
        except Tenant.DoesNotExist:
            # Create tenant if it doesn't exist
            return Tenant.objects.create(
                name=institution.name,
                admin_contact={'institution_id': str(institution.id)}
            )

    def _freeze_assessment_grades(self, assessment):
        """
        Freeze grades for an assessment after reconciliation.
        """
        tenant = self._get_tenant_for_assessment(assessment)
        if tenant:
            GradeFreeze.objects.create(
                tenant=tenant,
                assessment=assessment,
                justification='Automatic freeze after grading completion'
            )

    def _get_tenant_for_assessment(self, assessment):
        """
        Get tenant for an assessment.
        """
        from iam.models import Tenant
        institution = assessment.course.institution
        try:
            return Tenant.objects.get(name=institution.name)
        except Tenant.DoesNotExist:
            return Tenant.objects.create(
                name=institution.name,
                admin_contact={'institution_id': str(institution.id)}
            )


class GradeReconciliationEngine:
    """
    Engine for reconciling grades from multiple sources.
    Implements various algorithms for conflict detection and resolution.
    """

    def __init__(self, attempt):
        self.attempt = attempt
        self.grade_records = GradeRecord.objects.filter(attempt=attempt, source__is_active=True)

    def detect_conflicts(self) -> List[Tuple[GradeConflict, List[GradeRecord]]]:
        """
        Detect conflicts and anomalies in grade records.
        Returns a list of tuples: (conflict, involved_records)
        """
        conflicts = []

        if len(self.grade_records) < 2:
            return conflicts  # No conflicts possible with 0 or 1 record

        # Check for score discrepancies
        scores = [float(record.score) for record in self.grade_records]
        max_score = float(self.grade_records[0].max_score)  # Assume all have same max_score

        if len(set(scores)) > 1:  # Different scores
            std_dev = stdev(scores) if len(scores) > 1 else 0
            if std_dev > 0.1 * max_score:  # More than 10% variation
                conflict = GradeConflict(
                    tenant=self.grade_records[0].tenant,  # Get tenant from grade records
                    attempt=self.attempt,
                    conflict_type='score_discrepancy',
                    description=f"Score variation detected: std_dev={std_dev:.2f}, range=[{min(scores):.2f}, {max(scores):.2f}]",
                    severity=self._calculate_severity(std_dev, max_score),
                    detected_at=timezone.now()
                )
                conflicts.append((conflict, self.grade_records))

        # Check for statistical anomalies
        if len(scores) >= 3:
            mean_score = mean(scores)
            anomalies = []
            for record in self.grade_records:
                z_score = abs(float(record.score) - mean_score) / std_dev if std_dev > 0 else 0
                if z_score > 2:  # More than 2 standard deviations
                    anomalies.append(record)

            if anomalies:
                conflict = GradeConflict(
                    tenant=self.grade_records[0].tenant,
                    attempt=self.attempt,
                    conflict_type='anomaly',
                    description=f"Statistical anomalies detected in {len(anomalies)} records",
                    severity='high' if len(anomalies) > 1 else 'medium',
                    detected_at=timezone.now()
                )
                conflicts.append((conflict, anomalies))

        # Check for source conflicts (e.g., auto-grader vs manual)
        auto_sources = self.grade_records.filter(source__source_type='auto_grader')
        manual_sources = self.grade_records.filter(source__source_type='manual')

        if auto_sources.exists() and manual_sources.exists():
            auto_avg = mean([float(r.score) for r in auto_sources])
            manual_avg = mean([float(r.score) for r in manual_sources])

            if abs(auto_avg - manual_avg) > 0.05 * max_score:  # More than 5% difference
                conflict = GradeConflict(
                    tenant=self.grade_records[0].tenant,
                    attempt=self.attempt,
                    conflict_type='source_conflict',
                    description=f"Auto-grader ({auto_avg:.2f}) vs Manual ({manual_avg:.2f}) discrepancy",
                    severity='medium',
                    detected_at=timezone.now()
                )
                conflicts.append((conflict, list(auto_sources) + list(manual_sources)))

        return conflicts

    def _calculate_severity(self, std_dev: float, max_score: float) -> str:
        """Calculate conflict severity based on standard deviation."""
        variation_percent = (std_dev / max_score) * 100
        if variation_percent > 20:
            return 'high'
        elif variation_percent > 10:
            return 'medium'
        else:
            return 'low'

    def reconcile_grades(self, algorithm: str = 'weighted_average') -> Dict:
        """
        Reconcile conflicting grades using specified algorithm.
        Returns reconciled grade data.
        """
        if not self.grade_records:
            return {'error': 'No grade records found'}

        algorithms = {
            'highest_score': self._reconcile_highest,
            'lowest_score': self._reconcile_lowest,
            'average': self._reconcile_average,
            'weighted_average': self._reconcile_weighted_average,
            'manual_override': self._reconcile_manual_override,
        }

        if algorithm not in algorithms:
            return {'error': f'Unknown algorithm: {algorithm}'}

        return algorithms[algorithm]()

    def _reconcile_highest(self) -> Dict:
        """Take the highest score among all sources."""
        max_record = max(self.grade_records, key=lambda r: r.score)
        return self._format_reconciled_result(max_record, 'highest_score')

    def _reconcile_lowest(self) -> Dict:
        """Take the lowest score among all sources."""
        min_record = min(self.grade_records, key=lambda r: r.score)
        return self._format_reconciled_result(min_record, 'lowest_score')

    def _reconcile_average(self) -> Dict:
        """Calculate simple average of all scores."""
        total_score = sum(r.score for r in self.grade_records)
        avg_score = total_score / len(self.grade_records)
        max_score = self.grade_records[0].max_score

        return {
            'reconciled_score': avg_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'max_score': max_score,
            'percentage': ((avg_score / max_score) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'algorithm': 'average',
            'sources_used': len(self.grade_records),
            'confidence': self._calculate_confidence(avg_score, max_score)
        }

    def _reconcile_weighted_average(self) -> Dict:
        """Calculate weighted average based on source reliability."""
        weights = {
            'auto_grader': 0.6,
            'manual': 0.9,
            'external': 0.7,
            'reconciliation': 1.0,
        }

        total_weighted_score = Decimal('0.00')
        total_weight = Decimal('0.00')

        for record in self.grade_records:
            weight = Decimal(str(weights.get(record.source.source_type, 0.5)))
            total_weighted_score += record.score * weight
            total_weight += weight

        if total_weight == 0:
            return {'error': 'No valid weights'}

        avg_score = total_weighted_score / total_weight
        max_score = self.grade_records[0].max_score

        return {
            'reconciled_score': avg_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'max_score': max_score,
            'percentage': ((avg_score / max_score) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'algorithm': 'weighted_average',
            'sources_used': len(self.grade_records),
            'confidence': self._calculate_confidence(avg_score, max_score)
        }

    def _reconcile_manual_override(self) -> Dict:
        """Use manual grading if available, otherwise highest score."""
        manual_records = self.grade_records.filter(source__source_type='manual')
        if manual_records:
            # Use the most recent manual grade
            manual_record = manual_records.order_by('-graded_at').first()
            return self._format_reconciled_result(manual_record, 'manual_override')
        else:
            return self._reconcile_highest()

    def _format_reconciled_result(self, record: GradeRecord, algorithm: str) -> Dict:
        """Format a single record as reconciled result."""
        return {
            'reconciled_score': record.score,
            'max_score': record.max_score,
            'percentage': record.percentage,
            'algorithm': algorithm,
            'sources_used': 1,
            'confidence': Decimal('1.0'),  # High confidence for single source
            'source_record': record.id
        }

    def _calculate_confidence(self, score: Decimal, max_score: Decimal) -> Decimal:
        """
        Calculate confidence in the reconciled score.
        Higher confidence when multiple sources agree, lower when they conflict.
        """
        if len(self.grade_records) == 1:
            return Decimal('0.8')  # Moderate confidence for single source

        scores = [float(r.score) for r in self.grade_records]
        std_dev = stdev(scores) if len(scores) > 1 else 0
        variation_percent = (std_dev / float(max_score)) * 100

        # Confidence decreases with variation
        if variation_percent < 5:
            return Decimal('0.95')
        elif variation_percent < 10:
            return Decimal('0.85')
        elif variation_percent < 20:
            return Decimal('0.70')
        else:
            return Decimal('0.50')


class ApprovalWorkflowEngine:
    """
    Engine for managing approval workflows for grade amendments.
    """

    def __init__(self, tenant):
        self.tenant = tenant

    def create_amendment_workflow(self, amendment) -> ApprovalWorkflow:
        """
        Create an approval workflow for a grade amendment.
        """
        from .models import ApprovalWorkflow

        # Define approval hierarchy (this could be configurable per tenant)
        hierarchy = [
            {'role': 'instructor', 'step': 1},
            {'role': 'department_head', 'step': 2},
        ]

        workflow = ApprovalWorkflow.objects.create(
            tenant=self.tenant,
            workflow_type='grade_amendment',
            resource_id=amendment.id,
            required_approvers=[step['role'] for step in hierarchy],
            expires_at=timezone.now() + timezone.timedelta(days=7)  # 7 days to approve
        )

        # Create approval steps
        for step_info in hierarchy:
            ApprovalStep.objects.create(
                workflow=workflow,
                step_number=step_info['step'],
                approver_role=step_info['role']
            )

        return workflow

    def process_approval(self, workflow: ApprovalWorkflow, approver: User, decision: str, comments: str = '') -> bool:
        """
        Process an approval decision for a workflow step.
        Returns True if the workflow is completed.
        """

        # Find the current pending step
        current_step = workflow.steps.filter(approved=False).order_by('step_number').first()
        if not current_step:
            return True  # Already completed

        # Check if approver has the required role (simplified check)
        if not self._user_has_role(approver, current_step.approver_role):
            raise ValueError(f'User does not have required role: {current_step.approver_role}')

        # Record the approval
        current_step.approved = (decision == 'approve')
        current_step.approved_by = approver
        current_step.approved_at = timezone.now()
        current_step.comments = comments
        current_step.save()

        if decision == 'reject':
            workflow.status = 'rejected'
            workflow.save()
            return True

        # Check if all steps are approved
        if workflow.steps.filter(approved=False).exists():
            return False  # More steps pending

        # All steps approved
        workflow.status = 'approved'
        workflow.save()

        # Apply the amendment
        self._apply_amendment(workflow.resource_id)

        return True

    def _user_has_role(self, user: User, role_name: str) -> bool:
        """
        Check if user has the specified role.
        This is a simplified check - in reality, you'd check against the IAM system.
        """
        # Placeholder implementation
        return True  # Assume user has the role for now

    def _apply_amendment(self, amendment_id):
        """
        Apply the approved amendment to the grade record.
        """

        amendment = GradeAmendment.objects.get(id=amendment_id)
        grade_record = amendment.grade_record

        # Update the grade record
        grade_record.score = amendment.new_score
        grade_record.percentage = (amendment.new_score / grade_record.max_score) * 100
        grade_record.save()

        # Mark amendment as approved
        amendment.approved = True
        amendment.approved_at = timezone.now()
        amendment.save()
