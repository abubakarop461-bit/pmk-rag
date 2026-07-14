from loguru import logger

class QueryPreprocessingService:
    def preprocess(self, query: str) -> str:
        """
        Cleans and normalizes query text whitespace.
        """
        if not query:
            return ""
        # Strip and normalize spaces
        cleaned = " ".join(query.strip().split())
        logger.debug(f"Preprocessing clean query: '{cleaned}'")
        return cleaned
