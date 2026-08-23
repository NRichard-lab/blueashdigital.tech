from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session,
    *,
    event_type: str,
    result: str,
    user_id=None,
    ip_address: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            event_type=event_type,
            result=result,
            ip_address=ip_address,
            target_type=target_type,
            target_id=target_id,
            event_metadata=metadata or {},
        )
    )
