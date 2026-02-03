from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from ..models import Course, Assessment


class AssessmentViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        self.course = Course.objects.create(course_code='CS101', title='Intro CS')

    def test_list_assessments(self):
        Assessment.objects.create(
            course=self.course,
            title='Midterm',
            assessment_type='Q1_CA',
            open_datetime='2026-01-01T10:00:00Z',
            close_datetime='2026-01-01T12:00:00Z',
            duration_minutes=60)
        url = '/api/assessments/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.json()) >= 1)
