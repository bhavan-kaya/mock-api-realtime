from typing import List, Optional

from fastapi import FastAPI
from langchain_core.documents import Document
from pydantic import BaseModel

from mock_data import docs, vehicles
from rag import PGVectorStore

app = FastAPI()
appointments = []


# Models for request and response payloads
class AppointmentRequest(BaseModel):
    customer_id: str
    vehicle_id: str
    date: str
    time: str
    service: str


class AppointmentResponse(BaseModel):
    appointment_id: int
    customer_id: str
    vehicle_id: str
    date: str
    time: str
    service: str


class VectorSearch(BaseModel):
    query: str
    filter: dict
    native: Optional[bool] = False


class VectorLoad(BaseModel):
    docs: List[str]


pg_vector = PGVectorStore()


@app.post("/book-appointment", response_model=AppointmentResponse)
def book_appointment(request: AppointmentRequest):
    # Generate a new appointment ID
    appointment_id = len(appointments) + 1
    appointment = {
        "appointment_id": appointment_id,
        "customer_id": request.customer_id,
        "vehicle_id": request.vehicle_id,
        "date": request.date,
        "time": request.time,
        "service": request.service,
    }
    appointments.append(appointment)

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


@app.get("/vehicle/{vehicle_id}")
def get_vehicle_details(vehicle_id: str):
    vehicle = vehicles.get(vehicle_id)
    if not vehicle:
        return {"make": "Ferrari", "model": "Model X", "year": 2024}
    return vehicle


@app.post("/vector-info")
def get_vector_info(data: VectorSearch):
    retrieved_docs = pg_vector.similarity_search(
        query=data.query, filter=data.filter, k=10, native=data.native
    )
    retrieved_texts = [doc.page_content for doc in retrieved_docs]

    if not retrieved_texts:
        return f"No relevant information found in the knowledge base."

    return f"Information from knowledge base:\n" + "\n".join(retrieved_texts)


@app.get("/vector-store/load")
def load_vector_info():
    pg_vector.add_documents(docs)
    return f"Loaded {len(docs)} documents into the vector store."


@app.get("/vector-store/load-docs")
def load_vector_info(load: VectorLoad):
    docs = [
        Document(
            page_content=str(doc),
            metadata={
                "id": index,
                "topic": "maintenance",
            },
        )
        for index, doc in enumerate(load.docs)
    ]
    pg_vector.add_documents(docs)
    return f"Loaded {len(docs)} documents into the vector store."


# Run the application (if needed for local testing)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
