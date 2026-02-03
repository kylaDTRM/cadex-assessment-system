from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from .models import (
    IntegrityEvent, IntegrityIncident, RiskRule, Evidence,
    ReviewWorkflow, ReviewStep
)
from assessment_core.models import Attempt
from iam.models import Tenant


class IntegrityEventIngestionService:
    """
    Service for ingesting and processing proctoring signals.
    """

    def ingest_event(self, tenant: Tenant, proctoring_session_id: str,
                    event_type: str, event_data: dict, attempt: Attempt = None,
                    severity: str = 'low', metadata: dict = None) -> IntegrityEvent:
        """
        Ingest a proctoring event and create an IntegrityEvent record.
        """

        # Find attempt if not provided
        if not attempt:
            attempt = self._find_attempt_by_session(proctoring_session_id)

        if not attempt:
            raise ValueError(f"Could not find attempt for session {proctoring_session_id}")

        event = IntegrityEvent.objects.create(
            tenant=tenant,
            event_type=event_type,
            severity=severity,
            proctoring_session_id=proctoring_session_id,
            attempt=attempt,
            event_data=event_data,
            metadata=metadata or {},
        )

        # Process the event (async in production)
        self._process_event(event)

        return event

    def _find_attempt_by_session(self, session_id: str) -> Attempt:
        """
        Find attempt by proctoring session ID.
        This would integrate with the proctoring system.
        """
        # Placeholder - in real implementation, this would query
        # the proctoring system or a mapping table
        from iam.models import ExamSession
        try:
            exam_session = ExamSession.objects.get(proctoring_session_id=session_id)
            return exam_session.exam_instance.assessment_version.assessment.attempts.filter(
                user=exam_session.user
            ).first()
        except ExamSession.DoesNotExist:
            return None

    def _process_event(self, event: IntegrityEvent):
        """
        Process an event - check for incident creation, update risk scores, etc.
        """
        # Mark as processed
        event.processed = True
        event.processed_at = timezone.now()
        event.save()

        # Check if this event triggers incident creation
        risk_scorer = RiskScoringService(event.tenant)
        should_create_incident = risk_scorer.evaluate_incident_creation(event)

        if should_create_incident:
            incident_service = IncidentManagementService(event.tenant)
            incident_service.create_incident_from_event(event)


class RiskScoringService:
    """
    Service for rule-based risk scoring of integrity events.
    """

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    def evaluate_incident_creation(self, event: IntegrityEvent) -> bool:
        """
        Evaluate if an event should trigger incident creation.
        """
        rules = RiskRule.objects.filter(
            tenant=self.tenant,
            is_active=True,
            rule_type__in=['event_count', 'severity_weighted']
        )

        for rule in rules:
            if self._evaluate_rule(rule, event):
                return True

        return False

    def calculate_risk_score(self, attempt: Attempt, time_window_hours: int = 24) -> dict:
        """
        Calculate overall risk score for an attempt within a time window.
        """
        since = timezone.now() - timedelta(hours=time_window_hours)

        events = IntegrityEvent.objects.filter(
            tenant=self.tenant,
            attempt=attempt,
            timestamp__gte=since
        )

        if not events:
            return {'score': Decimal('0.00'), 'level': 'low', 'factors': []}

        total_score = Decimal('0.00')
        factors = []

        # Apply all active rules
        rules = RiskRule.objects.filter(tenant=self.tenant, is_active=True)

        for rule in rules:
            rule_score, rule_factors = self._calculate_rule_score(rule, events)
            total_score += rule_score
            factors.extend(rule_factors)

        # Cap the score
        total_score = min(total_score, Decimal('100.00'))

        # Determine risk level
        if total_score >= 80:
            level = 'critical'
        elif total_score >= 60:
            level = 'high'
        elif total_score >= 40:
            level = 'medium'
        else:
            level = 'low'

        return {
            'score': total_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'level': level,
            'factors': factors[:10]  # Limit factors
        }

    def _evaluate_rule(self, rule: RiskRule, event: IntegrityEvent) -> bool:
        """
        Evaluate a single rule against an event.
        """
        if rule.rule_type == 'event_count':
            return self._evaluate_count_rule(rule, event)
        elif rule.rule_type == 'severity_weighted':
            return self._evaluate_severity_rule(rule, event)

        return False

    def _evaluate_count_rule(self, rule: RiskRule, event: IntegrityEvent) -> bool:
        """
        Evaluate count-based rules.
        """
        time_window = rule.parameters.get('time_window_hours', 1)
        since = timezone.now() - timedelta(hours=time_window)

        count = IntegrityEvent.objects.filter(
            tenant=self.tenant,
            attempt=event.attempt,
            event_type=rule.event_type or event.event_type,
            timestamp__gte=since
        ).count()

        threshold = int(rule.threshold_value)
        return self._compare_values(count, threshold, rule.operator)

    def _evaluate_severity_rule(self, rule: RiskRule, event: IntegrityEvent) -> bool:
        """
        Evaluate severity-weighted rules.
        """
        severity_weights = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        weight = severity_weights.get(event.severity, 1)

        threshold = int(rule.threshold_value)
        return self._compare_values(weight, threshold, rule.operator)

    def _calculate_rule_score(self, rule: RiskRule, events) -> tuple[Decimal, list]:
        """
        Calculate score contribution from a rule.
        """
        score = Decimal('0.00')
        factors = []

        if rule.rule_type == 'event_count':
            count = events.filter(event_type=rule.event_type).count() if rule.event_type else len(events)
            if self._compare_values(count, int(rule.threshold_value), rule.operator):
                score = rule.base_score * rule.score_multiplier
                factors.append(f"Count rule '{rule.name}': {count} events")

        elif rule.rule_type == 'severity_weighted':
            severity_weights = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            total_weight = sum(severity_weights.get(e.severity, 1) for e in events)
            if self._compare_values(total_weight, int(rule.threshold_value), rule.operator):
                score = rule.base_score * rule.score_multiplier
                factors.append(f"Severity rule '{rule.name}': weight {total_weight}")

        return score, factors

    def _compare_values(self, value, threshold, operator) -> bool:
        """
        Compare values based on operator.
        """
        if operator == 'gt':
            return value > threshold
        elif operator == 'gte':
            return value >= threshold
        elif operator == 'lt':
            return value < threshold
        elif operator == 'lte':
            return value <= threshold
        elif operator == 'eq':
            return value == threshold

        return False


