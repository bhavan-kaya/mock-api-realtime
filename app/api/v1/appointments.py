import logging
import json
import uuid

from langchain_core.documents import Document

from fastapi import APIRouter, status, HTTPException
from app.models.appointment_request_model import AppointmentRequestModel
from app.models.appointment_update_model import AppointmentUpdateModel
from rag import pg_vector_db


# Get logger
logger = logging.getLogger(__name__)

# Initialize the router
router = APIRouter(prefix="/appointments")


@router.get("/{phone_number}")
def get_appointment_by_phone_number(phone_number: str):
    try:
        # Search for appointments with the given phone number
        filter_criteria = {
            "phone_number": phone_number,
            "type": "appointment"
        }

        # Using similarity search with a dummy query since we're filtering by metadata
        results = pg_vector_db.similarity_search(
            query="",  # Empty query since we're filtering by metadata
            filter=filter_criteria,
            k=1  # We only need one result to check existence
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No appointment found for phone number: {phone_number}"
            )

        # Return the first matching appointment
        appointment_data = json.loads(results[0].page_content)
        return {
            "id": results[0].metadata.get("id"),
            "phone_number": phone_number,
            **appointment_data
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f'An error occurred while fetching appointment: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{phone_number}")
def update_appointment(phone_number: str, appointment: AppointmentUpdateModel):
    try:
        # First check if an appointment exists for this phone number
        filter_criteria = {
            "phone_number": phone_number,
            "type": "appointment"
        }

        # Find the existing appointment
        results = pg_vector_db.similarity_search(
            query="",
            filter=filter_criteria,
            k=1
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No appointment found for phone number: {phone_number}"
            )

        # Get the document ID of the existing appointment
        doc_id = results[0].metadata["id"]

        # Create the updated document
        updated_data = json.dumps({
            "phone_number": phone_number,
            **appointment.customer_data
        })

        # Create the updated document with the same ID to perform an update
        updated_doc = Document(
            page_content=updated_data,
            metadata={
                "id": doc_id,
                "phone_number": phone_number,
                "type": "appointment",
            },
        )

        # In PGVector with langchain, we can add a document with the same ID to update it
        pg_vector_db.add_documents([updated_doc])

        return {"message": "Appointment updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(f'An error occurred while updating appointment: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/appointments")
def save_appointment(appointment: AppointmentRequestModel):
    try:
        # First check if an appointment already exists for this phone number
        filter_criteria = {
            "phone_number": appointment.customer_phone_number,
            "type": "appointment"
        }

        existing_appointments = pg_vector_db.similarity_search(
            query="",
            filter=filter_criteria,
            k=1
        )

        if existing_appointments:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An appointment already exists for phone number: {appointment.customer_phone_number}"
            )

        # Create a unique customer ID
        customer_id = str(uuid.uuid4())

        # Extract the payload
        phone_number = appointment.customer_phone_number
        customer_data = appointment.customer_data

        # Create the payload
        data = json.dumps({
            "phone_number": phone_number,
            **customer_data
        })

        # Create the document object
        document = [
            Document(
                page_content=data,
                metadata={
                    "id": customer_id,
                    "phone_number": phone_number,
                    "type": "appointment",
                },
            )
        ]

        # Save to the vector store (PGVect)
        pg_vector_db.add_documents(document)

        return {"id": customer_id, "message": "Appointment created successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(f'An internal error occurred: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
