import os
from typing import List
from langchain_core.documents import Document
from loguru import logger

from app.parsers.pdf_parser import PdfParser
from app.parsers.docx_parser import DocxParser
from app.parsers.xlsx_parser import XlsxParser
from app.parsers.pptx_parser import PptxParser
from app.parsers.txt_parser import TxtParser
from app.parsers.image_parser import ImageParser
from app.parsers.ifc_parser import IfcParser

class ParserService:
    def __init__(self):
        self.parsers = {
            ".pdf": PdfParser(),
            ".docx": DocxParser(),
            ".xlsx": XlsxParser(),
            ".xls": XlsxParser(),
            ".pptx": PptxParser(),
            ".txt": TxtParser(),
            ".jpg": ImageParser(),
            ".jpeg": ImageParser(),
            ".png": ImageParser(),
            ".ifc": IfcParser()
        }
        logger.info(f"ParserService initialized with {len(self.parsers)} extensions mapped.")

    def parse_file(self, file_path: str) -> List[Document]:
        """
        Dynamically selects the correct parser based on file extension and parses.
        """
        _, ext = os.path.splitext(file_path)
        ext_lower = ext.lower()
        
        parser = self.parsers.get(ext_lower)
        if not parser:
            logger.warning(f"No matching parser for file extension '{ext}'. Defaulting to TxtParser.")
            parser = self.parsers[".txt"]
            
        logger.info(f"Selected parser: {parser.__class__.__name__} for file: {file_path}")
        return parser.parse(file_path)
