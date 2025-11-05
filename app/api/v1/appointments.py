from urllib.parse import unquote

from fastapi import APIRouter, status, HTTPException, Query

from app.models.enum.response_status import ResponseStatus
from app.exceptions import AppointmentException
from app.exceptions.database.database_connection_exception import DatabaseConnectionException
from app.models.appointment.appointment_request_model import AppointmentRequestModel
from app.models.appointment.appointment_update_model import AppointmentUpdateModel
from app.models.appointment.appointment_response_model import (
    CreateAppointmentResponse,
    GetAppointmentByPhoneNumberResponse,
    UpdateAppointmentResponse,
    DeleteAppointmentResponse
)
from app.services.appointments_service import appointment_service


# Initialize the router
router = APIRouter(prefix="/appointments")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Appointment already exists"},
        422: {"description": "Invalid appointment data"},
        500: {"description": "Internal server error"}
    },
    response_model=CreateAppointmentResponse
)
async def create_appointment(appointment: AppointmentRequestModel):
    """
    Create a new appointment.

    Args:
        appointment: The appointment data including customer phone number

    Returns:
        dict: The created appointment ID and success message

    Raises:
        HTTPException: If appointment already exists, data is invalid, or an error occurs
    """
    try:
        # Parse the payload
        customer_data = appointment.model_dump(exclude_none=True)

        # Create the appointment
        appointment_id = appointment_service.create_appointment(customer_data)
        return CreateAppointmentResponse(
            appointment_id=appointment_id,
            data=data,
            status=ResponseStatus.SUCCESS
        )

    except (AppointmentException, DatabaseConnectionException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to create appointment: {str(e)}"}
        )

@router.get(
    "",
    responses={
        400: {"description": "Invalid phone number format"},
        404: {"description": "Appointment not found"},
        500: {"description": "Internal server error"}
    },
    response_model=GetAppointmentByPhoneNumberResponse
)
async def get_appointment_by_phone_number(
    phone_number: str = Query(..., description="Customer phone number")
):
    """
    Get an appointment by phone number.
    
    Args:
        phone_number: The phone number to search
        
    Returns:
        dict: The appointment data
        
    Raises:
        HTTPException: If appointment is not found, phone number is invalid, or an error occurs
    """
    try:
        # Decode URL-encoded phone number
        decoded_phone = unquote(phone_number)

        # Get contact info from vector store
        appointment_data = appointment_service.get_appointment_by_phone_number(decoded_phone)

        # Prepare the payload
        appointment_id = appointment_data['id']
        del appointment_data['id']

        return GetAppointmentByPhoneNumberResponse(
            appointment_id=appointment_id,
            data=appointment_data,
            status=ResponseStatus.SUCCESS
        )

    except (AppointmentException, DatabaseConnectionException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to retrieve appointment: {str(e)}"}
        )

@router.put(
    "",
    responses={
        404: {"description": "Appointment not found"},
        422: {"description": "Invalid appointment data"},
        500: {"description": "Internal server error"}
    },
    response_model=UpdateAppointmentResponse
)
async def update_appointment(appointment: AppointmentUpdateModel):
    """
    Update an existing appointment.
    
    Args:
        phone_number: The phone number of the appointment to update
        appointment: The appointment update data
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If appointment is not found, data is invalid, or an error occurs
    """
    try:
        # Parse the payload
        customer_data = appointment.model_dump(exclude_none=True)

        # Update the appointment
        updated = appointment_service.update_appointment(customer_data)
        response_status = ResponseStatus.SUCCESS if updated else ResponseStatus.FAILED

        return UpdateAppointmentResponse(
            updated=updated,
            data=customer_data,
            status=response_status
        )

    except (AppointmentException, DatabaseConnectionException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to update appointment: {str(e)}"}
        )


@router.delete(
    "",
    responses={
        400: {"description": "Invalid phone number format"},
        404: {"description": "Appointment not found"},
        500: {"description": "Internal server error"}
    },
    response_model=DeleteAppointmentResponse
)
async def delete_appointment_by_phone_number(
        phone_number: str = Query(..., description="Customer phone number")
):
    """
    Delete an appointment by phone number.

    Args:
        phone_number: The phone number to search

    Returns:
        dict: Success message

    Raises:
        HTTPException: If appointment is not found, phone number is invalid, or an error occurs
    """
    try:
        # Decode URL-encoded phone number
        decoded_phone = unquote(phone_number)

        # Get contact info from vector store
        success = appointment_service.delete_appointment_by_phone_number(decoded_phone)
        response_status = ResponseStatus.SUCCESS if success else ResponseStatus.FAILED

        return DeleteAppointmentResponse(
            phone_number=phone_number,
            deleted=success,
            status=response_status
        )

    except (AppointmentException, DatabaseConnectionException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to retrieve appointment: {str(e)}"}
        )
