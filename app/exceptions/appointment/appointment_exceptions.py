from fastapi import status


class AppointmentException(Exception):
    """Base exception for appointment related errors"""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An error occurred while processing the appointment"

    def __init__(self, detail: str = None, status_code: int = None):
        if detail:
            self.detail = detail
        if status_code:
            self.status_code = status_code
        super().__init__(self.detail)


class AppointmentNotFoundError(AppointmentException):
    """Raised when an appointment is not found"""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Appointment not found"


class AppointmentAlreadyExistsError(AppointmentException):
    """Raised when trying to create an appointment that already exists"""
    status_code = status.HTTP_409_CONFLICT
    detail = "An appointment with this phone number already exists"


class AppointmentDataError(AppointmentException):
    """Raised when there's an error with appointment data"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Invalid appointment data"
