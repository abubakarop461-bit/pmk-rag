from typing import Dict, Any, Optional
from loguru import logger

class MetadataFilterService:
    def build_filters(self, project_id: str, user_filters: Optional[Dict[str, Any]] = None, auto_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Combines project scope, auto-detected intent filters, and user overrides.
        """
        # Merge dictionaries (user filters override auto-filters on conflicts)
        merged = {**(auto_filters or {}), **(user_filters or {})}
        merged["project_id"] = project_id
        
        # Strip out null values
        cleaned = {k: v for k, v in merged.items() if v is not None}
        logger.info(f"Metadata filters configured: {cleaned}")
        return cleaned
