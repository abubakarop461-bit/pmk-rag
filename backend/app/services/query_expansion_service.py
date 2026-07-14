from loguru import logger

class QueryExpansionService:
    def __init__(self):
        # Configurable synonym map for local matching expansion
        self.synonym_map = {
            "boq": ["bill of quantities"],
            "bill of quantities": ["boq"],
            "rfi": ["request for information"],
            "request for information": ["rfi"],
            "fire": ["fire protection", "fire alarm", "fire fighting"],
            "specification": ["spec"],
            "spec": ["specification"],
            "drawings": ["drawing"],
            "drawing": ["drawings"]
        }

    def expand(self, query: str) -> str:
        """
        Expands keyword terms inside the query using the synonym dictionary.
        """
        if not query:
            return ""
            
        words = query.lower().split()
        expanded_terms = []
        for word in words:
            expanded_terms.append(word)
            if word in self.synonym_map:
                expanded_terms.extend(self.synonym_map[word])
                
        # De-duplicate words while keeping order
        seen = set()
        unique_terms = []
        for term in expanded_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
                
        expanded = " ".join(unique_terms)
        logger.info(f"Query expanded: '{query}' -> '{expanded}'")
        return expanded
