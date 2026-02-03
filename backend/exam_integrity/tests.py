
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from assessment_core.models import Institution, Course, Assessment, Attempt
from iam.models import Tenant
from .models import IntegrityIncident, RiskRule
from .services import IntegrityEventIngestionService, RiskScoringService, IncidentManagementService

# Use Django's configured user model
User = get_user_model()


class IntegrityEventTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Tenant")
        self.institution = Institution.objects.create(name="Test University", code="TU")
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.course = Course.objects.create(
            institution=self.institution,
            course_code="CS101",
            title="Computer Science 101"
        )
        self.assessment = Assessment.objects.create(
            course=self.course,
            title="Midterm Exam",
            assessment_type="Q2_INST",
            open_datetime=timezone.now(),
            close_datetime=timezone.now() + timezone.timedelta(hours=2)
        )
        self.attempt = Attempt.objects.create(
            assessment=self.assessment,
            student=self.user
        )

    def test_event_ingestion(self):
        """Test ingesting integrity events."""
        service = IntegrityEventIngestionService()

        event_data = {
            'face_detected': False,
            'confidence': 0.95
        }

        event = service.ingest_event(
            tenant=self.tenant,
            proctoring_session_id="test-session-123",
            event_type="face_not_visible",
            event_data=event_data,
            attempt=self.attempt,
            severity="high"
        )

        self.assertEqual(event.event_type, "face_not_visible")
        self.assertEqual(event.severity, "high")
        self.assertEqual(event.attempt, self.attempt)
        self.assertTrue(event.processed)

    def test_risk_rule_evaluation(self):
        """Test risk rule evaluation."""
        # Create a count-based rule
        _rule = RiskRule.objects.create(
            tenant=self.tenant,
            name="Multiple Face Detections",
            rule_type="event_count",
            event_type="multiple_faces",
            operator="gte",
            threshold_value="3",
            base_score=Decimal("25.00")
        )

        # Create events
        service = IntegrityEventIngestionService()
        for i in range(4):
            service.ingest_event(
                tenant=self.tenant,
                proctoring_session_id=f"session-{i}",
                event_type="multiple_faces",
                event_data={'faces_detected': 2},
                attempt=self.attempt,
                severity="medium"
            )

        # Test risk scoring
        risk_service = RiskScoringService(self.tenant)
        risk_data = risk_service.calculate_risk_score(self.attempt)

        self.assertGreater(risk_data['score'], Decimal('0.00'))
        self.assertIn('factors', risk_data)

    def test_incident_creation(self):
        """Test automatic incident creation from events."""
        # Create a rule that triggers incidents
        RiskRule.objects.create(
            tenant=self.tenant,
            name="Critical Event Trigger",
            rule_type="severity_weighted",
            operator="gte",
            threshold_value="3",  # Critical severity
            base_score=Decimal("50.00")
        )

        # Ingest a critical event
        service = IntegrityEventIngestionService()
        _event = service.ingest_event(
            tenant=self.tenant,
            proctoring_session_id="critical-session",
            event_type="system_integrity",
            event_data={'integrity_check': 'failed'},
            attempt=self.attempt,
            severity="critical"
        )

        # Check if incident was created
        incidents = IntegrityIncident.objects.filter(attempt=self.attempt)
        self.assertTrue(incidents.exists())

        incident = incidents.first()
        self.assertEqual(incident.status, 'open')
        self.assertGreater(incident.risk_score, Decimal('0.00'))

    def test_incident_resolution(self):
        """Test incident resolution workflow."""
        # Create an incident
        incident = IntegrityIncident.objects.create(
            tenant=self.tenant,
            title="Test Incident",
            description="Test integrity incident",
            attempt=self.attempt,
            risk_score=Decimal("75.00"),
            risk_level="high"
        )

        # Resolve the incident
        management_service = IncidentManagementService(self.tenant)
        resolved_incident = management_service.resolve_incident(
            incident=incident,
            resolution="minor_violation",
            notes="Student was warned about behavior",
            resolved_by=self.user
        )

        self.assertEqual(resolved_incident.status, 'resolved')
        self.assertEqual(resolved_incident.resolution, 'minor_violation')
        self.assertEqual(resolved_incident.resolved_by, self.user)


class APITestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="API Test Tenant")
        self.institution = Institution.objects.create(name="API Test University", code="ATU")
        self.user = User.objects.create_user(username="apiuser", email="api@example.com")
        self.course = Course.objects.create(
            institution=self.institution,
            course_code="APITEST",
            title="API Test Course"
        )
        self.assessment = Assessment.objects.create(
            course=self.course,
            title="API Test Assessment",
            assessment_type="Q2_INST",
            open_datetime=timezone.now(),
            close_datetime=timezone.now() + timezone.timedelta(hours=2)
        )
        self.attempt = Attempt.objects.create(
            assessment=self.assessment,
            student=self.user
        )

    def test_api_endpoints_accessible(self):
        """Test that API endpoints are accessible and return proper responses."""
        from django.test import Client

        client = Client()
        # Force login the user for session authentication
        client.force_login(self.user)

        # Test events endpoint
        response = client.get('/api/exam-integrity/events/')
        self.assertEqual(response.status_code, 200)

        # Test incidents endpoint
        response = client.get('/api/exam-integrity/incidents/')
        self.assertEqual(response.status_code, 200)

        # Test risk-rules endpoint
        response = client.get('/api/exam-integrity/risk-rules/')
        self.assertEqual(response.status_code, 200)

        # Test evidence endpoint
        response = client.get('/api/exam-integrity/evidence/')
        self.assertEqual(response.status_code, 200)

        # Test workflows endpoint
        response = client.get('/api/exam-integrity/workflows/')
        self.assertEqual(response.status_code, 200)

    def test_event_ingestion_endpoint(self):
        """Test the event ingestion custom action."""
        from django.test import Client

        client = Client()
        client.force_login(self.user)

        # Test event ingestion
        event_data = {
            'proctoring_session_id': 'test-session-123',
            'event_type': 'face_not_visible',
            'event_data': {'confidence': 0.95, 'duration_seconds': 30},
            'attempt_id': str(self.attempt.id),
            'severity': 'high'
        }

        response = client.post('/api/exam-integrity/events/ingest/', event_data, content_type='application/json')
        self.assertEqual(response.status_code, 201)  # Created
