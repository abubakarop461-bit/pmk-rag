class LlmService:
    def __init__(self, llm_provider):
        self.llm = llm_provider

    def query(self, prompt: str, system_prompt: str = None) -> str:
        return self.llm.generate(prompt, system_prompt)
