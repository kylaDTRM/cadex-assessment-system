"""Simple proctoring adapter stub.
Real adapters should implement API calls for session creation and webhook handling.
"""

def request_session(exam_instance, dry_run: bool = True) -> str:
    """Request a proctoring session and return session id."""
    if dry_run:
        return f"dry-proctor-{exam_instance.id}"
    # TODO: call proctoring vendor
    return "proctor-session-id"


def check_session_status(session_id: str, dry_run: bool = True) -> dict:
    if dry_run:
        return {'status': 'ready'}
    # TODO: implement
    return {'status': 'unknown'}
