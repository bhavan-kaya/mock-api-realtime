from pydantic import BaseModel


class AppointmentRequestModel(BaseModel):
    customer_phone_number: str
    customer_data: dict
