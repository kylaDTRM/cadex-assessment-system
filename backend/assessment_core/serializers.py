from rest_framework import serializers
from .models import Course, Assessment, Question, Attempt, Response, SyncLog


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class AssessmentSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = '__all__'


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ['id', 'question', 'response_data', 'client_id', 'client_ts', 'response_hash']


class AttemptSerializer(serializers.ModelSerializer):
    responses = ResponseSerializer(many=True, required=False)

    class Meta:
        model = Attempt
        fields = ['id', 'assessment', 'student', 'attempt_number', 'client_id', 'client_version', 'server_version', 'status', 'last_client_ts', 'responses']


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'
