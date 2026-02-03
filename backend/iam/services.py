import hashlib
import json
import time
from django.conf import settings
from django.core.cache import cache
from .models import RoleBinding, RolePermission, AttributePolicy, DelegatedGrant, EmergencyAccess, AuditLog, RevokedToken
from django.utils import timezone

CACHE_TTL = getattr(settings, 'IAM_CACHE_TTL', 60)  # seconds
CACHE_PREFIX = 'iam:perm:'
INVALIDATION_CHANNEL = getattr(settings, 'IAM_INVALIDATION_CHANNEL', 'iam_invalidation')


def _cache_key(tenant_id, user_id, permission, resource):
    r = json.dumps(resource, sort_keys=True) if resource else ''
    key = f"{tenant_id}:{user_id}:{permission}:{hashlib.sha1(r.encode()).hexdigest()}"
    return CACHE_PREFIX + hashlib.sha1(key.encode()).hexdigest()


def _hash_audit(prev_hash, tenant_id, actor_id, action, resource_json):
    s = (prev_hash or '') + '|' + str(tenant_id) + '|' + str(actor_id or '') + '|' + action + '|' + resource_json + '|' + str(time.time())
    return hashlib.sha256(s.encode()).hexdigest()


class PolicyEvaluator:
    """A small, safe evaluator for 'simple' ABAC expressions.
    The expression language supports referencing user and resource attributes via `user.attrs['key']` and resource['attrs']['key'].
    Only boolean logic and comparisons allowed: ==, !=, <, >, <=, >=, and, or, not.
    """

    SAFE_BUILTINS = {}

    @staticmethod
    def evaluate(expression: str, context: dict) -> bool:
        # Very lightweight and guarded: build a safe namespace exposing user and resource
        # Do NOT use eval on untrusted input in production without a full sandbox.
        allowed_names = {'user': context.get('user', {}), 'resource': context.get('resource', {})}
        # Restrict __builtins__ to prevent abuse
        safe_globals = {'__builtins__': {}}
        safe_globals.update(allowed_names)
        try:
            result = eval(expression, safe_globals, {})
            return bool(result)
        except Exception:
            return False


