import os
import random
from datetime import datetime
from itertools import islice
from typing import List, Optional

from fastapi import FastAPI, Query
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import INGESTION_TEMPLATE, RAG_TEMPLATE_THREE, REALTIME_MAX_TOKENS
from faiss_data import FAISS_DOCUMENTS
from faiss_store import Faiss
from mock_data import docs, vehicles
from rag import PGVectorStore
from util import Utils

app = FastAPI()


# Models for request and response payloads
class AppointmentRequest(BaseModel):
    customer_name: str
    vehicle_details: str
    date: str
    time: str
    service: str

class ContactPersistenceRequest(BaseModel):
    customer_name: str
    phone_number: str
    service_supplier: str


class HybridSearchOptions(BaseModel):
    searchWeight: Optional[float] = 0.5
    useEntities: Optional[bool] = False


class VectorSearch(BaseModel):
    query: str
    filter: dict = {}
    doRerank: Optional[bool] = False
    doHybridSearch: Optional[bool] = False
    hybridSearchOptions: Optional[HybridSearchOptions] = None
    native: Optional[bool] = False
    contentOnly: Optional[bool] = False
    k: Optional[int] = 10
    db: Optional[str] = "pg"


class VectorLoad(BaseModel):
    docs: List[str]
    topic: str


pg_vector = PGVectorStore()
faiss = Faiss()
# faiss.add(documents=FAISS_DOCUMENTS)


@app.post("/book-appointment")
def book_appointment(request: AppointmentRequest):
    appointment = {
        "appointment_id": random.randint(1000, 9999),
        "customer_name": request.customer_name,
        "vehicle_details": request.vehicle_details,
        "date": request.date,
        "time": request.time,
        "service": request.service,
    }

    try:

        docs = [
            Document(
                page_content=str(appointment),
                metadata={
                    "id": 1,
                    "topic": "maintenance",
                },
            )
        ]
        pg_vector.add_documents(docs)
    except Exception as e:
        print(e)

    return appointment


@app.post("/save-contact")
def book_appointment(request: ContactPersistenceRequest):
    appointment = {
        "customer_name": request.customer_name,
        "contact_number": request.phone_number,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
    }

    try:
        docs = [
            Document(
                page_content=str(appointment),
                metadata={
                    "service_provider": request.service_supplier,
                    "topic": "customer_identification",
                },
            )
        ]
        pg_vector.add_documents(docs)
    except Exception as e:
        print(e)

    return appointment


@app.get("/vehicle/{vehicle_id}")
def get_vehicle_details(vehicle_id: str):
    vehicle = vehicles.get(vehicle_id)
    if not vehicle:
        return {"make": "Ferrari", "model": "Model X", "year": 2024}
    return vehicle


@app.post("/vector-info")
def get_vector_info(data: VectorSearch):
    llm = ChatOpenAI(model_name="gpt-4o")
    prompt = PromptTemplate(
        template=RAG_TEMPLATE_THREE, input_variables=["query", "information"]
    )
    chain = prompt | llm

    if data.db == "faiss":
        retrieved_docs = faiss.search(query=data.query, k=data.k)
    else:
        if data.doHybridSearch:
            retrieved_docs = pg_vector.hybrid_search(
                data.query,
                data.filter,
                data.k,
                data.hybridSearchOptions.searchWeight,
                data.hybridSearchOptions.useEntities,
            )
        else:
            retrieved_docs = pg_vector.similarity_search(
                query=data.query, filter=data.filter, k=data.k, native=data.native
            )

    retrieved_texts = [doc.page_content for doc in retrieved_docs]

    if data.doRerank:
        ranked_docs = Utils.get_ranked_documents(data.query, retrieved_texts)
        retrieved_texts = [rank_doc.text for rank_doc in ranked_docs]

    information = "\n\n Car Profile:".join(
        [f"{idx} {text}" for idx, text in enumerate(retrieved_texts)]
    )

    if data.contentOnly:
        return information

    print("Query: ", data.query)
    print(
        "\n\nRetrieved indices: ",
        ", ".join([str(idx) for idx, _ in enumerate(retrieved_texts)]),
    )

    response = chain.invoke({"query": data.query, "information": information})

    return response.content


@app.get("/vector-store/load")
def load_vector_info():
    pg_vector.add_documents(docs)
    return f"Loaded {len(docs)} documents into the vector store."


@app.post("/vector-store/load-docs")
def load_vector_info(
    start: Optional[int] = Query(
        0, description="Start index for slicing the documents"
    ),
    end: Optional[int] = Query(None, description="End index for slicing the documents"),
):
    loader = CSVLoader(file_path="data/vehicle_inventory_data.csv")
    docs = loader.load()

    docs = docs[start:end] if end is not None else docs[start:]

    llm = ChatOpenAI(model_name="gpt-4o")
    prompt = PromptTemplate.from_template(template=INGESTION_TEMPLATE)
    chain = prompt | llm
    documents = []

    def batch(iterable, n=1):
        iterable = iter(iterable)
        while True:
            batch_items = list(islice(iterable, n))
            if not batch_items:
                break
            yield batch_items

    for idx, doc in enumerate(docs):
        response = chain.invoke({"information": doc.page_content})
        processed_doc = Document(
            page_content=str(response.content),
            metadata={"id": start + idx},
        )
        documents.append(processed_doc)
        print("Document loaded: ", start + idx)

        if len(documents) % 10 == 0 or idx == len(docs) - 1:
            pg_vector.add_documents(documents)
            print(f"Added {len(documents)} documents to vector store.")
            documents.clear()

    return f"Loaded {len(docs)} documents into the vector store, from index {start} to {end or 'end'}."


@app.get("/search")
def search(
    vin: Optional[str] = Query(None),
    stock_number: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    trim: Optional[str] = Query(None),
    style: Optional[str] = Query(None),
    exterior_color: Optional[str] = Query(None),
    interior_color: Optional[str] = Query(None),
    certified: Optional[bool] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    fuel_type: Optional[str] = Query(None),
    transmission: Optional[str] = Query(None),
    drive_type: Optional[str] = Query(None),
    doors: Optional[int] = Query(None),
    engine_type: Optional[str] = Query(None),
    features: Optional[str] = Query(None),
    packages: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    fields: Optional[str] = Query(None),
    options: Optional[str] = Query(None),
    context_limit: Optional[int] = Query(REALTIME_MAX_TOKENS),
):
    return pg_vector.search_vehicle_inventory(
        vin=vin,
        stock_number=stock_number,
        vehicle_type=vehicle_type,
        year=year,
        make=make,
        model=model,
        trim=trim,
        style=style,
        exterior_color=exterior_color,
        interior_color=interior_color,
        certified=certified,
        min_price=min_price,
        max_price=max_price,
        fuel_type=fuel_type,
        transmission=transmission,
        drive_type=drive_type,
        doors=doors,
        engine_type=engine_type,
        features=features,
        packages=packages,
        description=description,
        fields=fields,
        options=options,
        context_limit=context_limit,
    )


# Run the application (if needed for local testing)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
