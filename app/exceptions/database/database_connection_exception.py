from fastapi import status


class DatabaseConnectionException(Exception):
    """
    Exception raised when a database connection fails.
    """
    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE
    detail: str = "An error occurred while connecting to the database."

    def __init__(self, detail: str = None, status_code: int = None):
        if detail:
            self.detail = detail
        if status_code:
            self.status_code = status_code
        super().__init__(self.detail)
