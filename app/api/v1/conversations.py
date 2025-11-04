import logging

from fastapi import APIRouter, HTTPException, status, Query

from app.models.enum.response_status import ResponseStatus
from app.models.conversation.customer_data_request_model import CustomerDataRequestModel
from app.models.conversation.customer_data_response_model import (
    CustomerDataResponseModel,
    CustomerResponseModel
)
from app.services.conversation_service import conversation_service
from app.exceptions.conversation.conversation_exception import ConversationException


# Get logger
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/conversations")


@router.get("", response_model=CustomerDataResponseModel)
async def get_conversation_data(
        page: int = Query(1, description="Number of pages to return"),
        per_page: int = Query(10, le=100, description="Number of items per page"),
):
    """
    Retrieve the conversation data from the database
    
    Args:
        page (int): Number of pages to return
        per_page (int): Number of items per page
        
    Returns:
        CustomerDataResponseModel: The conversation artifacts from the database
    """
    try:
        conversation_data = await conversation_service.get_conversation_data(
            page=page,
            per_page=per_page
        )
        return conversation_data

    except Exception as e:
        logger.error(f"Unexpected error in get_conversation_data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.post("", response_model=CustomerResponseModel)
async def save_conversation_data(call_data: CustomerDataRequestModel):
    """
    Save conversation data to the database.

    Args:
        call_data (CustomerDataRequestModel): The conversation data to save

    Returns:
        CustomerResponseModel: Customer ID with the request status
    """
    try:
        customer_id = await conversation_service.save_conversation_data(call_data)
        return CustomerResponseModel(
            customer_id=customer_id,
            status=ResponseStatus.SUCCESS
        )

    except Exception as e:
        if isinstance(e, ConversationException):
            raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
        logger.error(f"Unexpected error in save_conversation_data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )
