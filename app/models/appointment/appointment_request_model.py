from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AppointmentRequestModel(BaseModel):
    """
    Model for appointment request data validation.
    """
    customer_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Customer's full name"
    )
    customer_phone_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
        pattern=r'^\+?[0-9]{10,15}$',
        description="Customer's phone number"
    )
    appointment_date: date
    appointment_time: time
    vehicle_details: Optional[str] = Field(
        None,
        max_length=255,
        description="Vehicle make, model, and year"
    )
    service: Optional[str] = Field(
        None,
        max_length=255,
        description="Requested service type"
    )
    remarks: Optional[str] = None

    @field_validator('appointment_date')
    @classmethod
    def validate_appointment_date_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Appointment date cannot be in the past")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "customer_name": "John Doe",
                "customer_phone_number": "+1234567890",
                "appointment_date": "2025-11-15",
                "appointment_time": "14:30",
                "vehicle_details": "Toyota Camry 2020, Black",
                "service": "Full Service",
                "remarks": "Please check the air conditioning"
            }
        }
