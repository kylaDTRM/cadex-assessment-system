# Examination Integrity Incident Backend

A comprehensive system for monitoring, detecting, and managing examination integrity incidents with automated risk scoring, evidence retention, and review workflows.

## Features

### Proctoring Signal Ingestion
- **Real-time Event Processing**: Ingest proctoring signals from external monitoring systems
- **Event Classification**: Categorize events by type and severity
- **Metadata Enrichment**: Store detailed event context and evidence

### Rule-Based Risk Scoring
- **Configurable Rules**: Define custom risk assessment rules
- **Multi-Criteria Evaluation**: Count thresholds, pattern matching, severity weighting
- **Dynamic Scoring**: Real-time risk calculation with time windows

### Incident Escalation Workflows
- **Automated Detection**: Create incidents from risk rule violations
- **Multi-Step Reviews**: Configurable approval and escalation processes
- **Role-Based Assignments**: Assign reviewers based on organizational hierarchy

### Evidence Management
- **Secure Storage**: Store screenshots, videos, and system logs
- **Retention Policies**: Automated cleanup based on risk level and policy
- **Access Control**: Restricted access to sensitive evidence

## Event Schema

### IntegrityEvent Model

```json
{
  "id": "uuid",
  "tenant": "uuid",
  "event_type": "face_not_visible|multiple_faces|tab_switch|copy_paste|...",
  "severity": "low|medium|high|critical",
  "timestamp": "2024-01-01T12:00:00Z",
  "proctoring_session_id": "string",
  "attempt": "uuid",
  "event_data": {
    "face_detected": false,
    "confidence": 0.95,
    "faces_count": 2
  },
  "metadata": {},
  "screenshot_url": "https://...",
  "video_clip_url": "https://...",
  "processed": true
}
```

### Event Types
- `face_not_visible` - No face detected in frame
- `multiple_faces` - Multiple faces detected
- `tab_switch` - Browser tab/window change
- `copy_paste` - Copy/paste operations detected
- `external_device` - External devices connected
- `audio_anomaly` - Unusual audio patterns
- `network_issue` - Connectivity problems
- `suspicious_behavior` - AI-detected suspicious actions
- `system_integrity` - System tampering detected
- `custom` - Custom event types

## Scoring Logic

### RiskRule Model

```json
{
  "id": "uuid",
  "tenant": "uuid",
  "name": "Multiple Face Detections",
  "rule_type": "event_count|event_pattern|severity_weighted|time_window|custom",
  "event_type": "multiple_faces",
  "operator": "gt|gte|lt|lte|eq|contains|regex",
  "threshold_value": "3",
  "parameters": {
    "time_window_hours": 1,
    "pattern": "regex_pattern"
  },
  "base_score": 25.00,
  "score_multiplier": 1.0,
  "is_active": true,
  "priority": 0
}
```

### Scoring Algorithms

#### Event Count Rules
```python
# Example: Alert if > 3 tab switches in 1 hour
if event_count > threshold:
    risk_score += base_score * multiplier
```

#### Severity Weighted Rules
```python
severity_weights = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
total_weight = sum(weights for event in time_window)
if total_weight >= threshold:
    risk_score += base_score * multiplier
```

#### Risk Level Calculation
```python
def calculate_risk_level(score):
    if score >= 80: return 'critical'
    elif score >= 60: return 'high'
    elif score >= 40: return 'medium'
    else: return 'low'
```

## Review Workflows

### Workflow Types
- `incident_review` - Standard incident investigation
- `escalation` - Higher-level review for critical incidents
- `appeal` - Student appeal process

### ReviewWorkflow Model

```json
{
  "id": "uuid",
  "tenant": "uuid",
  "workflow_type": "incident_review",
  "incident": "uuid",
  "required_reviewers": ["exam_integrity_officer", "department_head"],
  "escalation_rules": {
    "high_risk": {"escalate_to": "dean", "time_limit": 24},
    "critical_risk": {"escalate_to": "academic_integrity_committee", "time_limit": 4}
  },
  "status": "pending|in_progress|completed|cancelled",
  "current_step": "initial_review",
  "assigned_to": "uuid",
  "due_date": "2024-01-02T12:00:00Z"
}
```

### Review Steps

```json
{
  "id": "uuid",
  "workflow": "uuid",
  "step_name": "Initial Review",
  "step_type": "review|approval|escalation|notification",
  "status": "pending|in_progress|completed|skipped|failed",
  "assigned_to": "uuid",
  "instructions": "Review evidence and determine next steps",
  "required_actions": ["review_evidence", "contact_student"],
  "time_limit_hours": 24,
  "order": 1
}
```

