import re
from loguru import logger

class ConversationTitleGenerator:
    def generate_title(self, first_message: str) -> str:
        """
        Generates a concise conversation title (5-7 words) from the first message
        using lightweight heuristics (no LLM required).
        """
        if not first_message:
            return "New Chat Thread"
            
        # 1. Strip common leading query prefixes, filler words, and directions
        # This regex matches any repetitions/combinations of start words at the beginning
        prefix_regex = r"^(please|show|tell|explain|find|search|give|list|can|you|we|me|us|what|is|are|was|were|about|the|a|an|how|do|does|to|any|all)\s+"
        
        # Lowercase for uniform processing
        cleaned = first_message.lower().strip()
        
        # Repeatedly strip matching prefixes
        while True:
            new_cleaned = re.sub(prefix_regex, "", cleaned)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned
            
        # Strip final trailing punctuation
        cleaned = re.sub(r"[^\w\s\-\/]", "", cleaned).strip()
        
        # 2. Extract first 5-6 words
        tokens = cleaned.split()
        if not tokens:
            # Fall back to original cleaned tokens if everything got stripped
            fallback_cleaned = re.sub(r"[^\w\s\-\/]", "", first_message).strip()
            tokens = fallback_cleaned.split()
            if not tokens:
                return "New Chat Thread"
                
        selected_tokens = tokens[:6]
        
        # 3. Capitalize and format acronyms
        formatted_tokens = []
        for token in selected_tokens:
            # Keep common abbreviations capitalized
            if token.lower() in ["boq", "rfi", "ncr", "bim"]:
                formatted_tokens.append(token.upper())
            else:
                formatted_tokens.append(token.capitalize())
                
        title = " ".join(formatted_tokens)
        logger.info(f"ConversationTitleGenerator title result: '{title}' (original: '{first_message}')")
        return title
