CAEX Integration (Moodle local plugin)

Purpose:
- Lightweight plugin to allow legacy Moodles to forward events (webhook), create restricted service tokens, and expose minimal webservice functions for a CADEX-like external assessment platform.

Features (skeleton):
- Admin settings (API base URL, shared secret, enable/disable webhooks).
- Webhook forwarder with HMAC signing.
- Webservice functions to return capabilities and accept idempotent grade updates.
- CLI/cron reconciliation stubs for periodic syncing.

Installation:
- Copy this folder to moodle/local/caex_integration
- Visit Site administration → Notifications to install DB schema
- Configure the plugin under Site administration → Plugins → Local plugins → CAEX Integration

Security:
- Create a restricted webservice token for the external platform and limit capabilities.
- Keep shared secret safe and rotate periodically.

Creating a restricted webservice token (admin):
1. Site administration → Plugins → Web services → Manage tokens
2. Create a new token for a non-human service account (create a dedicated user like 'caex_service')
3. Restrict the token to the service 'CAEX integration service' (see plugin's db/services.php)
4. Store the token securely in the external platform and use it for REST calls.

Sample curl to call `local_caex_integration_update_grade` (REST webservice):

```bash
curl -X POST 'https://your-moodle.example.com/webservice/rest/server.php?wstoken=<TOKEN>&wsfunction=local_caex_integration_update_grade&moodlewsrestformat=json' \
  -H 'Content-Type: application/json' \
  --data-raw '{"itemid":123,"userid":456,"grade":"78.5","timestamp":"2026-02-03T12:00:00Z","client_request_id":"<uuid>"}'
```

Notes:
- Always supply `client_request_id` to ensure idempotency.
- Use TLS and a restricted token with minimal capabilities.
