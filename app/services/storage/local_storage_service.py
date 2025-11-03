from datetime import datetime
import logging
import asyncio
from pathlib import Path
from typing import Optional

from app.exceptions.gcp_exceptions import (
    BlobNotFoundError,
    StorageError,
    InvalidSIDError
)
from app.models.storage_response_model import FileData


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
    def _validate_sid(cls, sid: str) -> None:
        """Validate the SID format."""
        if not sid or not isinstance(sid, str) or len(sid.strip()) == 0:
            raise InvalidSIDError(sid)

    @classmethod
    def _list_all_files_blocking(cls, sid_dir: Path) -> list[FileData]:
        """
        (Blocking) Lists all absolute file paths for a given SID directory.
        """
        if not sid_dir.is_dir():
            logger.debug(f"SID directory not found or is not a directory: {sid_dir}")
            return []

        try:
            # Use rglob to find all files recursively
            # Convert to str and return absolute paths
            file_paths = [
                FileData(
                    file_name=file_path.name,
                    url=str(file_path.absolute()),
                    last_modified=datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat()
                )
                for file_path in sid_dir.rglob('*') 
                if file_path.is_file()
            ]

            logger.debug(f"Found {len(file_paths)} files in '{sid_dir}'")
            return file_paths

        except Exception as e:
            error_msg = f"Failed (blocking) to list files for directory '{sid_dir}': {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e

    async def get_all_files_in_sid(self, sid: str) -> list[FileData]:
        """
        Retrieves a list of all file paths (absolute paths) within a given SID directory.

        Args:
            sid: The unique session ID (conversation_id)

        Returns:
            A list of strings, where each string is the absolute path
            to a file in that SID's directory.
            Returns an empty list if the directory is empty or doesn't exist.

        Raises:
            InvalidSIDError: If the SID is invalid.
            StorageError: If there's an error accessing the filesystem.
        """
        try:
            self._validate_sid(sid)

            # Define the directory to search in
            sid_dir = self.base_path / sid

            logger.info(f"Listing all files in local directory: '{sid_dir}'")

            # Get the current event loop
            loop = asyncio.get_running_loop()

            # Run the blocking list function in a thread
            file_paths = await loop.run_in_executor(
                None,
                self._list_all_files_blocking,
                sid_dir
            )
            if not file_paths:
                raise BlobNotFoundError(sid=sid)

            return file_paths

        except Exception as e:
            error_message = f"Error listing files for SID {sid}: {str(e)}"
            logger.error(error_message)
            raise
