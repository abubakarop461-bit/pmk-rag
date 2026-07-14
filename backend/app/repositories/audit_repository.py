from typing import Dict, Any, Optional
from app.repositories.base_repository import BaseRepository

class AuditRepository(BaseRepository):
    def __init__(self, supabase_client):
        self.client = supabase_client

    def log_action(self, user_id: Optional[str], action: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts an event record into the audit_logs table."""
        data = {
            "user_id": user_id,
            "action": action,
            "details": details
        }
        response = self.client.table("audit_logs").insert(data).execute()
        if len(response.data) == 0:
            raise RuntimeError("Failed to write audit log record.")
        return response.data[0]
