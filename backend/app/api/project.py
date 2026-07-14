from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.supabase import get_supabase_client
from app.core.security import get_current_user
from app.repositories.project_repository import ProjectRepository
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])

def get_project_repo() -> ProjectRepository:
    client = get_supabase_client()
    return ProjectRepository(client)

def get_audit_service() -> AuditService:
    client = get_supabase_client()
    repo = AuditRepository(client)
    return AuditService(repo)

@router.get("", response_model=List[ProjectOut])
async def list_projects(
    repo: ProjectRepository = Depends(get_project_repo),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve all construction projects."""
    try:
        return repo.get_all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {e}"
        )

@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    repo: ProjectRepository = Depends(get_project_repo),
    audit: AuditService = Depends(get_audit_service),
    current_user: dict = Depends(get_current_user)
):
    """Create a new construction project and log an audit event."""
    try:
        project_data = project_in.model_dump()
        project_data["created_by"] = current_user["id"]
        created = repo.create(project_data)
        
        # Log event
        audit.log_event(
            user_id=current_user["id"],
            action="project_created",
            details={
                "project_id": created["id"],
                "project_number": created["project_number"],
                "project_name": created["name"]
            }
        )
        return created
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create project: {e}"
        )

@router.get("/{id}", response_model=ProjectOut)
async def get_project(
    id: str,
    repo: ProjectRepository = Depends(get_project_repo),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve a project by ID."""
    try:
        return repo.get_by_id(id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval error: {e}"
        )

@router.put("/{id}", response_model=ProjectOut)
async def update_project(
    id: str,
    project_in: ProjectUpdate,
    repo: ProjectRepository = Depends(get_project_repo),
    audit: AuditService = Depends(get_audit_service),
    current_user: dict = Depends(get_current_user)
):
    """Update a project and log an audit event."""
    try:
        update_data = project_in.model_dump(exclude_unset=True)
        updated = repo.update(id, update_data)
        
        # Log event
        audit.log_event(
            user_id=current_user["id"],
            action="project_updated",
            details={
                "project_id": id,
                "updated_fields": list(update_data.keys())
            }
        )
        return updated
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update project: {e}"
        )

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    id: str,
    repo: ProjectRepository = Depends(get_project_repo),
    audit: AuditService = Depends(get_audit_service),
    current_user: dict = Depends(get_current_user)
):
    """Delete a project and log an audit event."""
    try:
        # Fetch details first for logging
        proj = repo.get_by_id(id)
        success = repo.delete(id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delete action failed."
            )
            
        # Log event
        audit.log_event(
            user_id=current_user["id"],
            action="project_deleted",
            details={
                "project_id": id,
                "project_number": proj.get("project_number"),
                "project_name": proj.get("name")
            }
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {e}"
        )
