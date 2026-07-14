import os
import re
import fitz  # PyMuPDF
from PIL import Image as PILImage
from typing import Dict, Any, Optional
from loguru import logger
from app.services.ocr_service import OcrService

class DrawingExtractorService:
    def __init__(self):
        self.ocr_svc = OcrService()

    def extract_title_block_metadata(self, file_path: str, document_type: str) -> Dict[str, Any]:
        """
        Main entrypoint. Extracts construction-specific metadata from drawing sheets.
        Crops the title block area (bottom-right 35% of the first page) and runs OCR.
        """
        meta = {
            "drawing_number": None,
            "revision": None,
            "discipline": None,
            "sheet": None,
            "level": None
        }
        
        if document_type.lower() != "drawing":
            return meta
            
        ext = os.path.splitext(file_path)[1].lower()
        temp_img_path = f"temp_title_block_{os.path.basename(file_path)}.png"
        
        # 1. Crop bottom-right corner based on file extension
        cropped_successfully = False
        try:
            if ext == ".pdf":
                doc = fitz.open(file_path)
                if len(doc) > 0:
                    page = doc.load_page(0)
                    w, h = page.rect.width, page.rect.height
                    
                    # Crop bottom-right 35% width and 35% height (GOST title block standard placement)
                    rect = fitz.Rect(w * 0.65, h * 0.65, w, h)
                    pix = page.get_pixmap(clip=rect, dpi=150)
                    pix.save(temp_img_path)
                    cropped_successfully = True
                doc.close()
                
            elif ext in [".jpg", ".jpeg", ".png"]:
                img = PILImage.open(file_path)
                w, h = img.size
                
                # Crop bottom-right 35%
                cropped = img.crop((int(w * 0.65), int(h * 0.65), w, h))
                cropped.save(temp_img_path)
                cropped_successfully = True
        except Exception as e:
            logger.warning(f"Title block cropping failed for {file_path}: {e}")
            
        # 2. Execute OCR on the cropped title block image
        ocr_text = ""
        if cropped_successfully and os.path.exists(temp_img_path):
            try:
                ocr_text = self.ocr_svc.ocr_image(temp_img_path)
                logger.debug(f"Title block OCR text:\n{ocr_text}")
            except Exception as ocr_err:
                logger.error(f"OCR execution on cropped drawing block failed: {ocr_err}")
            finally:
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
                    
        # 3. Parse heuristics from title block text (supporting GOST and standard conventions)
        if ocr_text:
            meta = self.parse_text_heuristics(ocr_text)
            
        return meta

    def parse_text_heuristics(self, text: str) -> Dict[str, Any]:
        """
        Parses drawing numbers, revisions, disciplines, storeys, and sheets from OCR text.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        drawing_number = None
        revision = None
        discipline = None
        sheet = None
        level = None
        
        # 1. Heuristic regex for Drawing Numbers (GOST standard like XX-XX-XX-AR or numbers with dash segments)
        draw_patterns = [
            r"\b[A-Z0-9]{3,}\-[A-Z0-9\-]{3,}\-[A-Z0-9\-]+\b",
            r"\b\d{4,}\-[A-Z0-9\-]+\b",
            r"\b[A-Z0-9]+[-/][A-Z0-9]+[-/][A-Z0-9]+\b"
        ]
        
        for pat in draw_patterns:
            matches = re.findall(pat, text)
            if matches:
                # Pick the longest match as it is likely the main identifier
                drawing_number = max(matches, key=len)
                break
                
        # 2. Revision detection (Rev. A, Rev 02, Изм. 1, Revision: B)
        rev_match = re.search(r"\b(?:rev|revision|изм)\.?\s*[:\-]?\s*([a-zA-Z0-9]+)\b", text, re.IGNORECASE)
        if rev_match:
            revision = rev_match.group(1).upper()
            
        # 3. Sheet Number (Sheet 2, Лист 5)
        sheet_match = re.search(r"\b(?:sheet|лист)\.?\s*[:\-]?\s*([0-9]+)\b", text, re.IGNORECASE)
        if sheet_match:
            sheet = sheet_match.group(1)
            
        # 4. Level / Storey (e.g. Level 02, Floor 3, etc.) - line-by-line matching
        for line in lines:
            if any(k in line.lower() for k in ["level", "floor", "storey", "этаж", "отметка"]):
                match = re.search(r"\b(?:level|floor|storey|этаж|отметка)\.?\s*[:\-]?\s*([^\n]+)", line, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    # Prioritize values that contain digits or are explicitly LEVEL XX
                    if any(c.isdigit() for c in val) or not level:
                        level = val
                        
        # 5. Discipline Heuristic
        # Check suffixes and content keywords
        full_text_lower = text.lower()
        if drawing_number:
            num_lower = drawing_number.lower()
            if any(suff in num_lower for suff in ["-ar", "-ap", "arch"]):
                discipline = "Architectural"
            elif any(suff in num_lower for suff in ["-kr", "-km", "-kzh", "struc", "-s-"]):
                discipline = "Structural"
            elif any(suff in num_lower for suff in ["-ob", "-hvac", "mech"]):
                discipline = "HVAC"
            elif any(suff in num_lower for suff in ["-eo", "elec"]):
                discipline = "Electrical"
            elif any(suff in num_lower for suff in ["-vk", "plumb"]):
                discipline = "Plumbing"
                
        if not discipline:
            if any(term in full_text_lower for term in ["architect", "архитектур", "ар"]):
                discipline = "Architectural"
            elif any(term in full_text_lower for term in ["structural", "конструк", "кр", "кж", "км"]):
                discipline = "Structural"
            elif any(term in full_text_lower for term in ["hvac", "отоплен", "вентиляц"]):
                discipline = "HVAC"
            elif any(term in full_text_lower for term in ["electric", "электр"]):
                discipline = "Electrical"
            elif any(term in full_text_lower for term in ["plumb", "водопровод", "канализац"]):
                discipline = "Plumbing"
                
        return {
            "drawing_number": drawing_number,
            "revision": revision,
            "discipline": discipline,
            "sheet": sheet,
            "level": level
        }
