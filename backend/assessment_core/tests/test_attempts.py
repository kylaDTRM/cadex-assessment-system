from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from ..models import Course, Assessment, Attempt


class AttemptViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='student', password='pw')
        self.client.force_authenticate(user=self.user)
        self.course = Course.objects.create(course_code='CS102', title='Data Structures')
        self.assessment = Assessment.objects.create(course=self.course, title='Quiz', assessment_type='Q1_CA', open_datetime='2026-01-01T10:00:00Z', close_datetime='2026-01-01T12:00:00Z', duration_minutes=30)

    def test_create_attempt(self):
        url = '/api/attempts/'
        data = {
            'assessment': str(self.assessment.id),
            'student': str(self.user.id),
            'attempt_number': 1,
        }
        resp = self.client.post(url, data)
        self.assertIn(resp.status_code, (status.HTTP_201_CREATED, status.HTTP_200_OK))
        self.assertTrue(Attempt.objects.filter(assessment=self.assessment, student=self.user).exists())
