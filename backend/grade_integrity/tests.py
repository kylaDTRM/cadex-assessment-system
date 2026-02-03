from django.test import TestCase

from django.utils import timezone
from decimal import Decimal
from assessment_core.models import User, Institution, Course, Assessment, Question, Attempt
from iam.models import Tenant
from .models import GradeSource, GradeRecord
from .services import GradeReconciliationEngine


class GradeReconciliationTestCase(TestCase):
    def setUp(self):
        # Create test data
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
        self.question = Question.objects.create(
            assessment=self.assessment,
            question_type="MCQ",
            question_text="What is 2+2?",
            points=Decimal('10.0'),
            options=[{"text": "4", "correct": True}, {"text": "5", "correct": False}]
        )
        self.attempt = Attempt.objects.create(
            assessment=self.assessment,
            student=self.user,
            raw_score=Decimal('8.0'),
            max_score=Decimal('10.0'),
            percentage=Decimal('80.0')
        )

        # Create grade sources
        self.auto_grader = GradeSource.objects.create(
            tenant=self.tenant,
            name="Auto Grader",
            source_type="auto_grader"
        )
        self.manual_grader = GradeSource.objects.create(
            tenant=self.tenant,
            name="Manual Review",
            source_type="manual"
        )

    def test_reconciliation_algorithms(self):
        """Test different reconciliation algorithms"""
        # Create grade records
        GradeRecord.objects.create(
            tenant=self.tenant,
            attempt=self.attempt,
            source=self.auto_grader,
            score=Decimal('8.0'),
            max_score=Decimal('10.0'),
            percentage=Decimal('80.0')
        )
        GradeRecord.objects.create(
            tenant=self.tenant,
            attempt=self.attempt,
            source=self.manual_grader,
            score=Decimal('9.0'),
            max_score=Decimal('10.0'),
            percentage=Decimal('90.0')
        )

        engine = GradeReconciliationEngine(self.attempt)

        # Test weighted average
        result = engine.reconcile_grades('weighted_average')
        self.assertIn('reconciled_score', result)
        self.assertEqual(result['algorithm'], 'weighted_average')

        # Test average
        result = engine.reconcile_grades('average')
        self.assertEqual(result['reconciled_score'], Decimal('8.5'))

        # Test highest score
        result = engine.reconcile_grades('highest_score')
        self.assertEqual(result['reconciled_score'], Decimal('9.0'))

    def test_conflict_detection(self):
        """Test conflict detection"""
        # Create conflicting grade records
        GradeRecord.objects.create(
            tenant=self.tenant,
            attempt=self.attempt,
            source=self.auto_grader,
            score=Decimal('5.0'),  # Much lower score
            max_score=Decimal('10.0'),
            percentage=Decimal('50.0')
        )
        GradeRecord.objects.create(
            tenant=self.tenant,
            attempt=self.attempt,
            source=self.manual_grader,
            score=Decimal('9.5'),  # Much higher score
            max_score=Decimal('10.0'),
            percentage=Decimal('95.0')
        )

        engine = GradeReconciliationEngine(self.attempt)
        conflicts_data = engine.detect_conflicts()

        self.assertTrue(len(conflicts_data) > 0)
        conflict, involved_records = conflicts_data[0]
        self.assertEqual(conflict.conflict_type, 'score_discrepancy')
        self.assertEqual(conflict.severity, 'high')
        self.assertEqual(len(involved_records), 2)

    def test_no_conflicts_with_consistent_grades(self):
        """Test no conflicts detected with consistent grades"""
        # Create consistent grade records
        GradeRecord.objects.create(
            tenant=self.tenant,
            attempt=self.attempt,
            source=self.auto_grader,
            score=Decimal('8.5'),
            max_score=Decimal('10.0'),
            percentage=Decimal('85.0')
        )
        GradeRecord.objects.create(
            tenant=self.tenant,
            attempt=self.attempt,
            source=self.manual_grader,
            score=Decimal('8.7'),
            max_score=Decimal('10.0'),
            percentage=Decimal('87.0')
        )

        engine = GradeReconciliationEngine(self.attempt)
        conflicts_data = engine.detect_conflicts()

        # Should have no conflicts for small variations
        score_discrepancy_conflicts = [c for c, _ in conflicts_data if c.conflict_type == 'score_discrepancy']
        self.assertEqual(len(score_discrepancy_conflicts), 0)


class IntegrationTestCase(TestCase):
    def setUp(self):
        # Create test data similar to other tests
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
        self.question = Question.objects.create(
            assessment=self.assessment,
            question_type="MCQ",
            question_text="What is 2+2?",
            points=Decimal('10.0'),
            options=[{"text": "4", "correct": True}, {"text": "5", "correct": False}]
        )
        self.attempt = Attempt.objects.create(
            assessment=self.assessment,
            student=self.user
        )

    def test_auto_grader_integration(self):
        """Test that auto-grader creates grade records"""
        from auto_grading.grader import AutoGrader

        # Create a response
        from assessment_core.models import Response
        Response.objects.create(
            attempt=self.attempt,
            question=self.question,
            response_data={'selected': '4'}
        )

        # Run auto-grader
        grader = AutoGrader()
        grader.grade_attempt(self.attempt.id)

        # Check that grade record was created
        grade_records = GradeRecord.objects.filter(attempt=self.attempt)
        self.assertTrue(grade_records.exists())

        record = grade_records.first()
        self.assertEqual(record.score, Decimal('10.0'))
        self.assertEqual(record.max_score, Decimal('10.0'))
        self.assertEqual(record.source.source_type, 'auto_grader')


class GradeModelTestCase(TestCase):
    def setUp(self):
        # Similar setup as above
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
        self.source = GradeSource.objects.create(
            tenant=self.tenant,
            name="Test Source",
            source_type="manual"
        )

    def test_grade_record_creation(self):
        """Test creating grade records"""
        record = GradeRecord.objects.create(
            tenant=self.tenant,
            attempt=self.attempt,
            source=self.source,
            score=Decimal('8.5'),
            max_score=Decimal('10.0'),
            percentage=Decimal('85.0'),
            graded_by=self.user
        )

        self.assertEqual(record.score, Decimal('8.5'))
        self.assertEqual(record.source, self.source)
        self.assertEqual(record.attempt, self.attempt)

    def test_unique_constraint(self):
        """Test unique constraint on attempt-source pairs"""
        GradeRecord.objects.create(
            tenant=self.tenant,
            attempt=self.attempt,
            source=self.source,
            score=Decimal('8.0'),
            max_score=Decimal('10.0'),
            percentage=Decimal('80.0')
        )

        with self.assertRaises(Exception):  # Should raise IntegrityError
            GradeRecord.objects.create(
                tenant=self.tenant,
                attempt=self.attempt,
                source=self.source,
                score=Decimal('9.0'),
                max_score=Decimal('10.0'),
                percentage=Decimal('90.0')
            )
