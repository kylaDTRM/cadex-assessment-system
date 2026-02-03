# Assessment Lifecycle Runbook

This runbook covers handling common failures and emergency operations for the Assessment Lifecycle Engine.

## Key incidents

1. Provisioning failure (Moodle / Proctoring)
- Symptom: `provision_dry_run` fails, or live provisioning moves assessment to `failed`.
- Immediate actions:
  - Check CI logs and event bus for the provisioning error.
  - Re-run `python manage.py provision_dry_run --dry-run` locally to reproduce.
  - Inspect `IntegrationRecord` entries for vendor response payloads.
- Recovery:
  - If retryable (network issue), re-run provisioning with exponential backoff.
  - If vendor API changed, escalate to dev-team and open vendor support ticket.
- Escalation: notify CourseAdmin and on-call engineer; consider rolling assessment back to `scheduled` or `failed` state depending on severity.

2. Exam fails to start / proctoring unavailable
- Symptom: `ExamInstance` stuck in `provisioned` and proctoring reports error/timeout.
- Actions:
  - Confirm proctoring provider status and webhooks.
  - Optionally create an offline supervised session or switch to fallback proctoring.
  - If immediate exam is impacted, consider `pause` or `cancel` with admin approval.

3. Active exam integrity alert
- Symptom: proctoring webhook triggers `integrity-violation`.
- Actions:
  - Immediately move `ExamInstance` to `paused` (proctor or admin), preserving session state.
  - Notify instructors and on-call security.
  - Create incident ticket and attach evidence references.

4. Grading pipeline failure
- Symptom: grading jobs fail or are stuck in `grading`.
- Actions:
  - Requeue failed submissions and inspect logs.
  - If systemic, scale grading workers or fix grader code.

5. Break-glass (emergency override)
- Policy:
  - Only SystemAdmin may perform break-glass transitions (requires justification and audit entry).
  - Break-glass overrides should be used only when normal transitions would cause harm (e.g., system outage).
- Logging:
  - All break-glass actions must append a detailed audit entry including the reason, approver, and timestamp.

## Recovery checklist
- Reproduce the error in staging.
- If caused by external vendor, take vendor logs and open a ticket.
- For data-loss risk: consider rolling back to last good `AssessmentVersion` and redeploy.

## Contact matrix
- CourseAdmin: course-level decisions and scheduling.
- IAM/Security: approval and break-glass verification.
- On-call Backend: provisioning / API failures.
- Proctoring vendor support: proctoring incidents.

## Operational tips
- Use the `provision_dry_run` management command for validation before scheduling.
- Keep policy tests (OPA) in CI to detect incompatible Rego changes early.
- Keep audit logs exportable for compliance reviews.
