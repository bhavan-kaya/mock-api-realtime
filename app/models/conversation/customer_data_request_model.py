from pydantic import BaseModel

from app.models.conversation.customer_data_model import (
    CustomerDataModel,
    CallDataModel,
    VehicleDataModel
)


class CustomerDataRequestModel(BaseModel):
    customer_data: CustomerDataModel
    call_data: CallDataModel
    vehicle_data: VehicleDataModel

    class Config:
        json_schema_extra = {
            "example": {
                "customer_data": {
                    "first_name": "John",
                    "phone_number": "+1234567890",
                    "customer_type": "New Customer"
                },
                "call_data": {
                    "created_time": "2025-08-20 15:33",
                    "sid": "123456",
                    "duration": "07:23 Min",
                    "sentiment": "87%",
                    "summary": "This is a summary of the conversation",
                    "artifacts": [
                        {
                            'file_name': 'recordings.mp3',
                            'url': "/recordings.mp3"
                        }
                    ],
                    "transferred": False,
                    "abandoned": False,
                    "e_lead": True
                },
                "vehicle_data": {
                    "vehicle": "Chevy Silverado",
                    "model": "LT Crew Cab",
                    "requirements": [
                        "4WD",
                        "Towing Package",
                        "Leather Seats"
                    ]
                }
            }
        }
