import asyncio
import logging
from pathlib import Path
from google.cloud import storage

from app.exceptions.gcp_exceptions import (
    BlobNotFoundError,
    StorageError,
    InvalidSIDError
)
from app.models.storage_response_model import FileData
from config import GCS_BUCKET_NAME, GCP_CREDENTIALS_PATH, GCS_BLOB_EXPIRATION


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
    def _generate_signed_url_blocking(cls, blob) -> str:
        """
        (Blocking) Generates a V4 signed URL for a blob.

        Note: The service account must have the 'Service Account Token Creator'
        IAM role (roles/iam.serviceAccountTokenCreator) on itself.
        """
        try:
            url = blob.generate_signed_url(
                version="v4",
                expiration=GCS_BLOB_EXPIRATION,
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(
                f"Failed to generate signed URL for {blob.name}. "
                f"Check if service account has 'Service Account Token Creator' role. Error: {str(e)}"
            )
            raise StorageError(f"Failed to sign URL: {str(e)}") from e

    def _list_all_files_blocking(self, directory_prefix: str) -> list[FileData]:
        """
        (Blocking) Lists all blob names for a given directory prefix.
        """
        try:
            blobs_iterator = self.client.list_blobs(self.bucket, prefix=directory_prefix)
            file_paths = [
                FileData(
                    file_name=Path(blob.name).name,
                    url=self._generate_signed_url_blocking(blob),
                    last_modified=blob.updated.isoformat() if blob.updated else None
                )
                for blob in blobs_iterator
                if not blob.name.endswith("/")
            ]

            logger.debug(f"Found {len(file_paths)} blobs for prefix '{directory_prefix}'")
            return file_paths

        except Exception as e:
            error_msg = f"Failed (blocking) to list blobs for prefix '{directory_prefix}': {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg) from e

    async def get_all_files_in_sid(self, sid: str) -> list[FileData]:
        """
        Retrieves a list of all file paths (blob names) within a given SID directory.

        Args:
            sid: The unique session ID (conversation_id)

        Returns:
            A list of strings, where each string is the full GCS path
            to a file in that SID's directory. (e.g., ["sid/file1.txt", "sid/file2.mp3"])
            Returns an empty list if the directory is empty or doesn't exist.

        Raises:
            InvalidSIDError: If the SID is invalid.
            StorageError: If there's an error accessing GCS.
        """
        try:
            self._validate_sid(sid)

            # Define the directory prefix to search in (e.g., "sid/")
            directory_prefix = f"{sid}/"

            logger.info(f"Listing all files in directory: '{directory_prefix}'")

            # Get the current event loop
            loop = asyncio.get_running_loop()

            # Run the blocking list function in a thread
            file_paths = await loop.run_in_executor(
                None,
                self._list_all_files_blocking,
                directory_prefix
            )
            if not file_paths:
                raise BlobNotFoundError(sid=sid)

            return file_paths

        except Exception as e:
            error_message = f"Error listing files for SID {sid}: {str(e)}"
            logger.error(error_message)
            raise
