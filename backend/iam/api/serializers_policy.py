from rest_framework import serializers
from iam.models import TenantPolicy


class TenantPolicySerializer(serializers.ModelSerializer):
    tenant = serializers.UUIDField()

    class Meta:
        model = TenantPolicy
        fields = ('id', 'tenant', 'name', 'rego', 'version', 'last_deployed_at', 'last_deploy_status')
        read_only_fields = ('id', 'last_deployed_at', 'last_deploy_status')
