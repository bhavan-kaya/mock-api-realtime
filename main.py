from typing import List, Optional

from fastapi import FastAPI, Query
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
    topic: str


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


@app.post("/vector-store/load-docs")
def load_vector_info(load: VectorLoad):
    docs = [
        Document(
            page_content=str(doc),
            metadata={
                "id": index,
                "topic": load.topic,
            },
        )
        for index, doc in enumerate(load.docs)
    ]
    pg_vector.add_documents(docs)
    return f"Loaded {len(docs)} documents into the vector store."


@app.get("/search")
def search(
    vin: Optional[str] = Query(None),
    stock_number: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
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
    description: Optional[str] = Query(None),
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
        description=description,
    )


# Run the application (if needed for local testing)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
