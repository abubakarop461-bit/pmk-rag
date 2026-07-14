import os
from typing import List, Dict, Any, Tuple
from loguru import logger

class PromptBuilderService:
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            # Resolve to backend/app/prompts/ folder
            current_dir = os.path.dirname(os.path.dirname(__file__))
            prompts_dir = os.path.join(current_dir, "prompts")
        self.prompts_dir = prompts_dir

    def _load_template(self, filename: str) -> str:
        filepath = os.path.join(self.prompts_dir, filename)
        if not os.path.exists(filepath):
            logger.error(f"Prompt template file not found: {filepath}")
            raise FileNotFoundError(f"Template file '{filename}' is missing in {self.prompts_dir}")
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def build_prompt(
        self, 
        context_package: Dict[str, Any], 
        question: str, 
        history: List[Dict[str, str]]
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Dynamically loads templates from file system and formats system rules, context, and user questions.
        """
        logger.info("PromptBuilderService constructing RAG payload from template files...")
        
        # Load files dynamically
        system_template = self._load_template("system_prompt.txt")
        citation_template = self._load_template("citation_prompt.txt")
        construction_template = self._load_template("construction_prompt.txt")
        no_context_template = self._load_template("no_context_prompt.txt")
        
        # Combine system behavior directives
        system_prompt = f"{system_template}\n\n{citation_template}"
        
        blocks = context_package.get("context_blocks", [])
        if not blocks:
            # Build refusal prompt if context is empty
            user_prompt = no_context_template.format(question=question)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            return system_prompt, messages
            
        # Format Context Blocks
        context_str = ""
        for idx, block in enumerate(blocks):
            pages_list = ", ".join(map(str, block["pages"]))
            context_str += (
                f"--- Source Block #{idx+1} ---\n"
                f"Document: {block['filename']} (Type: {block['document_type']}, Revision: {block['revision_id']})\n"
                f"Pages: {pages_list}\n"
                f"Content:\n{block['text']}\n"
                f"-----------------------------\n\n"
            )
            
        # Format Chat History
        history_str = ""
        if history:
            for turn in history:
                role_label = turn["role"].capitalize()
                history_str += f"{role_label}: {turn['content']}\n"
        else:
            history_str = "None (New session)\n"
            
        # Apply construction scaffolding template
        user_prompt = construction_template.format(
            context=context_str,
            history=history_str,
            question=question
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return system_prompt, messages
