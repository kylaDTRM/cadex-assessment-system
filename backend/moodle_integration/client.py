"""Minimal Moodle integration stubs for provisioning and grade operations.
These functions are intentionally simple and can be replaced by real implementations
that call Moodle webservices or admin CLI.
"""


def create_lti_resource(assessment_version, dry_run: bool = True) -> str:
    """Create an LTI resource for the assessment and return resource id."""
    # In real impl: call moodle webservice or use CLI to create resource
    if dry_run:
        return f"dry-lti-{assessment_version.id}"
    # TODO: actual provisioning
    return "lti-resource-id"


def create_grade_item(assessment_version, dry_run: bool = True) -> str:
    """Create gradebook item and return id."""
    if dry_run:
        return f"dry-grade-{assessment_version.id}"
    # TODO: real call
    return "grade-item-id"


def provision_for_assessment(assessment_version, dry_run: bool = True) -> dict:
    """Provision LTI + grade items and return a dict of resource ids."""
    lti = create_lti_resource(assessment_version, dry_run=dry_run)
    grade = create_grade_item(assessment_version, dry_run=dry_run)
    return {'lti_resource_id': lti, 'grade_item_id': grade}


def update_grade(itemid, userid, grade, client_request_id=None, dry_run: bool = True) -> bool:
    """Update grade in Moodle; returns True on success."""
    if dry_run:
        return True
    # TODO: call moodle REST webservice
    return True
