from fastapi import status


class ConversationException(Exception):
    """Base exception for conversation related errors"""
    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE
    detail: str = "An error occurred while processing the conversation data."

    def __init__(self, detail: str = None, status_code: int = None):
        if detail:
            self.detail = detail
        if status_code:
            self.status_code = status_code
        super().__init__(self.detail)


class ConversationAlreadyExistsException(ConversationException):
    """Exception raised when a conversation already exists."""
    status_code = status.HTTP_409_CONFLICT
    detail = "Call with SID already exists. Please try again."
