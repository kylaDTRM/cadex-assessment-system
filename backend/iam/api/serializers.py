from rest_framework import serializers


class TokenRequestSerializer(serializers.Serializer):
    # For integration tests we allow issuing for a user by id; in real world protect this endpoint
    user_id = serializers.CharField()
    exp_seconds = serializers.IntegerField(default=900)
    roles = serializers.ListField(child=serializers.CharField(), required=False)
    scope = serializers.ListField(child=serializers.CharField(), required=False)
    attrs = serializers.DictField(child=serializers.CharField(), required=False)
