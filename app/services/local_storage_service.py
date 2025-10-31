import os
import shutil
from pathlib import Path
from typing import Optional, Union, BinaryIO, TextIO
import logging
from enum import Enum

from app.models.gcp_data_model import GCPFileResponse, GCPTextResponse, FileType
from app.exceptions.gcp_exceptions import (
    GCPFileNotFoundError, 
    GCPStorageError,
    InvalidSIDError
)

logger = logging.getLogger(__name__)

class LocalStorageService:
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize Local Storage service.
        
        Args:
            base_path: Base directory for storing files. Defaults to 'userdata' in the current directory.
        """
        self.base_path = Path(base_path) if base_path else Path("userdata")
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized Local Storage at: {self.base_path.absolute()}")

    def _validate_sid(self, sid: str) -> None:
        """Validate the SID format."""
        if not sid or not isinstance(sid, str) or len(sid.strip()) == 0:
            raise InvalidSIDError(sid)

    def _get_file_path(self, sid: str, file_type: FileType) -> Path:
        """Generate the file path based on SID and file type with proper prefix."""
        self._validate_sid(sid)
        
        # Map file types to their respective prefixes and extensions
        file_info = {
            FileType.RECORDING: ("recording_", ".mp3"),
            FileType.SYNOPSIS: ("synopsis_", ".mp3"),
            FileType.TRANSCRIPT: ("transcript_", ".txt"),
            FileType.SUMMARY: ("summary_", ".txt")
        }.get(file_type, ("", ""))
        
        # Get prefix and file extension
        prefix, file_ext = file_info

        # List the files in the directory
        sid_dir = self.base_path / sid
        files = os.listdir(sid_dir)

        # Check if the file exists using glob
        file_pattern = f"{prefix}*{file_ext}"
        matching_files = list(sid_dir.glob(file_pattern))
        
        return sid_dir / matching_files[0] if matching_files else None

    async def get_file(self, sid: str, file_type: FileType) -> GCPFileResponse:
        """
        Retrieve a file from local storage by SID and file type.
        
        Args:
            sid: The unique session ID
            file_type: Type of file to retrieve (recording, synopsis, transcript, summary)
            
        Returns:
            GCPFileResponse containing the file content and metadata
            
        Raises:
            GCPFileNotFoundError: If the file is not found
            GCPStorageError: If there's an error accessing the file
        """
        try:
            file_path = self._get_file_path(sid, file_type)
            if not file_path:
                raise GCPFileNotFoundError(sid, file_type.value)
            
            # Read the file content
            content = file_path.read_bytes()
            content_type = self._get_content_type(file_type)
            
            return GCPFileResponse(
                sid=sid,
                file_type=file_type,
                content=content,
                content_type=content_type,
                filename=file_path.name
            )
            
        except GCPFileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving {file_type} for SID {sid}: {str(e)}")
            raise GCPStorageError(f"Failed to retrieve {file_type}: {str(e)}")

    async def get_text_file(self, sid: str, file_type: FileType) -> GCPTextResponse:
        """
        Retrieve a text file from local storage by SID and file type.
        
        Args:
            sid: The unique session ID
            file_type: Type of text file to retrieve (transcript or summary)
            
        Returns:
            GCPTextResponse containing the text content and metadata
            
        Raises:
            GCPFileNotFoundError: If the file is not found
            GCPStorageError: If there's an error accessing the file
        """
        if file_type not in [FileType.TRANSCRIPT, FileType.SUMMARY]:
            raise ValueError("File type must be either 'transcript' or 'summary'")
            
        try:
            file_path = self._get_file_path(sid, file_type)
            
            if not file_path.exists():
                raise GCPFileNotFoundError(sid, file_type.value)
                
            # Read the actual .txt file
            content = file_path.read_text(encoding='utf-8')
            
            return GCPTextResponse(
                sid=sid,
                file_type=file_type,
                content=content,
                content_type="text/plain",
                filename=file_path.name
            )
            
        except GCPFileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving text {file_type} for SID {sid}: {str(e)}")
            raise GCPStorageError(f"Failed to retrieve {file_type}: {str(e)}")

    def _get_content_type(self, file_type: FileType) -> str:
        """Get the content type based on file type."""
        return {
            FileType.RECORDING: "audio/mpeg",
            FileType.SYNOPSIS: "audio/mpeg",
            FileType.TRANSCRIPT: "text/plain",
            FileType.SUMMARY: "text/plain"
        }.get(file_type, "application/octet-stream")
