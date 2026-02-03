LTI 1.3 Flow (textual explanation)

Overview:
- Student clicks an LTI resource in Moodle which initiates an OIDC-based login flow.
- Moodle issues an OIDC authorization to the registered tool (CADEX) including an id_token.
- CADEX validates the id_token (issuer, audience, expiry, nonce and signature) and establishes a local session mapping LMS roles to CADEX roles.
- For roster and role sync, CADEX calls NRPS (Names and Role Provisioning Service) if available to fetch course membership.
- When grades are produced by CADEX, they should be sent back using LTI AGS (Assignment & Grade Services) where possible, falling back to Moodle webservice endpoints for legacy setups.

Key security checks:
- Validate JWT signatures (RS256) using the registered public keys (jwks_uri/kid).
- Validate state and nonce values to prevent replay and CSRF.
- Use idempotency keys on grade writes and webhook processing to achieve safe retries.

Notes:
- AGS provides the most standards-compliant grade push mechanism; implement secure server-to-server auth for AGS calls and limit scopes on service tokens.
- For older Moodle versions where LTI or AGS are not available, use the lightweight local plugin and a restricted service token to call Moodle's REST endpoints.
