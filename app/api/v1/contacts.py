from urllib.parse import unquote
from fastapi import APIRouter, status, HTTPException, Query
import logging

from app.models.contact_model import (
    SaveContactRequest,
    GetContactRequest,
    DeleteContactRequest,
    ContactResponse,
    GetContactResponse,
    ContactListResponse,
    StatusResponse
)
from app.services.contact_service import (
    ContactInfoService,
    ContactNotFoundException,  
    ContactAlreadyExistsException
)
from app.exceptions.database.database_connection_exception import DatabaseConnectionException
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts")

contact_service = ContactInfoService()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StatusResponse,
    responses={
        409: {"description": "Contact already exists (will be updated)"},
        422: {"description": "Invalid contact data"},
        500: {"description": "Internal server error"}
    }
)
async def save_contact(contact: SaveContactRequest):
    """
    Create or update a contact.

    Args:
        contact: The contact data including customer name and phone number

    Returns:
        StatusResponse: The created/updated contact ID and success message

    Raises:
        HTTPException: If data is invalid or an error occurs
    """
    try:
        # Save or update the contact
        contact_id = contact_service.save_contact_info(
            customer_name=contact.customer_name,
            contact_number=contact.contact_number,
            date=contact.date
        )

        if contact_id:
            return StatusResponse(
                status="success",
                message="Contact saved successfully",
                id=str(contact_id)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"detail": "Failed to save contact"}
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to save contact: {str(e)}"}
        )


@router.get(
    "",
    response_model=GetContactResponse,
    responses={
        400: {"description": "Invalid phone number format"},
        404: {"description": "Contact not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_contact(
    phone_number: str = Query(..., description="Customer phone number")
):
    """
    Get a contact by phone number.
    
    Args:
        phone_number: The phone number to search
        
    Returns:
        GetContactResponse: The contact data with previous conversation summary
        
    Raises:
        HTTPException: If contact is not found, phone number is invalid, or an error occurs
    """
    try:
        # Decode URL-encoded phone number
        decoded_phone = unquote(phone_number)

        # Get contact info
        contact = contact_service.get_customer_by_contact(decoded_phone)

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"detail": f"Contact not found for phone number: {decoded_phone}"}
            )

        return GetContactResponse(**contact)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to retrieve contact: {str(e)}"}
        )


@router.get(
    "/all",
    response_model=ContactListResponse,
    responses={
        500: {"description": "Internal server error"}
    }
)
async def get_all_contacts():
    """
    Get all contacts.
    
    Returns:
        ContactListResponse: List of all contacts
        
    Raises:
        HTTPException: If an error occurs
    """
    try:
        contacts = contact_service.get_all_contacts()
        
        return ContactListResponse(
            contacts=[ContactResponse(**contact) for contact in contacts],
            total=len(contacts)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": f"Failed to retrieve contacts: {str(e)}"}
        )


@router.put(
    "",
    response_model=StatusResponse,
    responses={
        404: {"description": "Contact not found"},
        422: {"description": "Invalid contact data"},
        500: {"description": "Internal server error"}
    }
)
async def update_contact(
    phone_number: str = Query(..., description="Current phone number"),
    customer_name: Optional[str] = Query(None, description="New customer name"),
    new_phone_number: Optional[str] = Query(None, description="New phone number")
):
    """
    Update an existing contact.
    """
    try:
        # Decode URL-encoded phone number
        decoded_phone = unquote(phone_number)

        # Update the contact - this will raise ContactNotFoundException if not found
        success = contact_service.update_contact_by_phone(
            contact_number=decoded_phone,
            customer_name=customer_name,
            new_contact_number=new_phone_number
        )

        return StatusResponse(
            status="success",
            message="Contact updated successfully"
        )

    except ContactNotFoundException as e:
        # Handle the case when contact is not found - return 404
        logger.warning(f"Contact not found for update: {decoded_phone}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail
        )
    
    except DatabaseConnectionException as e:
        # Handle database connection errors - return 503
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.detail
        )
    
    except Exception as e:
        # Handle any other unexpected errors - return 500
        logger.error(f"Unexpected error while updating contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update contact: {str(e)}"
        )

@router.delete(
    "",
    response_model=StatusResponse,
    responses={
        400: {"description": "Invalid phone number format"},
        404: {"description": "Contact not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_contact(
    phone_number: str = Query(..., description="Customer phone number")
):
    """
    Delete a contact by phone number.

    Args:
        phone_number: The phone number to delete

    Returns:
        StatusResponse: Success message

    Raises:
        HTTPException: If contact is not found, phone number is invalid, or an error occurs
    """
    try:
        # Decode URL-encoded phone number
        decoded_phone = unquote(phone_number)

        # Delete the contact - this will raise ContactNotFoundException if not found
        success = contact_service.delete_contact_by_phone(decoded_phone)

        return StatusResponse(
            status="success",
            message="Contact deleted successfully"
        )

    except ContactNotFoundException as e:
        # Handle the case when contact is not found - return 404
        logger.warning(f"Contact not found for deletion: {decoded_phone}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.detail
        )
    
    except DatabaseConnectionException as e:
        # Handle database connection errors - return 503
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.detail
        )
    
    except Exception as e:
        # Handle any other unexpected errors - return 500
        logger.error(f"Unexpected error while deleting contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete contact: {str(e)}"
        )