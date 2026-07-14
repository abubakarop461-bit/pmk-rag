from app.agents.base_agent import BaseAgent

class BoqAgent(BaseAgent):
    def run(self, query: str, context: str = None) -> str:
        # TODO: Implement Bill of Quantities spreadsheet tabular extraction logic
        return f"[BOQ Agent reasoning answer for: {query}]"
