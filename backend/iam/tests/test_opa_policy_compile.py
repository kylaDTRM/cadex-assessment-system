import os
import unittest
from django.test import TestCase
from django.conf import settings
from iam.opa_client import OPAClient


@unittest.skipUnless(settings.OPA_URL, 'OPA_URL not configured')
class OPAPolicyCompileTest(TestCase):

    def test_policies_compile_in_opa(self):
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'test_policies')
        base_dir = os.path.normpath(base_dir)
        assert os.path.isdir(base_dir), f"Policies dir {base_dir} missing"

        for fname in os.listdir(base_dir):
            if not fname.endswith('.rego'):
                continue
            path = os.path.join(base_dir, fname)
            with open(path, 'r', encoding='utf-8') as f:
                src = f.read()
            name = os.path.splitext(fname)[0]
            # push policy; OPAClient.push_policy will raise on non-200
            pushed = OPAClient.push_policy(name, src)
            self.assertTrue(pushed, f"Policy {fname} failed to compile/push")
