from typing import List
from uuid import uuid4

from langchain_core.documents import Document

import faiss
from langchain_community.docstore import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from config import EMBEDDING_MODEL


class Faiss:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.index = faiss.IndexFlatL2(len(self.embeddings.embed_query("faiss store")))
        self.vector_store = FAISS(
            embedding_function=self.embeddings,
            index=self.index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
        )

    def add(self, documents: List[Document]):
        uuids = [str(uuid4()) for _ in range(len(documents))]
        self.vector_store.add_documents(documents=documents, ids=uuids)

    def search(self, query: str, k: int):
        return self.vector_store.similarity_search(query, k=k)


# faiss_db = Faiss()

