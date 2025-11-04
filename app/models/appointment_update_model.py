from typing import Optional

from pydantic import BaseModel


class AppointmentUpdateModel(BaseModel):
    """
    Model for updating appointment data.
    """
    customer_name: str
    customer_phone_number: str
    appointment_date: str
    appointment_time: str
    vehicle_details: Optional[str] = None
    service: Optional[str] = None
    remarks: Optional[str] = None

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
