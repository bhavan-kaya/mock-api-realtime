from pydantic import BaseModel

from app.models.appointment.appointment_request_model import AppointmentRequestModel
from app.models.enum.response_status import ResponseStatus


class CreateAppointmentResponse(BaseModel):
    appointment_id: str
    data: AppointmentRequestModel
    status: ResponseStatus


class GetAppointmentByPhoneNumberResponse(BaseModel):
    appointment_id: str
    data: AppointmentRequestModel
    status: ResponseStatus


class UpdateAppointmentResponse(BaseModel):
    updated: bool
    data: AppointmentRequestModel
    status: ResponseStatus


class DeleteAppointmentResponse(BaseModel):
    phone_number: str
    is_appointment_deleted: bool
    status: ResponseStatus
