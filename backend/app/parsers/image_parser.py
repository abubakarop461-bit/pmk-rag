from typing import List
from langchain_core.documents import Document
from app.parsers.base_parser import BaseParser
from loguru import logger

class ImageParser(BaseParser):
    def parse(self, file_path: str) -> List[Document]:
        """
        Placeholder parser for image-only files. Decoupled and deferred to OCR Phase 3B.
        """
        logger.info(f"ImageParser triggered for: {file_path}. Text layer extraction deferred to Phase 3B.")
        return [
            Document(
                page_content="[Visual image file content. Text extraction requires OCR indexing (Phase 3B).]",
                metadata={
                    "source": file_path,
                    "page": 1,
                    "ocr_required": True
                }
            )
        ]