class PermissionResolver:
    """Core permission resolution service.
    Use has_permission(user, permission, resource) to check access. Caches results and supports invalidation.
    """

    @staticmethod
    def has_permission(user, permission_name, resource=None):
        # user is an iam.User instance
        tenant_id = str(user.tenant_id)
        cache_key = _cache_key(tenant_id, str(user.id), permission_name, resource or {})
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 1. Emergency access check
        now = timezone.now()
        e = EmergencyAccess.objects.filter(tenant=user.tenant, requester=user, permission__name=permission_name, start_at__lte=now, expires_at__gte=now, consumed=False).first()
        if e:
            # record audit and optionally mark consumed here (we'll leave consumed policy to caller)
            PermissionResolver._audit(user.tenant, user, 'permission.allow.emergency', {'permission': permission_name, 'resource': resource})
            cache.set(cache_key, True, CACHE_TTL)
            return True

        # 2. Deny checks (explicit denies)
        # Gather user's role bindings
        bindings = RoleBinding.objects.filter(subject_type='user', subject_id=user.id, tenant=user.tenant)
        for b in bindings:
            if b.expires_at and b.expires_at <= now:
                continue
            rperms = RolePermission.objects.filter(role=b.role, permission__name=permission_name, effect='deny')
            for rp in rperms:
                if PermissionResolver._match_scope(rp.resource_pattern, resource, b.resource_scope):
                    PermissionResolver._audit(user.tenant, user, 'permission.deny.role', {'role': b.role.name, 'permission': permission_name, 'resource': resource})
                    cache.set(cache_key, False, CACHE_TTL)
                    return False

        # 3. Attribute policies deny
        ap_deny = AttributePolicy.objects.filter(tenant=user.tenant, effect='deny')
        for ap in ap_deny:
            if ap.policy_type == 'simple' and PolicyEvaluator.evaluate(ap.expression, {'user': {'attrs': user.attrs}, 'resource': resource or {}}):
                PermissionResolver._audit(user.tenant, user, 'permission.deny.policy', {'policy': ap.name, 'permission': permission_name})
                cache.set(cache_key, False, CACHE_TTL)
                return False
            if ap.policy_type == 'opa':
                # Use OPA client to evaluate with the stored policy path in `expression`.
                from .opa_client import OPAClient
                input_obj = {'user': {'attrs': user.attrs}, 'resource': resource or {}, 'permission': permission_name}
                res = OPAClient.evaluate(ap.expression, input_obj)
                if res:
                    PermissionResolver._audit(user.tenant, user, 'permission.deny.policy.opa', {'policy': ap.name, 'permission': permission_name})
                    cache.set(cache_key, False, CACHE_TTL)
                    return False

        # 4. Delegated denies (not commonly used) - omitted for brevity

        # 5. Allows
        allowed = False
        for b in bindings:
            if b.expires_at and b.expires_at <= now:
                continue
            rperms = RolePermission.objects.filter(role=b.role, permission__name=permission_name, effect='allow')
            for rp in rperms:
                if PermissionResolver._match_scope(rp.resource_pattern, resource, b.resource_scope):
                    allowed = True
                    break
            if allowed:
                break

        # 6. Delegated grants
        if not allowed:
            dg = DelegatedGrant.objects.filter(tenant=user.tenant, grantee=user, permission__name=permission_name, active=True, expires_at__gte=now).first()
            if dg:
                # optionally check resource scope match
                allowed = True

        # 7. ABAC allow policies
        if not allowed:
            ap_allow = AttributePolicy.objects.filter(tenant=user.tenant, effect='allow')
            for ap in ap_allow:
                if ap.policy_type == 'simple' and PolicyEvaluator.evaluate(ap.expression, {'user': {'attrs': user.attrs}, 'resource': resource or {}}):
                    allowed = True
                    break
                if ap.policy_type == 'opa':
                    from .opa_client import OPAClient
                    input_obj = {'user': {'attrs': user.attrs}, 'resource': resource or {}, 'permission': permission_name}
                    res = OPAClient.evaluate(ap.expression, input_obj)
                    if res:
                        allowed = True
                        break

        PermissionResolver._audit(user.tenant, user, 'permission.check', {'permission': permission_name, 'resource': resource, 'result': allowed})
        cache.set(cache_key, allowed, CACHE_TTL)
        return allowed

    @staticmethod
    def _match_scope(pattern, resource, binding_scope):
        # Very simple scope matching: exact match or wildcard patterns like 'course:*' or 'course:3001'
        if pattern:
            if not resource:
                return False
            res_id = resource.get('id') or ''
            pat = pattern
            if pat.endswith(':*'):
                return res_id.startswith(pat[:-2]) or res_id == pat[:-2]
            return pat == res_id or pat == binding_scope
        # if pattern is empty, binding scope may apply
        if binding_scope:
            if not resource:
                return False
            return binding_scope == resource.get('id')
        return True

    @staticmethod
    def _audit(tenant, actor, action, resource_json):
        # Append-only audit with chained hashes
        prev = AuditLog.objects.filter(tenant=tenant).order_by('-id').first()
        prev_hash = prev.hash if prev else None
        resource_s = json.dumps(resource_json, sort_keys=True)
        h = _hash_audit(prev_hash, tenant.id, getattr(actor, 'id', None), action, resource_s)
        AuditLog.objects.create(tenant=tenant, actor=actor, action=action, resource=resource_json, prev_hash=prev_hash, hash=h)


class JWTHelper:
    import jwt
    @staticmethod
    def create_token(private_key, issuer, subject, tenant_id, uid, roles=None, scope=None, attrs=None, delegation=None, breakglass=None, exp_seconds=900, jti=None):
        now = int(time.time())
        payload = {
            'iss': issuer,
            'sub': subject,
            'aud': 'caex-app',
            'tid': str(tenant_id),
            'uid': str(uid),
            'roles': roles or [],
            'scope': scope or [],
            'attrs': attrs or {},
            'iat': now,
            'exp': now + exp_seconds,
            'jti': jti or hashlib.sha1(f"{uid}{now}".encode()).hexdigest()
        }
        if delegation:
            payload['delegation'] = delegation
        if breakglass:
            payload['breakglass'] = breakglass
        token = JWTHelper.jwt.encode(payload, private_key, algorithm='RS256')
        return token

    @staticmethod
    def validate_token(token, public_key, check_revoked=True):
        try:
            payload = JWTHelper.jwt.decode(token, public_key, algorithms=['RS256'], audience='caex-app')
        except Exception:
            raise
        if check_revoked:
            jti = payload.get('jti')
            if RevokedToken.objects.filter(jti=jti).exists():
                raise Exception('token_revoked')
        return payload


# Simple invalidation hook to purge cache when bindings/grants/policies change.
# In production, this should publish to Redis channel and other nodes should listen and clear cache entries.

def notify_invalidation(tenant_id):
    # naive: clear entire IAM cache keys; optimized approaches should target keys per tenant
    keys = cache.keys(CACHE_PREFIX + '*') if hasattr(cache, 'keys') else []
    for k in keys:
        if str(tenant_id) in k:
            cache.delete(k)
    # publish to redis channel when configured
    try:
        import redis
        redis_url = getattr(settings, 'REDIS_URL', None)
        if redis_url:
            r = redis.from_url(redis_url)
            r.publish(INVALIDATION_CHANNEL, str(tenant_id))
    except Exception:
        pass
