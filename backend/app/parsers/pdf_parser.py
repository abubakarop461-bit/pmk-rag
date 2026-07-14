import fitz  # PyMuPDF
from typing import List
from langchain_core.documents import Document
from app.parsers.base_parser import BaseParser
from loguru import logger
import concurrent.futures

class PdfParser(BaseParser):
    def parse(self, file_path: str) -> List[Document]:
        """
        Loads PDF using PyMuPDF and extracts page-by-page text layers concurrently.
        """
        logger.info(f"PdfParser starting extraction on: {file_path}")
        
        try:
            # First open to check page count
            doc = fitz.open(file_path)
            num_pages = len(doc)
            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF failed to open PDF {file_path}: {e}")
            raise RuntimeError(f"PDF parsing failed: {e}")

        # Worker function to parse a single page
        def parse_single_page(page_num: int) -> Document:
            # Open a separate fitz document instance per thread for thread safety
            thread_doc = fitz.open(file_path)
            try:
                page = thread_doc.load_page(page_num)
                text = page.get_text().strip()
                return Document(
                    page_content=text,
                    metadata={
                        "source": file_path,
                        "page": page_num + 1
                    }
                )
            finally:
                thread_doc.close()

        documents = [None] * num_pages
        try:
            # Parse pages concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(max(num_pages, 1), 8)) as executor:
                future_to_page = {
                    executor.submit(parse_single_page, page_num): page_num 
                    for page_num in range(num_pages)
                }
                for future in concurrent.futures.as_completed(future_to_page):
                    page_num = future_to_page[future]
                    documents[page_num] = future.result()
                    
            logger.info(f"PdfParser completed successfully for {file_path}. Extracted {len(documents)} pages.")
        except Exception as e:
            logger.error(f"Parallel PyMuPDF failed to parse PDF {file_path}: {e}")
            raise RuntimeError(f"Parallel PDF parsing failed: {e}")
            
        return documents
