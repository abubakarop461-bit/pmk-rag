from app.repositories.audit_repository import AuditRepository

class AuditService:
    def __init__(self, audit_repository: AuditRepository):
        self.repo = audit_repository

    def log_event(self, user_id: str, action: str, details: dict):
        return self.repo.log_action(user_id, action, details)
