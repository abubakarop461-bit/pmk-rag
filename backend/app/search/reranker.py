class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name

    def rerank(self, query: str, documents: list) -> list:
        # TODO: Implement cross-encoder query-document score reranking logic
        return documents