## API Endpoints

### Event Ingestion
```
POST /api/exam-integrity/events/ingest/
{
  "proctoring_session_id": "session-123",
  "event_type": "face_not_visible",
  "severity": "high",
  "event_data": {"confidence": 0.95},
  "metadata": {"camera_id": "cam-1"}
}
```

### Incident Management
```
GET /api/exam-integrity/incidents/ - List incidents
POST /api/exam-integrity/incidents/{id}/resolve/ - Resolve incident
POST /api/exam-integrity/incidents/{id}/calculate_risk/ - Recalculate risk
```

### Risk Rules
```
GET /api/exam-integrity/risk-rules/ - List rules
POST /api/exam-integrity/risk-rules/ - Create rule
PUT /api/exam-integrity/risk-rules/{id}/ - Update rule
```

### Evidence Management
```
GET /api/exam-integrity/evidence/ - List evidence
POST /api/exam-integrity/evidence/cleanup_expired/ - Cleanup expired files
```

### Workflow Management
```
GET /api/exam-integrity/workflows/ - List workflows
POST /api/exam-integrity/workflows/{id}/perform_action/ - Execute workflow action
```

## Evidence Retention Policies

### Retention Tiers
- **Minimal**: 30 days - Low-risk incidents
- **Standard**: 180 days - Medium-risk incidents
- **Extended**: 365 days - High-risk incidents
- **Permanent**: 7 years - Critical incidents requiring legal retention

### Automatic Cleanup
```python
# Daily cleanup job
expired_evidence = Evidence.objects.filter(
    retention_until__lt=timezone.now(),
    auto_delete=True
)
# Delete from storage and mark as deleted
```

## Integration Points

### Proctoring System Integration
```python
# Webhook endpoint for real-time events
@app.route('/webhook/proctoring', methods=['POST'])
def proctoring_webhook():
    data = request.json
    service = IntegrityEventIngestionService()
    event = service.ingest_event(
        tenant=get_tenant_from_request(),
        proctoring_session_id=data['session_id'],
        event_type=data['event_type'],
        event_data=data['event_data']
    )
    return {'status': 'processed'}
```

### Assessment System Integration
```python
# Signal when attempt is submitted
@receiver(post_save, sender=Attempt)
def on_attempt_submitted(sender, instance, **kwargs):
    if instance.status == 'submitted':
        # Final risk assessment
        risk_service = RiskScoringService(tenant)
        final_risk = risk_service.calculate_risk_score(instance)
        # Flag for manual review if high risk
```

## Security Considerations

### Data Separation
- Integrity data completely separated from grade data
- No cross-contamination of sensitive monitoring information
- Encrypted evidence storage with access logging

### Access Control
- Role-based permissions for incident review
- Audit logging of all evidence access
- Multi-factor authentication for sensitive operations

### Privacy Compliance
- Automatic evidence deletion per retention policies
- Anonymized reporting for aggregate analytics
- Student notification requirements for incidents

## Monitoring & Analytics

### Key Metrics
- Incident detection rate
- False positive/negative rates
- Average resolution time
- Risk score distribution
- Evidence retention compliance

### Alerts & Notifications
- Real-time alerts for critical incidents
- Escalation notifications
- Evidence cleanup warnings
- Policy compliance reports

## Configuration Examples

### Basic Risk Rules Setup
```python
# Create standard rules
RiskRule.objects.create(
    tenant=tenant,
    name="Multiple Faces",
    rule_type="event_count",
    event_type="multiple_faces",
    operator="gte",
    threshold_value="2",
    base_score=30.00
)

RiskRule.objects.create(
    tenant=tenant,
    name="Face Disappearance",
    rule_type="event_count",
    event_type="face_not_visible",
    operator="gte",
    threshold_value="5",
    base_score=25.00
)
```

### Workflow Configuration
```python
# Configure review workflow
workflow_config = {
    'initial_review': {
        'assignee': 'exam_integrity_officer',
        'time_limit': 24,
        'actions': ['review_evidence', 'assess_risk']
    },
    'supervisor_review': {
        'assignee': 'department_head',
        'time_limit': 48,
        'actions': ['approve', 'escalate', 'dismiss']
    }
}
```

This system provides a robust foundation for maintaining examination integrity with automated monitoring, intelligent risk assessment, and comprehensive incident management workflows.
