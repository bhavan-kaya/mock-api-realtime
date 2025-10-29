from pydantic import BaseModel


class AppointmentUpdateModel(BaseModel):
    customer_data: dict