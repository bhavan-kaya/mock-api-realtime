from google.cloud import storage
from pathlib import Path
import logging
import asyncio

from app.models.gcp_data_model import GCPFileResponse, GCPTextResponse, FileType
from app.exceptions.gcp_exceptions import (
    GCPFileNotFoundError, 
    GCPStorageError,
    InvalidSIDError
)
from config import GCS_BUCKET_NAME, GCP_CREDENTIALS_PATH


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
            raise GCPStorageError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to initialize GCP Storage client: {str(e)}"
            logger.error(error_msg)
            raise GCPStorageError(error_msg) from e

    def _validate_sid(self, sid: str) -> None:
        """Validate the SID format."""
        if not sid or not isinstance(sid, str) or len(sid.strip()) == 0:
            raise InvalidSIDError(sid)

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

            # This is a blocking I/O operation, so run it in an executor
            def list_and_find_blob():
                # List blobs in the directory
                blobs = self.client.list_blobs(self.bucket, prefix=directory_prefix)

                for blob in blobs:
                    # Get the filename part (e.g., "recording_xxx.mp3")
                    filename = blob.name.split('/')[-1]
                    
                    # Check if the filename starts with the required prefix
                    if filename.startswith(file_prefix):
                        logger.info(f"Found matching blob: {blob.name}")
                        return blob # Return the first match
                
                return None # No match found

            # Run the blocking search function in a thread
            found_blob = await loop.run_in_executor(None, list_and_find_blob)
            
            if not found_blob:
                logger.warning(f"No file found for SID {sid} with prefix '{file_prefix}'")
                raise GCPFileNotFoundError(sid, file_type.value)
            
            # This is also a blocking I/O operation
            def download_blob():
                return found_blob.download_as_bytes()

            # Run the blocking download in a thread
            content = await loop.run_in_executor(None, download_blob)
            
            return GCPFileResponse(
                sid=sid,
                file_type=file_type,
                content=content,
                content_type="application/octet-stream", # Generic type
                filename=Path(found_blob.name).name
            )
            
        except GCPFileNotFoundError:
            raise
        except InvalidSIDError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving {file_type} for SID {sid}: {str(e)}")
            raise GCPStorageError(f"Failed to retrieve {file_type}: {str(e)}")

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
            if isinstance(e, (GCPFileNotFoundError, GCPStorageError, InvalidSIDError, ValueError)):
                raise

            # Wrap unexpected errors
            raise GCPStorageError(f"Failed to retrieve {file_type}: {str(e)}")
