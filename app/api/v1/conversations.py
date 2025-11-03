import logging

from fastapi import APIRouter, HTTPException, status, Query

from app.exceptions.gcp_exceptions import (
    DataException
)
from app.models.response_status import ResponseStatus
from app.models.storage_response_model import StorageResponse
from app.services.conversation_service import conversation_service


# Get logger
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/conversations")


@router.get("", response_model=StorageResponse)
async def get_post_conversation_artifacts(
        sid: str = Query(..., description="The session ID to retrieve the post conversation artifacts for")
):
    """
    Retrieve post conversation artifacts of a given SID.
    
    Args:
        sid: The session ID to retrieve the post conversation artifacts for
        
    Returns:
        StorageResponse: The post conversation artifacts as a storage response
    """
    try:
        post_conversation_data = await conversation_service.get_post_conversation_artifacts(sid)

        # Create the response model
        return StorageResponse(
            sid=sid,
            data=post_conversation_data,
            status=ResponseStatus.SUCCESS
        )

    except Exception as e:
        logger.error(f"Unexpected error in get_post_conversation_artifacts: {str(e)}")
        if isinstance(e, DataException):
            raise HTTPException(
                status_code=e.status_code,
                detail=str(e.detail)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )
