import json
import uuid
from typing import Dict, Any

from langchain_core.documents import Document

from rag import pg_vector_db
from app.exceptions import (
    AppointmentNotFoundError,
    AppointmentAlreadyExistsError,
    AppointmentDataError
)


class AppointmentService:
    @staticmethod
    async def get_appointment_by_phone_number(phone_number: str) -> Dict[str, Any]:
        """
        Retrieve an appointment by phone number.

        Args:
            phone_number: The phone number to search for

        Returns:
            dict: The appointment data

        Raises:
            HTTPException: If appointment not found or an error occurs
        """
        try:
            filter_criteria = {
                "phone_number": phone_number,
                "type": "appointment"
            }

            results = pg_vector_db.similarity_search(
                query="",
                filter=filter_criteria,
                k=1
            )

            if not results:
                raise AppointmentNotFoundError(
                    detail=f"No appointment found for phone number: {phone_number}"
                )

            appointment_data = json.loads(results[0].page_content)
            return {
                "id": results[0].metadata.get("id"),
                "phone_number": phone_number,
                **appointment_data
            }

        except (AppointmentNotFoundError, AppointmentDataError):
            raise
        except Exception as e:
            raise AppointmentDataError(
                detail=f"Failed to retrieve appointment: {str(e)}"
            )

    @staticmethod
    async def update_appointment(customer_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Update an existing appointment.

        Args:
            update_data: The data to update

        Returns:
            dict: Success message

        Raises:
            AppointmentNotFoundError: If appointment not found
            AppointmentDataError: If there's an error updating the appointment
        """
        try:
            # Get the customer phone number
            phone_number = customer_data.get("customer_phone_number")

            # Create a filter
            filter_criteria = {
                "phone_number": phone_number,
                "type": "appointment"
            }

            # Check for existing data
            results = pg_vector_db.similarity_search(
                query="",
                filter=filter_criteria,
                k=1
            )
            if not results:
                raise AppointmentNotFoundError(
                    detail=f"No appointment found for phone number: {phone_number}"
                )

            # Create the updated customer data object
            doc_id = results[0].metadata["id"]
            customer_data = json.dumps(customer_data)
            updated_doc = Document(
                page_content=customer_data,
                metadata={
                    "id": doc_id,
                    "phone_number": phone_number,
                    "type": "appointment",
                },
            )

            pg_vector_db.add_documents([updated_doc])
            return {
                "id": doc_id,
                "data": customer_data,
                "message": "Appointment updated successfully"
            }

        except (AppointmentNotFoundError, AppointmentDataError):
            raise
        except Exception as e:
            raise AppointmentDataError(
                detail=f"Failed to update appointment: {str(e)}"
            )

    @staticmethod
    async def create_appointment(customer_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create a new appointment.

        Args:
            customer_data: The appointment data

        Returns:
            dict: The created appointment ID and success message

        Raises:
            AppointmentAlreadyExistsError: If an appointment with this phone number already exists
            AppointmentDataError: If there's an error creating the appointment
        """
        try:
            # Get the customer phone number
            phone_number = customer_data.get("customer_phone_number")

            # Create filter
            filter_criteria = {
                "phone_number": phone_number,
                "type": "appointment"
            }

            # Check for existing data
            existing_appointments = pg_vector_db.similarity_search(
                query="",
                filter=filter_criteria,
                k=1
            )
            if existing_appointments:
                raise AppointmentAlreadyExistsError(
                    detail=f"An appointment already exists for phone number: {phone_number}"
                )

            # Create the payload to save on the DB
            customer_id = str(uuid.uuid4())
            customer_data = json.dumps(customer_data)

            document = [
                Document(
                    page_content=customer_data,
                    metadata={
                        "id": customer_id,
                        "phone_number": phone_number,
                        "type": "appointment",
                    },
                )
            ]

            # Save to DB
            pg_vector_db.add_documents(document)

            return {
                "id": customer_id,
                "data": customer_data,
                "message": "Appointment created successfully"
            }

        except (AppointmentAlreadyExistsError, AppointmentDataError):
            raise
        except Exception as e:
            raise AppointmentDataError(
                detail=f"Failed to create appointment: {str(e)}"
            )
