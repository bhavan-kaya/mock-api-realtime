from pydantic import BaseModel
from typing import Optional


class AppointmentRequestModel(BaseModel):
    customer_name: str
    customer_phone_number: str
    appointment_date: str
    appointment_time: str
    vehicle_details: Optional[str]
    service: Optional[str]
    remarks: Optional[str]
