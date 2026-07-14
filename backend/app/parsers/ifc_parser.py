import os
import re
from typing import List
from langchain_core.documents import Document
from loguru import logger

class IfcParser:
    def parse(self, file_path: str) -> List[Document]:
        """
        Parses an Industry Foundation Classes (.ifc) file.
        Attempts to use ifcopenshell if available, falling back to a STEP text line parser if missing.
        """
        logger.info(f"IfcParser parsing file: {file_path}")
        
        try:
            import ifcopenshell
            logger.info("ifcopenshell available. Initializing standard model parser...")
            model = ifcopenshell.open(file_path)
            
            project_info = model.by_type("IfcProject")
            proj_name = project_info[0].Name if project_info else "Unknown Project"
            
            # Element counts
            walls = len(model.by_type("IfcWall")) + len(model.by_type("IfcWallStandardCase"))
            columns = len(model.by_type("IfcColumn"))
            beams = len(model.by_type("IfcBeam"))
            slabs = len(model.by_type("IfcSlab"))
            doors = len(model.by_type("IfcDoor"))
            windows = len(model.by_type("IfcWindow"))
            
            # Levels/Storeys
            storeys = [s.Name for s in model.by_type("IfcBuildingStorey")]
            # Materials
            materials = list(set([m.Name for m in model.by_type("IfcMaterial") if m.Name]))
            
            description = (
                f"IFC Building Information Model (BIM)\n"
                f"Project Name: {proj_name}\n"
                f"Elements Summary:\n"
                f"  - Walls: {walls}\n"
                f"  - Columns: {columns}\n"
                f"  - Beams: {beams}\n"
                f"  - Slabs: {slabs}\n"
                f"  - Doors: {doors}\n"
                f"  - Windows: {windows}\n\n"
                f"Building Storeys / Levels: {', '.join(storeys) if storeys else 'None'}\n"
                f"Materials List: {', '.join(materials) if materials else 'None'}\n"
            )
            
        except Exception as e:
            logger.info(f"Standard ifcopenshell import/load failed ({e}). Initializing STEP fallback parser...")
            description = self._parse_step_fallback(file_path)
            
        return [
            Document(
                page_content=description,
                metadata={
                    "source": os.path.basename(file_path),
                    "page": 1
                }
            )
        ]

    def _parse_step_fallback(self, file_path: str) -> str:
        """
        Lightweight fallback parsing STEP line elements inside .ifc file using regular expressions.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            # Regex element matching
            walls = len(re.findall(r"IFCWALL(STANDARDCASE)?\b", content, re.IGNORECASE))
            columns = len(re.findall(r"IFCCOLUMN\b", content, re.IGNORECASE))
            beams = len(re.findall(r"IFCBEAM\b", content, re.IGNORECASE))
            slabs = len(re.findall(r"IFCSLAB\b", content, re.IGNORECASE))
            doors = len(re.findall(r"IFCDOOR\b", content, re.IGNORECASE))
            windows = len(re.findall(r"IFCWINDOW\b", content, re.IGNORECASE))
            
            # Extract Project name from FILE_NAME or IFCPROJECT
            proj_match = re.search(r"FILE_NAME\(\s*'([^']+)'", content, re.IGNORECASE)
            proj_name = proj_match.group(1) if proj_match else os.path.basename(file_path)
            
            # Extract materials
            materials = re.findall(r"IFCMATERIAL\(\s*'([^']+)'", content, re.IGNORECASE)
            unique_materials = list(set(materials))
            
            # Extract storeys
            storeys = re.findall(r"IFCBUILDINGSTOREY\(\s*'[^']*'\s*,\s*\$\s*,\s*'([^']+)'", content, re.IGNORECASE)
            if not storeys:
                # Alternate pattern
                storeys = re.findall(r"IFCBUILDINGSTOREY\(\s*'[^']*'\s*,\s*[^,]*\s*,\s*'([^']+)'", content, re.IGNORECASE)
            unique_storeys = list(set(storeys))
            
            return (
                f"IFC Building Information Model (BIM) [Parsed via STEP Fallback]\n"
                f"Model Name: {proj_name}\n"
                f"Elements Summary:\n"
                f"  - Walls: {walls}\n"
                f"  - Columns: {columns}\n"
                f"  - Beams: {beams}\n"
                f"  - Slabs: {slabs}\n"
                f"  - Doors: {doors}\n"
                f"  - Windows: {windows}\n\n"
                f"Building Storeys / Levels: {', '.join(unique_storeys) if unique_storeys else 'None'}\n"
                f"Materials List: {', '.join(unique_materials) if unique_materials else 'None'}\n"
            )
        except Exception as err:
            logger.error(f"STEP fallback parser crashed: {err}")
            return f"IFC Model: Failed to parse structural data. Error: {err}"