class IncidentManagementService:
    """
    Service for managing integrity incidents and workflows.
    """

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    def create_incident_from_event(self, event: IntegrityEvent) -> IntegrityIncident:
        """
        Create an incident from a triggering event.
        """
        # Calculate risk score
        risk_scorer = RiskScoringService(self.tenant)
        risk_data = risk_scorer.calculate_risk_score(event.attempt)

        # Gather related events
        related_events = self._find_related_events(event)

        incident = IntegrityIncident.objects.create(
            tenant=self.tenant,
            title=f"Integrity Alert: {event.event_type}",
            description=self._generate_incident_description(event, related_events),
            attempt=event.attempt,
            risk_score=risk_data['score'],
            risk_level=risk_data['level'],
            detected_at=event.timestamp,
        )

        # Associate events
        incident.related_events.set(related_events)

        # Create review workflow
        self._create_review_workflow(incident)

        return incident

    def _find_related_events(self, trigger_event: IntegrityEvent) -> list[IntegrityEvent]:
        """
        Find events related to the triggering event.
        """
        time_window = timedelta(hours=1)  # Look at events within 1 hour

        return list(IntegrityEvent.objects.filter(
            tenant=self.tenant,
            attempt=trigger_event.attempt,
            timestamp__gte=trigger_event.timestamp - time_window,
            timestamp__lte=trigger_event.timestamp + time_window
        ))

    def _generate_incident_description(self, event: IntegrityEvent, related_events: list) -> str:
        """
        Generate a description for the incident.
        """
        description = f"Integrity event detected: {event.event_type} with severity {event.severity}."

        if len(related_events) > 1:
            description += f" {len(related_events)} related events found in the time window."

        return description

    def _create_review_workflow(self, incident: IntegrityIncident):
        """
        Create a review workflow for the incident.
        """
        workflow = ReviewWorkflow.objects.create(
            tenant=self.tenant,
            workflow_type='incident_review',
            incident=incident,
            required_reviewers=['exam_integrity_officer', 'department_head'],
            escalation_rules={
                'high_risk': {'escalate_to': 'academic_integrity_committee', 'time_limit': 24},
                'critical_risk': {'escalate_to': 'dean', 'time_limit': 4}
            }
        )

        # Create workflow steps
        steps_data = [
            {
                'step_name': 'Initial Review',
                'step_type': 'review',
                'assigned_role': 'exam_integrity_officer',
                'instructions': 'Review the incident details and evidence.',
                'order': 1
            },
            {
                'step_name': 'Supervisor Approval',
                'step_type': 'approval',
                'assigned_role': 'department_head',
                'instructions': 'Review and approve the incident findings.',
                'order': 2
            }
        ]

        for step_data in steps_data:
            ReviewStep.objects.create(
                workflow=workflow,
                **step_data
            )

    def resolve_incident(self, incident: IntegrityIncident, resolution: str,
                        notes: str, resolved_by) -> IntegrityIncident:
        """
        Resolve an incident with a final decision.
        """
        incident.status = 'resolved'
        incident.resolution = resolution
        incident.resolution_notes = notes
        incident.resolved_by = resolved_by
        incident.resolved_at = timezone.now()
        incident.save()

        # Update related workflow
        workflow = incident.workflows.filter(workflow_type='incident_review').first()
        if workflow:
            workflow.status = 'completed'
            workflow.decision = resolution
            workflow.decision_notes = notes
            workflow.decided_by = resolved_by
            workflow.completed_at = timezone.now()
            workflow.save()

        return incident


class EvidenceRetentionService:
    """
    Service for managing evidence retention and cleanup.
    """

    def __init__(self, tenant: Tenant):
        self.tenant = tenant

    def set_retention_policy(self, incident: IntegrityIncident, policy: str = 'standard'):
        """
        Set retention policy for incident evidence.
        """
        retention_days = self._get_retention_days(policy, incident.risk_level)

        retention_until = timezone.now() + timedelta(days=retention_days)

        incident.evidence_retention_until = retention_until
        incident.save()

        # Update all evidence files
        incident.evidence_files.update(retention_until=retention_until)

    def cleanup_expired_evidence(self):
        """
        Clean up evidence that has exceeded retention period.
        """
        expired_evidence = Evidence.objects.filter(
            tenant=self.tenant,
            retention_until__lt=timezone.now(),
            auto_delete=True
        )

        deleted_count = 0
        for evidence in expired_evidence:
            # In real implementation, this would delete from storage
            # For now, just mark as deleted
            evidence.incident.evidence_deleted = True
            evidence.incident.save()
            evidence.delete()
            deleted_count += 1

        return deleted_count

    def _get_retention_days(self, policy: str, risk_level: str) -> int:
        """
        Get retention days based on policy and risk level.
        """
        base_retention = {
            'minimal': 30,
            'standard': 180,  # 6 months
            'extended': 365,  # 1 year
            'permanent': 2555,  # 7 years
        }.get(policy, 180)

        # Adjust based on risk level
        multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5,
            'critical': 2.0,
        }

        return int(base_retention * multipliers.get(risk_level, 1.0))
