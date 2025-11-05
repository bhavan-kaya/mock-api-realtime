from fastapi import APIRouter, HTTPException, status, Query

from app.exceptions.conversation.conversation_exception import ConversationException
from app.exceptions.database.database_connection_exception import DatabaseConnectionException
from app.models.conversation.customer_data_request_model import CustomerDataRequestModel
from app.models.conversation.customer_data_response_model import (
    CustomerDataResponseModel,
    CustomerResponseModel
)
from app.models.enum.response_status import ResponseStatus
from app.services.conversation_service import conversation_service

# Create API router
router = APIRouter(prefix="/conversations")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Call with SID already exists. Please try again."},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    },
    response_model=CustomerResponseModel
)
async def create_conversation_data(call_data: CustomerDataRequestModel):
    """
    Save conversation data to the database.

    Args:
        call_data (CustomerDataRequestModel): The conversation data to save

    Returns:
        CustomerResponseModel: Customer ID with the request status
    """
    try:
        customer_id = conversation_service.save_conversation_data(call_data)
        return CustomerResponseModel(
            customer_id=customer_id,
            data=call_data,
            status=ResponseStatus.SUCCESS
        )

    except (ConversationException, DatabaseConnectionException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating a conversation record. Please try again later."
        )


@router.get(
    "",
    responses={
        400: {"description": "Invalid page or per_page parameter"},
        404: {"description": "No data found for the given page"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    },
    response_model=CustomerDataResponseModel
)
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
        conversation_data = conversation_service.get_conversation_data(
            page=page,
            per_page=per_page
        )
        return conversation_data

    except (ConversationException, DatabaseConnectionException) as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching conversation records. Please try again later."
        )
