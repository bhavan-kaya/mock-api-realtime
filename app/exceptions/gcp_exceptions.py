from fastapi import status

class GCPException(Exception):
    """Base exception for GCP related errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)

class GCPFileNotFoundError(GCPException):
    """Raised when a requested file is not found in GCP storage"""
    def __init__(self, sid: str, file_type: str):
        super().__init__(
            detail=f"{file_type.capitalize()} file not found for SID: {sid}",
            status_code=status.HTTP_404_NOT_FOUND
        )

class GCPStorageError(GCPException):
    """Raised when there's an error accessing GCP storage"""
    def __init__(self, detail: str):
        super().__init__(
            detail=f"GCP Storage error: {detail}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class InvalidSIDError(GCPException):
    """Raised when an invalid SID is provided"""
    def __init__(self, sid: str):
        super().__init__(
            detail=f"Invalid SID format: {sid}",
            status_code=status.HTTP_400_BAD_REQUEST
        )
