from fastapi import APIRouter, HTTPException, status, Response, Query
from fastapi.responses import StreamingResponse
import io
import logging

from app.services.storage import storage_factory
from app.models.gcp_data_model import FileType
from app.exceptions.gcp_exceptions import (
    BlobFileNotFoundError,
    StorageError,
    InvalidSIDError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations")

# Create the storage instance
storage = storage_factory.get_storage()


async def _create_response(sid: str, file_type: FileType):
    """
    Internal helper to fetch any file type (binary or text)
    """
    try:
        filename: str
        content_type: str
        content_bytes: bytes

        # Check the file type to call the correct storage method
        if file_type in (FileType.TRANSCRIPT, FileType.SUMMARY):
            # --- Handle Text Files ---
            text_response = await storage.get_text_file(sid, file_type)
            filename = text_response.filename
            content_type = text_response.content_type

            # Encode the string content to bytes for StreamingResponse
            content_bytes = text_response.content.encode("utf-8")

        else:
            # --- Handle Binary Audio Files ---
            file_response = await storage.get_file(sid, file_type)
            filename = file_response.filename
            content_type = file_response.content_type
            content_bytes = file_response.content

        # Wrap the in-memory bytes in io.BytesIO for streaming
        content_stream = io.BytesIO(content_bytes)

        return StreamingResponse(
            content_stream,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
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


@router.get("/recording", response_class=StreamingResponse)
async def get_recording(
        sid: str = Query(..., description="The session ID to retrieve the recording for")
):
    """
    Retrieve the audio recording file for a given SID.
    
    Args:
        sid: The session ID to retrieve the recording for
        
    Returns:
        StreamingResponse: The audio file as a streaming response
    """
    return await _create_response(
        sid=sid,
        file_type=FileType.RECORDING
    )

@router.get("/synopsis", response_class=StreamingResponse)
async def get_synopsis(
        sid: str = Query(..., description="The session ID to retrieve the synopsis for")
):
    """
    Retrieve the synopsis audio file for a given SID.
    
    Args:
        sid: The session ID to retrieve the synopsis for
        
    Returns:
        StreamingResponse: The audio file as a streaming response
    """
    return await _create_response(
        sid=sid,
        file_type=FileType.SYNOPSIS
    )

@router.get("/transcript", response_class=StreamingResponse)
async def get_transcript(
        sid: str = Query(..., description="The session ID to retrieve the transcript for")
):
    """
    Retrieve the transcript text file for a given SID.
    
    Args:
        sid: The session ID to retrieve the transcript for
        
    Returns:
        Response: The transcript file as a streaming response
    """
    return await _create_response(
        sid=sid,
        file_type=FileType.TRANSCRIPT
    )

@router.get("/summary", response_class=StreamingResponse)
async def get_summary(
        sid: str = Query(..., description="The session ID to retrieve the summary for")
):
    """
    Retrieve the summary text file for a given SID.
    
    Args:
        sid: The session ID to retrieve the summary for
        
    Returns:
        Response: The summary file as a streaming response
    """
    return await _create_response(
        sid=sid,
        file_type=FileType.SUMMARY
    )

@router.get("/latest", response_class=Response)
async def get_latest_file(file_type: FileType):
    """
    Retrieve the latest created/modified file for the given file type.

    Args:
        file_type: Type of file to retrieve

    Returns:
        Response: The requested file
    """
    try:
        # Get the latest SID
        sid = await storage.get_latest_sid(file_type)

    except BlobFileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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

    # Get the corresponding file
    return await _create_response(
        sid=sid,
        file_type=file_type
    )