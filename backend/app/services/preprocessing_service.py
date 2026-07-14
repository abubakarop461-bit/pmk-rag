import re
from typing import Dict, Any, Tuple
from loguru import logger

class PreprocessingService:
    def preprocess_query(self, query: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Cleans search queries, classifies user intent (regex/heuristics),
        and extracts auto-applicable metadata filters.
        
        Returns:
            Tuple[clean_query, detected_intent, injected_filters]
        """
        if not query:
            return "", "semantic_search", {}
            
        # Clean query: strip outer spaces and normalize inner whitespace
        clean_query = " ".join(query.strip().split())
        query_lower = clean_query.lower()
        
        detected_intent = "semantic_search"
        injected_filters = {}
        
        # Regex lookups for document type categories
        if any(w in query_lower for w in ["drawing", "drawings", "drw", "blueprint", "plan", "elevation"]):
            detected_intent = "drawing_search"
            injected_filters["document_type"] = "drawing"
        elif any(w in query_lower for w in ["contract", "agreement", "clause", "article", "liability", "term"]):
            detected_intent = "contract_search"
            injected_filters["document_type"] = "contract"
        elif any(w in query_lower for w in ["boq", "quantities", "quantity", "rate", "bill of quantities"]):
            detected_intent = "boq_search"
            injected_filters["document_type"] = "BOQ"
        elif any(w in query_lower for w in ["spec", "specs", "specification", "specifications", "standard"]):
            detected_intent = "specification_search"
            injected_filters["document_type"] = "specification"
        elif any(w in query_lower for w in ["rfi", "information request"]):
            detected_intent = "rfi_search"
            injected_filters["document_type"] = "RFI"
        elif any(w in query_lower for w in ["rev", "revision", "version"]):
            detected_intent = "revision_search"
            
        # Log references detected
        logger.info(f"Query Preprocessing: '{clean_query}' -> Intent: {detected_intent}, Injected Filters: {injected_filters}")
        return clean_query, detected_intent, injected_filters
