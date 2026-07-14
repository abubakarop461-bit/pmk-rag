import os
from PIL import Image
from loguru import logger

_paddle_ocr_instance = None
_ocr_initialized = False
_ocr_cache = {}

def get_ocr_cache():
    global _ocr_cache
    return _ocr_cache


class OcrService:
    def __init__(self):
        pass

    def _init_paddle(self):
        global _paddle_ocr_instance, _ocr_initialized
        if _ocr_initialized:
            return
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing global PaddleOCR engine...")
            # Initialize with English, angle classification, and logging disabled
            _paddle_ocr_instance = PaddleOCR(lang="en", use_angle_cls=True, show_log=False)
            logger.info("[SUCCESS] PaddleOCR engine loaded.")
        except Exception as e:
            logger.warning(f"PaddleOCR failed to import (will use Tesseract fallback): {e}")
        _ocr_initialized = True

    def ocr_image(self, image_path: str) -> str:
        """
        Performs text extraction on an image file.
        Tries PaddleOCR first, falling back to pytesseract.
        """
        self._init_paddle()
        global _paddle_ocr_instance
        
        if _paddle_ocr_instance:
            try:
                logger.info(f"Running PaddleOCR on {image_path}...")
                result = _paddle_ocr_instance.ocr(image_path, cls=True)
                if result and result[0]:
                    lines = [line[1][0] for line in result[0] if line and len(line) > 1]
                    extracted_text = "\n".join(lines).strip()
                    if extracted_text:
                        logger.info("PaddleOCR completed successfully.")
                        return extracted_text
            except Exception as e:
                logger.warning(f"PaddleOCR run failed: {e}. Falling back to Tesseract...")

        # Tesseract Fallback
        try:
            logger.info(f"Running Tesseract OCR on {image_path}...")
            import pytesseract
            text = pytesseract.image_to_string(Image.open(image_path)).strip()
            logger.info("Tesseract completed successfully.")
            return text
        except Exception as e:
            logger.error(f"Tesseract OCR fallback failed: {e}")
            raise RuntimeError(f"OCR processing failed on all engines: {e}")
