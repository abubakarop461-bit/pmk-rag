from app.agents.base_agent import BaseAgent

class BimAgent(BaseAgent):
    def run(self, query: str, context: str = None) -> str:
        # TODO: Implement BIM/IFC geometric and semantic metadata query logic
        return f"[BIM Agent reasoning answer for: {query}]"
