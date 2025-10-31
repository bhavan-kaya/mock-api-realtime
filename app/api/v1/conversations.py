from fastapi import APIRouter, HTTPException, status, Response, Query
from fastapi.responses import StreamingResponse
import io
import logging

from app.services.storage import storage_factory
from app.models.gcp_data_model import FileType
from app.exceptions.gcp_exceptions import (
    GCPFileNotFoundError,
    GCPStorageError,
    InvalidSIDError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations")


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
    try:
        storage = storage_factory.get_storage()
        file_response = await storage.get_file(sid, FileType.RECORDING)
        return StreamingResponse(
            io.BytesIO(file_response.content),
            media_type=file_response.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_response.filename}"
            }
        )
    except GCPFileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    except GCPStorageError as e:
        logger.error(f"Storage error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=str(e)
        )
    except InvalidSIDError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
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
    try:
        storage = storage_factory.get_storage()
        file_response = await storage.get_file(sid, FileType.SYNOPSIS)
        return StreamingResponse(
            io.BytesIO(file_response.content),
            media_type=file_response.content_type,
            headers={"Content-Disposition": f"attachment; filename={file_response.filename}"}
        )
    except GCPFileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    except GCPStorageError as e:
        logger.error(f"Storage error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=str(e)
        )
    except InvalidSIDError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/transcript", response_class=Response)
async def get_transcript(
        sid: str = Query(..., description="The session ID to retrieve the transcript for")
):
    """
    Retrieve the transcript text file for a given SID.
    
    Args:
        sid: The session ID to retrieve the transcript for
        
    Returns:
        Response: The transcript file as a text/plain response
    """
    try:
        storage = storage_factory.get_storage()
        text_response = await storage.get_text_file(sid, FileType.TRANSCRIPT)
        return Response(
            content=text_response.content,
            media_type=text_response.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={text_response.filename}"
            }
        )
    except GCPFileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    except GCPStorageError as e:
        logger.error(f"Storage error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=str(e)
        )
    except InvalidSIDError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/summary", response_class=Response)
async def get_summary(
        sid: str = Query(..., description="The session ID to retrieve the summary for")
):
    """
    Retrieve the summary text file for a given SID.
    
    Args:
        sid: The session ID to retrieve the summary for
        
    Returns:
        Response: The summary file as a text/plain response
    """
    try:
        storage = storage_factory.get_storage()
        text_response = await storage.get_text_file(sid, FileType.SUMMARY)
        return Response(
            content=text_response.content,
            media_type=text_response.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={text_response.filename}"
            }
        )
    except GCPFileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    except GCPStorageError as e:
        logger.error(f"Storage error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=str(e)
        )
    except InvalidSIDError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
        