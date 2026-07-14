from typing import List
from langchain_core.documents import Document
from app.parsers.base_parser import BaseParser

class TxtParser(BaseParser):
    def parse(self, file_path: str) -> List[Document]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path, "page": 1})]
