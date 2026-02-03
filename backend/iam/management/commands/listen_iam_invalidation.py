from django.core.management.base import BaseCommand
from django.conf import settings
import redis
from django.core.cache import cache

class Command(BaseCommand):
    help = 'Listen for IAM invalidation events on Redis and clear local caches accordingly'

    def handle(self, *args, **options):
        redis_url = getattr(settings, 'REDIS_URL', None)
        if not redis_url:
            self.stdout.write(self.style.ERROR('REDIS_URL not configured'))
            return
        r = redis.from_url(redis_url)
        p = r.pubsub()
        channel = getattr(settings, 'IAM_INVALIDATION_CHANNEL', 'iam_invalidation')
        p.subscribe(channel)
        self.stdout.write(self.style.SUCCESS(f'Listening on channel {channel}'))
        for message in p.listen():
            if message['type'] != 'message':
                continue
            tenant_id = message['data'].decode()
            # Naive clear: delete cache keys with tenant in name if cache supports .keys()
            try:
                keys = cache.keys('iam:perm:*') if hasattr(cache, 'keys') else []
                for k in keys:
                    if tenant_id in k:
                        cache.delete(k)
                self.stdout.write(self.style.SUCCESS(f'Invalidated cache for tenant {tenant_id}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error clearing cache: {e}'))
