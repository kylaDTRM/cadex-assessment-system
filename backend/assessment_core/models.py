from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    moodle_user_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True)
    student_number = models.CharField(max_length=50, null=True, blank=True)
    institution_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'users'


class Institution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    course_code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course_code} - {self.title}"


class Assessment(models.Model):
    TYPE_CHOICES = [
        ('Q1_CA', 'Continuous Assessment'),
        ('Q2_INST', 'Institutional Exam'),
        ('Q3_CENTRAL', 'Central Exam'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='assessments')
    title = models.CharField(max_length=200)
    assessment_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='Q1_CA')

    open_datetime = models.DateTimeField()
    close_datetime = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    max_attempts = models.IntegerField(default=1)
    shuffle_questions = models.BooleanField(default=True)

    status = models.CharField(max_length=20, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice'),
        ('TF', 'True/False'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='questions')
    question_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    question_text = models.TextField()
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    order_index = models.IntegerField(default=0)
    options = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['order_index']

    def __str__(self):
        return f"Q{self.order_index}"


class Attempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.IntegerField(default=1)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    raw_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True)
    max_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True)

    status = models.CharField(max_length=20, default='IN_PROGRESS')

    class Meta:
        unique_together = ['assessment', 'student', 'attempt_number']


class Response(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    response_data = models.JSONField(default=dict)
    points_awarded = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['attempt', 'question']
