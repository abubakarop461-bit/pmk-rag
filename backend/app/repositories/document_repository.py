from typing import Dict, Any, List, Optional
from app.repositories.base_repository import BaseRepository

class DocumentRepository(BaseRepository):
    def __init__(self, supabase_client):
        self.client = supabase_client

    def create_document(self, project_id: str, document_name: str, document_type: str, ai_classified_type: Optional[str] = None) -> Dict[str, Any]:
        """Creates a logical document record."""
        data = {
            "project_id": project_id,
            "document_name": document_name,
            "document_type": document_type,
            "ai_classified_type": ai_classified_type
        }
        response = self.client.table("documents").insert(data).execute()
        if len(response.data) == 0:
            raise RuntimeError("Failed to create document record.")
        return response.data[0]

    def get_document_by_name(self, project_id: str, document_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a logical document by its project ID and name."""
        response = self.client.table("documents").select("*").eq("project_id", project_id).eq("document_name", document_name).execute()
        if len(response.data) == 0:
            return None
        return response.data[0]

    def get_project_documents(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all documents in a project, including their latest revision.
        """
        # Fetch documents and all their revisions in a single joined select
        response = self.client.table("documents").select("*, document_revisions(*)").eq("project_id", project_id).execute()
        
        docs = []
        for doc in response.data:
            revisions = doc.get("document_revisions", [])
            # Sort revisions by creation date or revision string to find the latest
            if revisions:
                # Simple sort: latest created_at is the last element
                revisions.sort(key=lambda r: r.get("created_at", ""))
                doc["latest_revision"] = revisions[-1]
            else:
                doc["latest_revision"] = None
            
            # Clean up the nested list for serialization
            if "document_revisions" in doc:
                del doc["document_revisions"]
            docs.append(doc)
            
        return docs

    def create_revision(self, revision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a physical file revision record."""
        response = self.client.table("document_revisions").insert(revision_data).execute()
        if len(response.data) == 0:
            raise RuntimeError("Failed to create document revision record.")
        return response.data[0]

    def get_revision_by_checksum(self, document_id: str, checksum: str) -> Optional[Dict[str, Any]]:
        """Check if a file with the same checksum has already been uploaded for this document."""
        response = self.client.table("document_revisions").select("*").eq("document_id", document_id).eq("checksum", checksum).execute()
        if len(response.data) == 0:
            return None
        return response.data[0]

    def get_revision_by_number(self, document_id: str, revision_number: str) -> Optional[Dict[str, Any]]:
        """Check if a specific revision string already exists for this document."""
        response = self.client.table("document_revisions").select("*").eq("document_id", document_id).eq("revision_number", revision_number).execute()
        if len(response.data) == 0:
            return None
        return response.data[0]

    def get_document_revisions(self, document_id: str) -> List[Dict[str, Any]]:
        """Lists all revisions for a specific logical document, ordered by creation date."""
        response = self.client.table("document_revisions").select("*").eq("document_id", document_id).order("created_at", desc=False).execute()
        return response.data

    def delete_document(self, document_id: str) -> bool:
        """Deletes a document and its cascade-linked revisions."""
        response = self.client.table("documents").delete().eq("id", document_id).execute()
        return len(response.data) > 0

    def get_any_ready_revision_by_checksum(self, checksum: str) -> Optional[Dict[str, Any]]:
        """Check if any document revision across the system has the same checksum and is ready."""
        response = self.client.table("document_revisions").select("*, documents(project_id)").eq("checksum", checksum).eq("processing_status", "ready").execute()
        if len(response.data) == 0:
            return None
        return response.data[0]

