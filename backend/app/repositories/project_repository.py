from typing import Dict, Any, List
from app.repositories.base_repository import BaseRepository

class ProjectRepository(BaseRepository):
    def __init__(self, supabase_client):
        self.client = supabase_client

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new project record into Supabase."""
        response = self.client.table("projects").insert(data).execute()
        if len(response.data) == 0:
            raise RuntimeError("Failed to create project record in Supabase.")
        return response.data[0]

    def get_by_id(self, project_id: str) -> Dict[str, Any]:
        """Retrieve a project record by UUID from Supabase."""
        response = self.client.table("projects").select("*").eq("id", project_id).execute()
        if len(response.data) == 0:
            raise KeyError(f"Project with ID {project_id} not found.")
        return response.data[0]

    def update(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing project record in Supabase."""
        response = self.client.table("projects").update(data).eq("id", project_id).execute()
        if len(response.data) == 0:
            raise KeyError(f"Project with ID {project_id} not found or failed to update.")
        return response.data[0]

    def delete(self, project_id: str) -> bool:
        """Delete a project record from Supabase."""
        response = self.client.table("projects").delete().eq("id", project_id).execute()
        return len(response.data) > 0

    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieve all project records from Supabase."""
        response = self.client.table("projects").select("*").execute()
        return response.data
