from django.conf import settings
# Import requests lazily inside methods to avoid hard dependency at module import time


class OPAClient:
    """Lightweight OPA client using HTTP API. Configure OPA_URL in settings."""

    @staticmethod
    def _base_url():
        return getattr(settings, 'OPA_URL', None)

    @staticmethod
    def evaluate(policy_path: str, input_obj: dict) -> bool:
        """Evaluate an OPA policy. policy_path should be like 'example/data/allow' or 'data/tenant/policy/allow'.
        Returns boolean result (True=allowed).
        """
        base = OPAClient._base_url()
        if not base:
            raise RuntimeError('OPA_URL not configured')
        # Compose eval endpoint: /v1/data/<policy_path>/eval
        # Normalize
        p = policy_path.strip('/')
        url = f"{base}/v1/data/{p}"
        try:
            import requests
            resp = requests.post(url, json={'input': input_obj}, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            # OPA returns `result` key with value; conservative: if result is truthy (e.g., {'allow': true} or true), consider True
            if isinstance(data, dict) and 'result' in data:
                result = data['result']
                if isinstance(result, bool):
                    return result
                # if dict like {'allow': True}
                if isinstance(result, dict):
                    # prefer explicit 'allow' key
                    if 'allow' in result:
                        return bool(result['allow'])
                    # fallback: any truthy value
                    return bool(result)
            return False
        except Exception:
            # On OPA failure, default to deny (fail-closed)
            return False

    @staticmethod
    def push_policy(policy_path: str, rego_source: str) -> bool:
        base = OPAClient._base_url()
        if not base:
            raise RuntimeError('OPA_URL not configured')
        url = f"{base}/v1/policies/{policy_path}"
        import requests
        resp = requests.put(url, data=rego_source.encode('utf-8'), headers={'Content-Type': 'text/plain'})
        resp.raise_for_status()
        return True
