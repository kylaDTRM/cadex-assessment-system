# Grade Integrity and Reconciliation System

This system provides comprehensive grade integrity management with conflict detection, reconciliation algorithms, approval workflows, and immutable audit logging.

## Features

### Multi-Source Grade Support
- Support grades from multiple sources (auto-grader, manual grading, external systems)
- Weighted reconciliation algorithms
- Source reliability scoring

### Conflict Detection
- Automatic detection of grade discrepancies
- Statistical anomaly detection
- Configurable conflict thresholds

### Approval Hierarchies
- Multi-step approval workflows
- Role-based approval requirements
- Configurable approval hierarchies per tenant

### Immutable Audit Logs
- Blockchain-style hash chaining for immutability
- Comprehensive audit trail for all grade operations
- Tamper-evident logging

### Grade Freeze and Amendments
- Assessment-level grade freezing
- Post-freeze amendment requests with justification
- Approval-required amendments

## API Endpoints

### Grade Sources
- `GET/POST /api/grade-integrity/grade-sources/` - Manage grade sources
- `GET/PUT/DELETE /api/grade-integrity/grade-sources/{id}/` - Individual source operations

### Grade Records
- `GET/POST /api/grade-integrity/grade-records/` - Manage grade records
- `GET/PUT/DELETE /api/grade-integrity/grade-records/{id}/` - Individual record operations

### Grade Conflicts
- `GET /api/grade-integrity/grade-conflicts/` - List conflicts
- `POST /api/grade-integrity/grade-conflicts/{id}/resolve/` - Resolve conflicts

### Grade Freezes
- `GET/POST /api/grade-integrity/grade-freezes/` - Manage grade freezes
- `GET/PUT/DELETE /api/grade-integrity/grade-freezes/{id}/` - Individual freeze operations

### Grade Amendments
- `GET/POST /api/grade-integrity/grade-amendments/` - Manage amendment requests
- `GET/PUT/DELETE /api/grade-integrity/grade-amendments/{id}/` - Individual amendment operations

### Approval Workflows
- `GET /api/grade-integrity/approval-workflows/` - List workflows
- `POST /api/grade-integrity/approval-workflows/{id}/approve/` - Process approvals

### Reconciliation
- `POST /api/grade-integrity/reconciliation/reconcile_attempt/` - Reconcile grades for an attempt
- `POST /api/grade-integrity/reconciliation/detect_conflicts/` - Detect conflicts for an attempt

## Reconciliation Algorithms

### Available Algorithms

1. **weighted_average** (default)
   - Weights sources by reliability
   - Auto-grader: 0.6, Manual: 0.9, External: 0.7, Reconciliation: 1.0

2. **average**
   - Simple arithmetic mean of all grades

3. **highest_score**
   - Takes the highest score among all sources

4. **lowest_score**
   - Takes the lowest score among all sources

5. **manual_override**
   - Uses manual grading if available, otherwise highest score

### Algorithm Selection

```python
# Example API call
POST /api/grade-integrity/reconciliation/reconcile_attempt/
{
    "attempt_id": "uuid",
    "algorithm": "weighted_average"
}
```

## Conflict Detection

### Conflict Types

1. **score_discrepancy**
   - Standard deviation > 10% of max score

2. **source_conflict**
   - Significant difference between auto-grader and manual grades

3. **anomaly**
   - Statistical outliers (Z-score > 2)

### Detection Example

```python
# Example API call
POST /api/grade-integrity/reconciliation/detect_conflicts/
{
    "attempt_id": "uuid"
}
```

## Approval Workflows

### Workflow Types

1. **grade_amendment**
   - For post-freeze grade changes
   - Requires instructor and department head approval

2. **freeze_override**
   - For unfreezing grades
   - Requires higher-level approval

### Workflow Configuration

Workflows are configured per tenant with required roles:

```json
{
    "required_approvers": ["instructor", "department_head"],
    "expires_at": "2024-12-31T23:59:59Z"
}
```

## Audit Data Schema

### GradeAuditLog Model

```python
class GradeAuditLog(AuditLog):
    action_type = models.CharField(choices=ACTION_TYPES)
    grade_related_resource = models.JSONField(null=True)
```

### Action Types

- `grade_recorded` - New grade recorded
- `conflict_detected` - Conflict detected
- `conflict_resolved` - Conflict resolved
- `grades_frozen` - Grades frozen
- `amendment_requested` - Amendment requested
- `amendment_approved` - Amendment approved
- `workflow_started` - Workflow initiated
- `workflow_completed` - Workflow completed

### Hash Chaining

Each audit log entry includes:
- Previous hash for immutability
- Current hash of the entry
- Timestamp and actor information

## Database Schema

### Core Models

- **GradeSource**: Defines grading sources
- **GradeRecord**: Individual grade entries
- **GradeConflict**: Detected conflicts
- **GradeFreeze**: Grade freezing records
- **GradeAmendment**: Amendment requests
- **ApprovalWorkflow**: Approval processes
- **ApprovalStep**: Individual approval steps
- **GradeAuditLog**: Audit trail

### Key Relationships

- GradeRecord → Attempt (many-to-one)
- GradeRecord → GradeSource (many-to-one)
- GradeConflict → GradeRecord (many-to-many)
- GradeAmendment → GradeRecord (one-to-one)
- ApprovalWorkflow → ApprovalStep (one-to-many)

## Usage Examples

### Recording a Grade

```python
# Create grade source
source = GradeSource.objects.create(
    tenant=tenant,
    name="Auto Grader",
    source_type="auto_grader"
)

# Record grade
GradeRecord.objects.create(
    tenant=tenant,
    attempt=attempt,
    source=source,
    score=85.5,
    max_score=100.0,
    percentage=85.5
)
```

### Reconciling Grades

```python
engine = GradeReconciliationEngine(attempt)
result = engine.reconcile_grades('weighted_average')
# Result contains reconciled score, confidence, etc.
```

### Creating Amendment

```python
amendment = GradeAmendment.objects.create(
    tenant=tenant,
    grade_record=record,
    old_score=85.5,
    new_score=90.0,
    justification="Curve adjustment",
    requested_by=user
)

# Automatically creates approval workflow
workflow_engine = ApprovalWorkflowEngine(tenant)
workflow = workflow_engine.create_amendment_workflow(amendment)
```

## Security Considerations

- All grade changes require proper authentication
- Approval workflows enforce separation of duties
- Audit logs are immutable and tamper-evident
- Grade freezes prevent unauthorized changes
- Multi-tenant isolation ensures data security

## Monitoring and Alerts

- Automatic alerts for detected conflicts
- Dashboard for approval queue management
- Audit log monitoring for compliance
- Performance metrics for reconciliation algorithms

## Future Enhancements

- Machine learning-based anomaly detection
- Predictive conflict resolution
- Integration with external grading systems
- Advanced approval routing based on grade changes
- Real-time grade reconciliation
