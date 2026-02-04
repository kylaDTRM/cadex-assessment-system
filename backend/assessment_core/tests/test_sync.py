from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from ..models import Course, Assessment, Question, Attempt
from django.utils import timezone
import uuid


class SyncTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='syncuser', password='pw')
        self.client.force_authenticate(user=self.user)
        self.course = Course.objects.create(course_code='CS200', title='Sync Test')
        self.assessment = Assessment.objects.create(course=self.course, title='Sync Assessment', assessment_type='Q1_CA', open_datetime=timezone.now(), close_datetime=timezone.now())
        self.q1 = Question.objects.create(assessment=self.assessment, question_type='MCQ', question_text='Q1', points=1.0, order_index=1)

    def test_create_attempt_sync(self):
        client_id = str(uuid.uuid4())
        payload = {
            'client_id': client_id,
            'attempt': {
                'assessment_id': str(self.assessment.id),
                'attempt_number': 1,
                'status': 'IN_PROGRESS',
            },
            'responses': [
                {'question_id': str(self.q1.id), 'answer': {'choice': 'A'}}
            ]
        }
        resp = self.client.post('/api/sync/attempts/', payload, format='json')
        self.assertIn(resp.status_code, (201, 200))
        data = resp.json()
        self.assertIn('server_id', data)
        self.assertIn('server_version', data)

    def test_version_conflict_returns_409(self):
        # create initial attempt
        client_id = str(uuid.uuid4())
        payload = {
            'client_id': client_id,
            'attempt': {
                'assessment_id': str(self.assessment.id),
                'attempt_number': 1,
                'status': 'IN_PROGRESS',
            },
            'responses': []
        }
        resp = self.client.post('/api/sync/attempts/', payload, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        server_version = data['server_version']

        # Simulate server-side change by updating attempt directly
        att = Attempt.objects.get(client_id=client_id)
        att.server_version += 1
        att.save()

        # Now client tries to update using old base_version
        payload2 = {
            'client_id': client_id,
            'base_version': server_version,  # old version
            'attempt': {
                'status': 'SUBMITTED'
            }
        }
        resp2 = self.client.post('/api/sync/attempts/', payload2, format='json')
        self.assertEqual(resp2.status_code, 409)
        j = resp2.json()
        self.assertIn('server_state', j)
