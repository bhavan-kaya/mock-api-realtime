import logging
import os
import asyncio
from pathlib import Path
from typing import Optional

from app.exceptions.gcp_exceptions import (
    BlobFileNotFoundError,
    StorageError,
    InvalidSIDError
)
from app.models.gcp_data_model import GCPFileResponse, GCPTextResponse, FileType


# Initialize logger
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

    @classmethod
    def _get_content_type(cls, file_type: FileType) -> str:
        """Get the content type based on file type."""
        return {
            FileType.RECORDING: "audio/mpeg",
            FileType.SYNOPSIS: "audio/mpeg",
            FileType.TRANSCRIPT: "text/plain",
            FileType.SUMMARY: "text/plain"
        }.get(file_type, "application/octet-stream")

    @classmethod
    def _validate_sid(cls, sid: str) -> None:
        """Validate the SID format."""
        if not sid or not isinstance(sid, str) or len(sid.strip()) == 0:
            raise InvalidSIDError(sid)

    def _find_latest_sid_blocking(self) -> Optional[str]:
        latest_sid = None
        latest_mod_time = 0.0

        try:
            # Iterate through all entries in the base path
            for sid_entry in self.base_path.iterdir():
                if not sid_entry.is_dir():
                    continue  # Skip files at the root

                current_sid = sid_entry.name
                current_sid_latest_mod_time = 0.0
                found_file_in_sid = False

                # Recursively walk through the SID directory
                for root, _, files in os.walk(sid_entry):
                    for file in files:
                        found_file_in_sid = True
                        file_path = Path(root) / file
                        try:
                            mod_time = file_path.stat().st_mtime
                            if mod_time > current_sid_latest_mod_time:
                                current_sid_latest_mod_time = mod_time

                        except FileNotFoundError:
                            # File might be deleted during iteration, safe to ignore
                            continue

                # Now compare this SID's latest time to the overall latest
                if found_file_in_sid and current_sid_latest_mod_time > latest_mod_time:
                    latest_mod_time = current_sid_latest_mod_time
                    latest_sid = current_sid

            if latest_sid:
                logger.info(f"Found latest SID '{latest_sid}' (mod time: {latest_mod_time})")
            else:
                logger.warning(f"No SIDs or files found in {self.base_path}")
            return latest_sid

        except Exception as e:
            logger.error(f"Error scanning local directory {self.base_path}: {e}")
            raise StorageError(f"Failed to scan local storage: {str(e)}")

    def _get_file_path(self, sid: str, file_type: FileType) -> Optional[Path]:
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
        
        # Check if the directory exists
        if not sid_dir.exists():
            return None

        # Check if the file exists using glob
        file_pattern = f"{prefix}*{file_ext}"
        matching_files = list(sid_dir.glob(file_pattern))

        return matching_files[0] if matching_files else None

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
                raise BlobFileNotFoundError(sid, file_type.value)
            
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
            
        except BlobFileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving {file_type} for SID {sid}: {str(e)}")
            raise StorageError(f"Failed to retrieve {file_type}: {str(e)}")

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
                raise BlobFileNotFoundError(
                    sid=sid,
                    file_type=str(file_type.value)
                )
                
            # Read the actual .txt file
            content = file_path.read_text(encoding='utf-8')
            
            return GCPTextResponse(
                sid=sid,
                file_type=file_type,
                content=content,
                content_type="text/plain",
                filename=file_path.name
            )
            
        except BlobFileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving text {file_type} for SID {sid}: {str(e)}")
            raise StorageError(f"Failed to retrieve {file_type}: {str(e)}")

    async def get_latest_sid(self, file_type: FileType) -> Optional[str]:
        """
        Retrieves the SID (top-level folder) that contains the most recently
        modified file in the local storage base_path.

        Args:
            file_type: Type of file to retrieve

        Returns:
            The latest SID as a string, or None if the base_path is empty.

        Raises:
            StorageError: If there's an error accessing the filesystem.
        """
        logger.info(f"Attempting to find the latest SID in {self.base_path}")

        loop = asyncio.get_running_loop()
        try:
            # Run the blocking filesystem scan in an executor
            latest_sid = await loop.run_in_executor(
                executor=None,
                func=self._find_latest_sid_blocking
            )
            if latest_sid is None:
                raise BlobFileNotFoundError(
                    sid="None",
                    file_type=FileType.value,
                )
            return latest_sid

        except Exception as e:
            logger.error(f"Error finding latest SID: {str(e)}")
            if isinstance(e, GCPStorageError):
                raise
            if isinstance(e, BlobFileNotFoundError):
                raise
            raise GCPStorageError(f"Failed to find latest SID: {str(e)}")
