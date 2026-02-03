from django.test import TestCase
from django.contrib.auth import get_user_model
from iam.models import Tenant, User
from django.conf import settings
from django.urls import reverse

class TokenIssueTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='T')
        self.user = User.objects.create(tenant=self.tenant, username='svc')
        # create admin user to call endpoint
        UserModel = get_user_model()
        self.admin = UserModel.objects.create_superuser('admin', 'admin@example.com', 'pass')
        # inject a private key into settings
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv = key.private_bytes(encoding=serialization.Encoding.PEM,format=serialization.PrivateFormat.TraditionalOpenSSL,encryption_algorithm=serialization.NoEncryption())
        settings.IAM_PRIVATE_KEY_PEM = priv.decode()

    def test_token_issue_requires_admin(self):
        url = reverse('iam:iam-token')
        r = self.client.post(url, {'user_id': str(self.user.id)})
        self.assertEqual(r.status_code, 403)
        # login as admin
        self.client.login(username='admin', password='pass')
        r2 = self.client.post(url, {'user_id': str(self.user.id)})
        self.assertEqual(r2.status_code, 200)
        self.assertIn('token', r2.json())
