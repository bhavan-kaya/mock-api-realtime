from fastapi import APIRouter, status, HTTPException

from app.models.appointment_request_model import AppointmentRequestModel
from app.models.appointment_update_model import AppointmentUpdateModel
from app.services.appointments_service import AppointmentService
from app.exceptions import (
    AppointmentNotFoundError,
    AppointmentAlreadyExistsError,
    AppointmentDataError
)

# Initialize the router
router = APIRouter(prefix="/appointments")


@router.get(
    "/{phone_number}",
    responses={
        404: {"description": "Appointment not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_appointment_by_phone_number(phone_number: str):
    """
    Get an appointment by phone number.
    
    Args:
        phone_number: The phone number to search for
        
    Returns:
        dict: The appointment data
        
    Raises:
        HTTPException: If appointment is not found or an error occurs
    """
    try:
        return await AppointmentService.get_appointment_by_phone_number(phone_number)
    except AppointmentNotFoundError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"detail": str(e.detail) if hasattr(e, 'detail') else str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to retrieve appointment: {str(e)}"}
        )

@router.put(
    "/{phone_number}",
    responses={
        404: {"description": "Appointment not found"},
        422: {"description": "Invalid appointment data"},
        500: {"description": "Internal server error"}
    }
)
async def update_appointment(phone_number: str, appointment: AppointmentUpdateModel):
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
        return await AppointmentService.update_appointment(
            phone_number=phone_number,
            update_data=appointment.customer_data
        )
    except (AppointmentNotFoundError, AppointmentDataError) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"detail": str(e.detail) if hasattr(e, 'detail') else str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to update appointment: {str(e)}"}
        )

@router.post(
    "/appointments",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Appointment already exists"},
        422: {"description": "Invalid appointment data"},
        500: {"description": "Internal server error"}
    }
)
async def save_appointment(appointment: AppointmentRequestModel):
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
        return await AppointmentService.create_appointment(
            phone_number=appointment.customer_phone_number,
            customer_data=appointment.customer_data
        )
    except (AppointmentAlreadyExistsError, AppointmentDataError) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"detail": str(e.detail) if hasattr(e, 'detail') else str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to create appointment: {str(e)}"}
        )
