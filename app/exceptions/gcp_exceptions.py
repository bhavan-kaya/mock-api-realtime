from fastapi import status

class DataException(Exception):
    """Base exception for data related errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)

class BlobNotFoundError(DataException):
    """Raised when a requested file is not found in the storage"""
    def __init__(self, sid: str):
        super().__init__(
            detail=f"No files found for SID: {sid}",
            status_code=status.HTTP_404_NOT_FOUND
        )

class StorageError(DataException):
    """Raised when there's an error accessing the storage"""
    def __init__(self, detail: str):
        super().__init__(
            detail=f"Storage error: {detail}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class InvalidSIDError(DataException):
    """Raised when an invalid SID is provided"""
    def __init__(self, sid: str):
        super().__init__(
            detail=f"Invalid SID format: {sid}",
            status_code=status.HTTP_400_BAD_REQUEST
        )
