from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from iam.api.serializers_policy import TenantPolicySerializer
from iam.models import TenantPolicy, Tenant
from iam.management.commands.deploy_opa_policies import Command as DeployCommand


class TenantPolicyListCreate(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = TenantPolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        tenant_id = data['tenant']
        tenant = Tenant.objects.get(id=tenant_id)
        policy = TenantPolicy.objects.create(tenant=tenant, name=data['name'], rego=data['rego'], version=data.get('version'))
        return Response(TenantPolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class TenantPolicyDeploy(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            TenantPolicy.objects.get(id=pk)
        except TenantPolicy.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            DeployCommand().handle()
            return Response({'status': 'deployed'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
