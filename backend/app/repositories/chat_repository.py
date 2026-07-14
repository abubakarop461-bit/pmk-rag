from typing import List, Dict, Any, Optional
from loguru import logger
from postgrest.exceptions import APIError
from app.core.supabase import get_supabase_client

class ChatRepository:
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or get_supabase_client()

    def create_session(self, project_id: str, title: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new chat session thread in Supabase.
        """
        try:
            payload = {
                "project_id": project_id,
                "title": title,
            }
            if user_id:
                payload["user_id"] = user_id
                
            res = self.supabase.table("chat_sessions").insert(payload).execute()
            if not res.data:
                raise RuntimeError("Failed to create chat session.")
            logger.info(f"Created chat session: {res.data[0]['id']} - '{title}'")
            return res.data[0]
        except APIError as e:
            logger.error(f"Supabase API Error creating chat session: {e.message}")
            raise RuntimeError(f"Database error: {e.message}")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single chat session metadata.
        """
        try:
            res = self.supabase.table("chat_sessions").select("*").eq("id", session_id).execute()
            return res.data[0] if res.data else None
        except APIError as e:
            logger.error(f"Supabase API Error retrieving chat session {session_id}: {e.message}")
            return None

    def list_sessions_by_project(self, project_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists all chat session threads for a given project.
        """
        try:
            q = self.supabase.table("chat_sessions").select("*").eq("project_id", project_id)
            if user_id:
                q = q.eq("user_id", user_id)
            res = q.order("created_at", desc=True).execute()
            return res.data or []
        except APIError as e:
            logger.error(f"Supabase API Error listing sessions: {e.message}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Deletes a chat session thread (cascades message deletes).
        """
        try:
            res = self.supabase.table("chat_sessions").delete().eq("id", session_id).execute()
            logger.info(f"Deleted chat session {session_id}")
            return len(res.data) > 0
        except APIError as e:
            logger.error(f"Supabase API Error deleting chat session {session_id}: {e.message}")
            return False

    def create_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        citations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Appends a message (user or assistant) to a chat session history.
        """
        try:
            payload = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "citations": citations or []
            }
            res = self.supabase.table("chat_messages").insert(payload).execute()
            if not res.data:
                raise RuntimeError("Failed to insert chat message.")
            return res.data[0]
        except APIError as e:
            logger.error(f"Supabase API Error inserting message: {e.message}")
            raise RuntimeError(f"Database error: {e.message}")

    def get_messages_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all messages for a given session sorted chronologically.
        """
        try:
            res = self.supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).execute()
            return res.data or []
        except APIError as e:
            logger.error(f"Supabase API Error getting messages: {e.message}")
            return []

    def update_session_title(self, session_id: str, title: str) -> Dict[str, Any]:
        """
        Updates the title of an existing chat session.
        """
        try:
            res = self.supabase.table("chat_sessions").update({"title": title}).eq("id", session_id).execute()
            if not res.data:
                raise RuntimeError("Failed to update session title.")
            logger.info(f"Updated session title to '{title}' for session {session_id}")
            return res.data[0]
        except APIError as e:
            logger.error(f"Supabase API Error updating session title: {e.message}")
            raise RuntimeError(f"Database error: {e.message}")

    def create_analytics_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Creates a new analytics tracking row in Supabase. Fails gracefully.
        """
        try:
            res = self.supabase.table("chat_analytics").insert(entry).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.warning(f"Supabase failed to record RAG chat analytics (Graceful Fallback): {e}")
            return None
