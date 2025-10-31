from google.cloud import storage
from pathlib import Path
from typing import Optional
import logging
import asyncio

from app.models.gcp_data_model import GCPFileResponse, GCPTextResponse, FileType
from app.exceptions.gcp_exceptions import (
    BlobFileNotFoundError,
    StorageError,
    InvalidSIDError
)
from config import GCS_BUCKET_NAME, GCP_CREDENTIALS_PATH


# Initialize logger
logger = logging.getLogger(__name__)


class GCPService:
    def __init__(self):
        """
        Initialize GCP Storage client.
        """
        try:
            # Initialize the client with service account credentials
            logger.info(f"Initializing GCP Storage client with credentials: {GCP_CREDENTIALS_PATH}")
            self.client = storage.Client.from_service_account_json(GCP_CREDENTIALS_PATH)

            self.bucket = self.client.bucket(GCS_BUCKET_NAME)
            logger.info(f"Successfully initialized GCP Storage client with bucket: {GCS_BUCKET_NAME}")

        except FileNotFoundError as e:
            error_msg = f"Service account credentials file not found at: {GCP_CREDENTIALS_PATH}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to initialize GCP Storage client: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e

    @classmethod
    def _validate_sid(cls, sid: str) -> None:
        """Validate the SID format."""
        if not sid or not isinstance(sid, str) or len(sid.strip()) == 0:
            raise InvalidSIDError(sid)

    @classmethod
    def _download_blob(cls, found_blob):
        """
        Download a blob as bytes from the bucket.
        """
        return found_blob.download_as_bytes()

    def _find_latest_sid_blocking(self) -> Optional[str]:
        latest_blob = None
        try:
            # This iterates through all blobs in the bucket
            all_blobs = self.client.list_blobs(self.bucket)

            # We must iterate to find the one with the max 'updated' time
            for blob in all_blobs:
                if not blob.updated:  # Skip blobs without an update time
                    continue

                if latest_blob is None or blob.updated > latest_blob.updated:
                    latest_blob = blob

        except Exception as e:
            # Log the GCS error and re-raise as a standard type
            logger.error(f"Failed during blob listing or comparison: {str(e)}")
            raise StorageError(f"Failed to list blobs: {str(e)}") from e

        if not latest_blob:
            logger.warning(f"No blobs found in bucket {self.bucket.name}")
            return None

        # Now we have the latest_blob. Extract its SID.
        # The name looks like "sid/filename.txt" or "sid/subdir/file.txt"
        # We want the first part of the path.
        try:
            # Ensure name is not None or empty
            if not latest_blob.name:
                logger.warning(f"Latest blob has no name.")
                return None

            parts = latest_blob.name.split('/')
            if len(parts) > 1:
                # It's in a folder, e.g., "sid/file.txt"
                sid = parts[0]
                logger.info(f"Found latest blob '{latest_blob.name}' (updated: {latest_blob.updated}). SID: {sid}")
                return sid
            else:
                # It's a root file, e.g., "readme.txt"
                logger.warning(f"Latest blob '{latest_blob.name}' is at the root. Cannot extract SID.")
                return None

        except Exception as ex:
            logger.warning(f"Error processing blob name '{latest_blob.name}': {str(ex)}")
            return None

    def _list_and_find_blob(self, directory_prefix: str, file_prefix: str):
        """
        Finds the corresponding file from the Bucket
        """
        # List blobs in the directory
        blobs = self.client.list_blobs(self.bucket, prefix=directory_prefix)

        for blob in blobs:
            # Get the filename part (e.g., "recording_xxx.mp3")
            filename = blob.name.split('/')[-1]

            # Check if the filename starts with the required prefix
            if filename.startswith(file_prefix):
                logger.debug(f"Found matching blob: {blob.name}")
                return blob  # Return the first match

        return None  # No match found

    async def get_file(self, sid: str, file_type: FileType) -> GCPFileResponse:
        """
        Retrieve a file from GCS by SID and file type.
        Searches for a file starting with the file_type prefix (e.g., "recording_")
        within the SID directory.
        
        Args:
            sid: The unique session ID (conversation_id)
            file_type: Type of file to retrieve (recording, synopsis, transcript, summary)
            
        Returns:
            GCPFileResponse containing the file content and metadata
            
        Raises:
            GCPFileNotFoundError: If the file is not found
            GCPStorageError: If there's an error accessing GCS
            InvalidSIDError: If the SID is invalid
        """
        try:
            self._validate_sid(sid)
            
            # Define the prefix for the file based on its type (e.g., "recording_")
            file_prefix = f"{file_type.value}_"

            # Define the directory prefix to search in (e.g., "sid/")
            directory_prefix = f"{sid}/"

            logger.info(f"Searching for blob starting with '{file_prefix}' in directory '{directory_prefix}'")

            # Get the current event loop
            loop = asyncio.get_running_loop()

            # Run the blocking search function in a thread
            found_blob = await loop.run_in_executor(
                None,
                self._list_and_find_blob,
                directory_prefix,
                file_prefix
            )
            if not found_blob:
                logger.warning(f"No file found for SID {sid} with prefix '{file_prefix}'")
                raise BlobFileNotFoundError(sid, file_type.value)

            # Run the blocking download in a thread
            content = await loop.run_in_executor(
                None,
                self._download_blob,
                found_blob
            )
            
            return GCPFileResponse(
                sid=sid,
                file_type=file_type,
                content=content,
                content_type="application/octet-stream", # Generic type
                filename=Path(found_blob.name).name
            )
            
        except BlobFileNotFoundError:
            raise
        except InvalidSIDError:
            raise
        except Exception as e:
            error_message = f"Error retrieving {file_type} for SID {sid}: {str(e)}"
            logger.error(error_message)
            raise StorageError(error_message)

    async def get_text_file(self, sid: str, file_type: FileType) -> GCPTextResponse:
        """
        Retrieve a text file from GCS by SID and file type and return as string.
        
        Args:
            sid: The unique session ID
            file_type: Type of text file to retrieve (transcript or summary)
            
        Returns:
            GCPTextResponse containing the text content and metadata
            
        Raises:
            GCPFileNotFoundError: If file is not found
            GCPStorageError: If there's an error accessing GCS
            ValueError: If file_type is not transcript or summary
        """
        if file_type not in [FileType.TRANSCRIPT, FileType.SUMMARY]:
            logger.error(f"Invalid file_type for get_text_file: {file_type.value}")
            raise ValueError("File type must be either 'transcript' or 'summary'")
            
        try:
            # get_file now handles the prefix-based search and async I/O
            file_response = await self.get_file(sid, file_type)
            
            # Decoding is fast, no need for executor
            content = file_response.content
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            return GCPTextResponse(
                sid=sid,
                file_type=file_type,
                content=content,
                content_type="text/plain",
                filename=file_response.filename
            )
            
        except Exception as e:
            logger.error(f"Error retrieving text {file_type} for SID {sid}: {str(e)}")

            # Re-raise exceptions we expect
            if isinstance(e, (BlobFileNotFoundError, StorageError, InvalidSIDError, ValueError)):
                raise

            # Wrap unexpected errors
            raise StorageError(f"Failed to retrieve {file_type}: {str(e)}")

    async def get_latest_sid(self, file_type: FileType) -> Optional[str]:
        """
        Retrieves the SID (top-level folder) that contains the most recently
        modified object in the bucket.

        Args:
            file_type: Type of file to retrieve

        Returns:
            The latest SID as a string, or None if the bucket is empty or
            the latest object is at the root.

        Raises:
            GCPStorageError: If there's an error accessing GCS.
        """
        logger.info(f"Attempting to find the latest SID in bucket {self.bucket.name}")

        loop = asyncio.get_running_loop()
        try:
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
            if isinstance(e, StorageError):
                raise
            if isinstance(e, BlobFileNotFoundError):
                raise
            raise StorageError(f"Failed to find latest SID: {str(e)}")
