import logging

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import StreamingResponse

from app.exceptions.gcp_exceptions import (
    BlobFileNotFoundError,
    StorageError,
    InvalidSIDError
)
from app.services.storage import storage_factory
from app.models.storage_response_model import StorageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations")

# Create the storage instance
storage = storage_factory.get_storage()


@router.get("", response_model=StorageResponse)
async def get_conversation(
        sid: str = Query(..., description="The session ID to retrieve the recording for")
):
    """
    Retrieve the audio recording file for a given SID.
    
    Args:
        sid: The session ID to retrieve the recording for
        
    Returns:
        StreamingResponse: The audio file as a streaming response
    """
    try:
        conversation_data = await storage.get_all_files_in_sid(sid)

        # Create the response model
        return StorageResponse(
            sid=sid,
            data=conversation_data
        )

    except BlobFileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidSIDError as e:
        logger.error(f"SID error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except StorageError as e:
        logger.error(f"Storage error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
