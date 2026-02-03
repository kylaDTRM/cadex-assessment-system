from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from iam.api.serializers import TokenRequestSerializer
from iam.models import User
from iam.services import JWTHelper
from django.conf import settings

class TokenIssueView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = TokenRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = User.objects.get(id=data['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'user_not_found'}, status=status.HTTP_404_NOT_FOUND)
        # Create token signed with local private key. For tests use settings.IAM_PRIVATE_KEY
        private_key = getattr(settings, 'IAM_PRIVATE_KEY_PEM', None)
        if not private_key:
            return Response({'error': 'private_key_not_configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        token = JWTHelper.create_token(private_key, getattr(settings, 'IAM_ISSUER', 'https://auth'), f'user:{user.id}', user.tenant.id, user.id, roles=data.get('roles', []), scope=data.get('scope', []), attrs=data.get('attrs', {}), exp_seconds=data.get('exp_seconds', 900))
        return Response({'token': token})
