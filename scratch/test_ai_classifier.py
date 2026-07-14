import os
import sys
from loguru import logger

# Add backend folder path to sys.path
backend_path = r"c:\Users\HP\OneDrive\Desktop\pmk-RAG\backend"
sys.path.append(backend_path)

from app.services.document_classification_service import DocumentClassificationService

def run_classifier_tests():
    logger.info("Initializing Document Classification Service tests...")
    
    classifier = DocumentClassificationService()
    
    test_cases = [
        # 1. BOQ match
        {
            "filename": "site_quantities_takeoff.xlsx",
            "text": "Item Description | Unit Rate | Total Qty | BOQ",
            "expected_type": "BOQ",
            "expected_min_confidence": 80
        },
        # 2. Contract match
        {
            "filename": "lease_agreement_draft.pdf",
            "text": "This agreement is made between terms and conditions liability",
            "expected_type": "contract",
            "expected_min_confidence": 80
        },
        # 3. Drawing match
        {
            "filename": "5042-DRW-02-ARCH.pdf",
            "text": "drawing number: 5042 scale: 1:100",
            "expected_type": "drawing",
            "expected_min_confidence": 80
        },
        # 4. RFI match
        {
            "filename": "rfi_clarification_concrete_strength.pdf",
            "text": "Request for information query description response",
            "expected_type": "RFI",
            "expected_min_confidence": 80
        },
        # 5. Low confidence fallback
        {
            "filename": "random_file_name_123.pdf",
            "text": "some general unstructured text document details",
            "expected_type": "other",
            "expected_min_confidence": 40
        }
    ]
    
    for tc in test_cases:
        dtype, conf = classifier.classify_document(tc["filename"], tc["text"])
        logger.info(f"File: '{tc['filename']}' -> AI Detected: {dtype} (Confidence: {conf}%)")
        assert dtype == tc["expected_type"]
        assert conf >= tc["expected_min_confidence"]
        
    logger.info("[SUCCESS] Document Classification Service tests passed successfully!")

if __name__ == "__main__":
    run_classifier_tests()
