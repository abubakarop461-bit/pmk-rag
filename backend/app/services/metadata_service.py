import os
import re
from typing import Dict, Any, List
from langchain_core.documents import Document
from loguru import logger
from app.services.drawing_extractor import DrawingExtractorService

class MetadataService:
    def __init__(self):
        self.drawing_extractor = DrawingExtractorService()

    def extract_metadata(
        self, 
        file_path: str, 
        mime_type: str, 
        doc_type: str, 
        revision_number: str, 
        project_id: str, 
        parsed_docs: List[Document]
    ) -> Dict[str, Any]:
        """
        Compiles document properties, OS details, best-effort language check, 
        and extracts construction-specific metadata for engineering drawings and models.
        """
        logger.info(f"MetadataService extracting metadata properties for: {file_path}")
        
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        page_count = len(parsed_docs)
        
        # Language detection
        language = "en"
        if page_count > 0:
            sample_text = parsed_docs[0].page_content.lower()[:1000]
            if any(word in sample_text for word in [" le ", " la ", " les ", " et ", " est "]):
                language = "fr"
            elif any(word in sample_text for word in [" der ", " die ", " das ", " und ", " ist "]):
                language = "de"
            elif any(word in sample_text for word in [" el ", " la ", " los ", " y ", " es "]):
                language = "es"
                
        # File date statistics retrieval
        os_created = None
        os_modified = None
        try:
            stat_info = os.stat(file_path)
            os_created = stat_info.st_ctime
            os_modified = stat_info.st_mtime
        except Exception as e:
            logger.warning(f"Could not retrieve OS file statistics: {e}")

        # Basic metadata payload
        meta_properties = {
            "file_name": filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "page_count": page_count,
            "language": language,
            "document_type": doc_type,
            "revision": revision_number,
            "project_id": project_id,
            "drawing_number": None,
            "discipline": None,
            "sheet": None,
            "level": None
        }
        
        # If it is an IFC file, parse project info from STEP details
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".ifc" and page_count > 0:
            # Pick up materials and levels details from the parsed document content
            content = parsed_docs[0].page_content
            
            # Retrieve levels
            levels_match = re.search(r"Building Storeys / Levels:\s*([^\n]+)", content)
            if levels_match:
                meta_properties["level"] = levels_match.group(1)
                
            # Retrieve project name
            proj_match = re.search(r"Project Name:\s*([^\n]+)", content)
            if proj_match:
                meta_properties["drawing_number"] = proj_match.group(1)
            
            meta_properties["discipline"] = "BIM Model"

        # If drawing, run GOST title block extraction
        if doc_type.lower() == "drawing":
            logger.info("Triggering GOST Title Block extractor...")
            try:
                drawing_meta = self.drawing_extractor.extract_title_block_metadata(file_path, doc_type)
                meta_properties.update({
                    "drawing_number": drawing_meta.get("drawing_number") or meta_properties.get("drawing_number"),
                    "discipline": drawing_meta.get("discipline") or meta_properties.get("discipline"),
                    "sheet": drawing_meta.get("sheet") or meta_properties.get("sheet"),
                    "level": drawing_meta.get("level") or meta_properties.get("level")
                })
                # If title block specifies a revision, override the default upload revision
                if drawing_meta.get("revision"):
                    meta_properties["revision"] = drawing_meta["revision"]
            except Exception as extract_err:
                logger.error(f"Drawing extractor failed: {extract_err}")

        if os_created:
            meta_properties["creation_date"] = str(os_created)
        if os_modified:
            meta_properties["modification_date"] = str(os_modified)
            
        logger.info(f"MetadataService completed. Compiled payload: {meta_properties}")
        return meta_properties
