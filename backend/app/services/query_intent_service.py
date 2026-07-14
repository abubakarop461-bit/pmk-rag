import re
from typing import Dict, Any, Tuple
from loguru import logger

class QueryIntentService:
    def detect_intent(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Classifies construction query intent and extracts auto-filters 
        for document types, drawing numbers, disciplines, and storey levels.
        """
        if not query:
            return "semantic_search", {}
            
        query_lower = query.lower()
        intent = "semantic_search"
        auto_filters = {}
        
        # 1. Classify document type intent
        if any(w in query_lower for w in ["drawing", "drawings", "drw", "blueprint", "plan", "elevation"]):
            intent = "drawing_search"
            auto_filters["document_type"] = "drawing"
        elif any(w in query_lower for w in ["contract", "agreement", "clause", "article", "liability", "term"]):
            intent = "contract_search"
            auto_filters["document_type"] = "contract"
        elif any(w in query_lower for w in ["boq", "quantities", "quantity", "rate", "bill of quantities"]):
            intent = "boq_search"
            auto_filters["document_type"] = "BOQ"
        elif any(w in query_lower for w in ["spec", "specs", "specification", "specifications", "standard"]):
            intent = "specification_search"
            auto_filters["document_type"] = "specification"
        elif any(w in query_lower for w in ["rfi", "information request"]):
            intent = "rfi_search"
            auto_filters["document_type"] = "RFI"
        elif any(w in query_lower for w in ["rev", "revision", "version"]):
            intent = "revision_search"
            
        # 2. Extract Construction-Specific Filters
        
        # A. Discipline detection
        if any(w in query_lower for w in ["architectural", "architecture", "arch"]):
            auto_filters["discipline"] = "Architectural"
        elif any(w in query_lower for w in ["structural", "structure", "struc", "civil"]):
            auto_filters["discipline"] = "Structural"
        elif any(w in query_lower for w in ["hvac", "heating", "mechanical", "ventilation"]):
            auto_filters["discipline"] = "HVAC"
        elif any(w in query_lower for w in ["electrical", "electric"]):
            auto_filters["discipline"] = "Electrical"
        elif any(w in query_lower for w in ["plumbing", "plumb", "vk"]):
            auto_filters["discipline"] = "Plumbing"
            
        # B. Level / Floor detection (e.g. Level 2, Floor 3, L4, F5)
        lvl_match = re.search(r"\b(?:level|floor|storey|L|F)\.?\s*(\d+)\b", query, re.IGNORECASE)
        if lvl_match:
            # We match the level number and standardise it as "Level {X}" or store the digit
            auto_filters["level"] = lvl_match.group(1)
            
        # C. Drawing Number detection (matches XX-XX-XX-AR standard formats)
        draw_match = re.search(r"\b[A-Z0-9]{3,}\-[A-Z0-9\-]{3,}\-[A-Z0-9\-]+\b", query)
        if draw_match:
            auto_filters["drawing_number"] = draw_match.group(0)
            
        logger.info(f"Query Intent Classified: '{query}' -> {intent} (Auto-filters: {auto_filters})")
        return intent, auto_filters
