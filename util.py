from typing import List

from rerankers import Reranker

from config import COHERE_API_KEY


class Utils:
    @staticmethod
    def get_ranked_documents(query, retrieved_texts) -> List[str]:
        if not retrieved_texts:
            print("No documents found for the query.")
            return []
        ranker = Reranker(
            "cohere",
            lang="en",
            model_type="rerank-english-v3.0",
            api_key=COHERE_API_KEY,
        )
        ranked_docs = ranker.rank(query=query, docs=retrieved_texts)
        return ranked_docs.results