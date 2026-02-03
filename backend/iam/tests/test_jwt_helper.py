from django.test import TestCase
from iam.services import JWTHelper
from iam.models import Tenant, User, RevokedToken

class JWTHelperTest(TestCase):
    def setUp(self):
        # generate a key pair for tests
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.private_key = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.public_key = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.tenant = Tenant.objects.create(name='T')
        self.user = User.objects.create(tenant=self.tenant, username='bob')

    def test_create_and_validate(self):
        token = JWTHelper.create_token(self.private_key, 'https://auth', f'user:{self.user.id}', self.tenant.id, self.user.id, roles=['teacher'])
        payload = JWTHelper.validate_token(token, self.public_key)
        self.assertEqual(payload['tid'], str(self.tenant.id))

    def test_revoked_token(self):
        token = JWTHelper.create_token(self.private_key, 'https://auth', f'user:{self.user.id}', self.tenant.id, self.user.id, roles=['teacher'], jti='test-jti')
        RevokedToken.objects.create(jti='test-jti')
        with self.assertRaises(Exception):
            JWTHelper.validate_token(token, self.public_key)
