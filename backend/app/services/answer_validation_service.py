from typing import List, Dict, Any
from loguru import logger

class AnswerValidationService:
    def validate_answer(self, answer: str, context_package: Dict[str, Any], confidence_summary: str) -> str:
        """
        Validates the generated response text against the retrieved context package.
        Returns the original answer on success, or a safe fallback failure string on validation errors.
        """
        logger.info("AnswerValidationService running checks on generated response...")
        
        # 1. Empty answer check
        if not answer or not answer.strip():
            logger.warning("Validation failed: Answer is empty or whitespace-only.")
            return self.get_fallback_message()
            
        blocks = context_package.get("context_blocks", [])
        
        # If no context blocks were retrieved (refusal case), skip citation checking
        if not blocks or confidence_summary == "Low":
            # Just ensure it doesn't state it answered confidently
            logger.info("Skipped full validation checks for low-confidence/empty-context refusal.")
            return answer
            
        # 2. Citations Exist check
        # Check for presence of citation format square brackets "[Doc: " or generic "["
        if "[" not in answer or "]" not in answer:
            logger.warning("Validation failed: Answer does not contain any citation brackets.")
            return self.get_fallback_message()
            
        # 3. Context References check
        # Ensure at least one filename from the context package is mentioned in the answer
        filenames = {b["filename"].lower() for b in blocks}
        answer_lower = answer.lower()
        
        has_file_reference = False
        for fname in filenames:
            if fname in answer_lower:
                has_file_reference = True
                break
                
        if not has_file_reference:
            logger.warning("Validation failed: Answer does not reference any retrieved context filenames.")
            return self.get_fallback_message()
            
        logger.info("[SUCCESS] Answer validation passed successfully.")
        return answer

    def get_fallback_message(self) -> str:
        """
        Standard fallback refusal string.
        """
        return (
            "I apologize, but I could not validate the generated response against the provided source documents. "
            "Please verify your query or consult the source files directly."
        )
