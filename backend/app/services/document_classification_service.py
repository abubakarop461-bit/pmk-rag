import os
import re
from typing import Dict, Any, Tuple, Optional
from loguru import logger

class DocumentClassificationService:
    def classify_document(self, filename: str, text_content: Optional[str] = None) -> Tuple[str, int]:
        """
        Classifies a document into one of the supported types based on multiple signals:
        - Filename
        - File extension
        - Extracted text snippets (if provided)
        
        Returns:
            Tuple[detected_document_type, confidence_score] (where confidence is 0-100)
        """
        logger.info(f"Classifying document: {filename}...")
        
        filename_lower = filename.lower()
        ext = os.path.splitext(filename_lower)[1]
        
        # Normalize text content if provided
        text_lower = text_content.lower() if text_content else ""
        
        # Supported types: Contract, Specification, BOQ, RFI, Drawing, Technical Submittal, Method Statement, NCR, Other
        signals: Dict[str, float] = {
            "contract": 0.0,
            "specification": 0.0,
            "BOQ": 0.0,
            "RFI": 0.0,
            "drawing": 0.0,
            "technical_submittal": 0.0,
            "method_statement": 0.0,
            "NCR": 0.0,
            "other": 1.0  # Base level fallback
        }
        
        # 1. SIGNAL GROUP A: File Extension
        if ext == ".ifc":
            signals["drawing"] += 0.8
        elif ext in [".dwg", ".dxf", ".rvt"]:
            signals["drawing"] += 0.9
        elif ext in [".xls", ".xlsx", ".csv"]:
            signals["BOQ"] += 0.4  # spreadsheets are often BOQ
            
        # 2. SIGNAL GROUP B: Filename Heuristics (High confidence triggers)
        # Contract keywords
        if any(w in filename_lower for w in ["contract", "agreement", "nda", "lease", "covenant", "mou"]):
            signals["contract"] += 1.2
        # Specification keywords
        if any(w in filename_lower for w in ["spec", "specs", "specification", "code", "standard", "guideline"]):
            signals["specification"] += 1.2
        # BOQ keywords
        if any(w in filename_lower for w in ["boq", "bill of quantities", "quantities", "takeoff", "estimation"]):
            signals["BOQ"] += 1.2
        # RFI keywords
        if any(w in filename_lower for w in ["rfi", "request for information", "query"]):
            signals["RFI"] += 1.2
        # Drawing keywords / patterns
        if any(w in filename_lower for w in ["drawing", "drawings", "layout", "plan", "elevation", "section", "detail", "drw", "dwg"]):
            signals["drawing"] += 1.2
        # Drawing number format check (e.g. 5042-DRW-02-ARCH or XX-XX-AR)
        if re.search(r"\b[A-Z0-9]{3,}\-[A-Z0-9\-]{3,}\-[A-Z0-9\-]+\b", filename.upper()):
            signals["drawing"] += 1.0
            
        # Technical Submittal keywords
        if any(w in filename_lower for w in ["submittal", "tech submittal", "material submittal", "datasheet", "data sheet"]):
            signals["technical_submittal"] += 1.2
        # Method Statement keywords
        if any(w in filename_lower for w in ["method statement", "wms", "work method", "construction method"]):
            signals["method_statement"] += 1.2
        # NCR keywords
        if any(w in filename_lower for w in ["ncr", "non-conformance", "non conformance", "defect report"]):
            signals["NCR"] += 1.2

        # 3. SIGNAL GROUP C: Extracted Text Heuristics (if text is supplied)
        if text_lower:
            # Contract text signals
            if any(p in text_lower for p in ["agreement made this", "hereby agree", "terms and conditions", "liability limit", "indemnify"]):
                signals["contract"] += 1.0
            # Spec text signals
            if any(p in text_lower for p in ["specifications", "technical specs", "standards of work", "compliance with code"]):
                signals["specification"] += 1.0
            # BOQ text signals
            if any(p in text_lower for p in ["bill of quantities", "unit rate", "item description", "quantity and rate"]):
                signals["BOQ"] += 1.0
            # RFI text signals
            if any(p in text_lower for p in ["request for information", "rfi query", "clarification requested"]):
                signals["RFI"] += 1.0
            # Drawing title block text signals
            if any(p in text_lower for p in ["drawing number", "sheet number", "drawn by", "checked by", "scale:"]):
                signals["drawing"] += 1.0
            # Technical submittal text signals
            if any(p in text_lower for p in ["technical submittal", "material submittal", "manufacturer details", "testing report"]):
                signals["technical_submittal"] += 1.0
            # Method statement text signals
            if any(p in text_lower for p in ["method statement", "sequence of work", "safety measures", "risk assessment"]):
                signals["method_statement"] += 1.0
            # NCR text signals
            if any(p in text_lower for p in ["non-conformance report", "ncr number", "disposition status", "corrective action"]):
                signals["NCR"] += 1.0

        # Sort signals to find the top classified type
        sorted_signals = sorted(signals.items(), key=lambda item: item[1], reverse=True)
        top_type, score = sorted_signals[0]
        
        # Calculate confidence score percentage
        # 1.0 score or above represents high confidence (>=90%)
        # Lower scores scale down proportionally
        if top_type == "other":
            confidence = 50
        else:
            if score >= 1.2:
                confidence = min(95 + int(score * 2), 100)
            elif score >= 0.8:
                confidence = int(80 + (score - 0.8) * 25)
            elif score >= 0.4:
                confidence = int(60 + (score - 0.4) * 50)
            else:
                confidence = int(score * 150)
                
            confidence = max(min(confidence, 100), 10)
            
        logger.info(f"Classified: '{filename}' -> Detected Type: {top_type} (Score: {score:.2f}, Confidence: {confidence}%)")
        return top_type, confidence
