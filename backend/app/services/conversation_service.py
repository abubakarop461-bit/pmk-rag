from typing import List, Dict, Any, Optional
from loguru import logger
from app.repositories.chat_repository import ChatRepository
from app.services.conversation_title_generator import ConversationTitleGenerator

class ConversationService:
    def __init__(self, chat_repository: ChatRepository):
        self.chat_repo = chat_repository
        self.title_gen = ConversationTitleGenerator()

    def create_chat_session(self, project_id: str, title: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new conversation session.
        """
        logger.info(f"Creating chat session for project {project_id} with title '{title}'...")
        return self.chat_repo.create_session(project_id, title, user_id)

    def rename_chat_session(self, session_id: str, new_title: str) -> Dict[str, Any]:
        """
        Renames an existing chat session thread.
        """
        logger.info(f"Renaming chat session {session_id} to '{new_title}'...")
        return self.chat_repo.update_session_title(session_id, new_title)

    def list_sessions_for_project(self, project_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists all chat sessions belonging to a project.
        """
        logger.info(f"Listing chat sessions for project {project_id}...")
        return self.chat_repo.list_sessions_by_project(project_id, user_id)

    def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves session details.
        """
        return self.chat_repo.get_session(session_id)

    def delete_chat_session(self, session_id: str) -> bool:
        """
        Deletes a chat session.
        """
        return self.chat_repo.delete_session(session_id)

    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all messages for a session.
        """
        return self.chat_repo.get_messages_by_session(session_id)

    def save_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        citations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Saves a message in the database. Auto-titles session if this is the first user message.
        """
        # Auto-title heuristics check
        if role == "user":
            existing_messages = self.chat_repo.get_messages_by_session(session_id)
            if not existing_messages:
                # Generate and save heuristic title
                new_title = self.title_gen.generate_title(content)
                try:
                    self.chat_repo.update_session_title(session_id, new_title)
                except Exception as title_err:
                    logger.warning(f"Failed to auto-update session title: {title_err}")
                    
        return self.chat_repo.create_message(session_id, role, content, citations)
