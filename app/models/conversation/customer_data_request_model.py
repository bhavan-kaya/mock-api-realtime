from pydantic import Field
from app.models.conversation.customer_data_model import (
    CoreModel,
    CustomerDataModel,
    CallDataModel,
    VehicleDataModel,
    ConversationSummaryModel,
    SentimentDataModel
)


class CustomerDataRequestModel(CoreModel):
    """
    Main request body model for ingesting all data related to a single interaction.
    """
    customer_data: CustomerDataModel = Field(
        ...,
        description="Information about the customer."
    )
    call_data: CallDataModel = Field(
        ...,
        description="Technical metadata about the call."
    )
    summary_data: ConversationSummaryModel = Field(
        ...,
        description="AI-generated summary of the conversation."
    )
    sentiment_data: SentimentDataModel = Field(
        ...,
        description="AI-generated sentiment analysis."
    )
    vehicle_data: VehicleDataModel = Field(
        ...,
        description="Vehicle customer is interested in."
    )

    # We use ConfigDict in the CoreModel, but for overriding json_schema_extra,
    # we define it directly in the model.
    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_data": {
                    "first_name": "John Doe",
                    "phone_number": "+1 (555) 123-4567",
                    "customer_type": "New Customer"
                },
                "call_data": {
                    "created_time": "2025-08-20T15:33:00Z",
                    "sid": "CA123abc456def7890123",
                    "duration": "00:07:23",
                    "artifacts": [
                        {
                            'file_name': 'recording_CA123abc.mp3',
                            'url': "https://api.twilio.com/recordings/RE..."
                        }
                    ],
                    "live_agent_transfer": False,
                    "abandoned": False,
                    "e_lead": True
                },
                "summary_data": {
                    "summary": "Customer called to inquire about pricing and availability of the new Chevy Silverado.",
                    "intent": "Vehicle Purchase Inquiry",
                    "resolution": "Provided pricing for LT Crew Cab and scheduled a dealership visit.",
                    "escalation": "Finance Follow-up",
                    "next_steps": "Customer will visit on Saturday at 2 PM for a test drive.",
                    "flags": ["High Intent"],
                    "tags": ["Truck", "Silverado", "New Lead"]
                },
                "sentiment_data": {
                    "score": 87.5,
                    "tone_summary": "Positive and Inquisitive",
                    "ai_interpretation": "Caller sounds engaged and serious about making a purchase. Showed positive sentiment towards pricing.",
                    "emotion_breakdown": [
                        {"emotion": "interest", "score": 0.92},
                        {"emotion": "satisfaction", "score": 0.75}
                    ],
                    "key_phrases": [
                        "positive tone",
                        "follow-up pending",
                        "finance inquiry"
                    ]
                },
                "vehicle_data": {
                    "vehicle": "Chevrolet",
                    "model": "Silverado 1500 LT Crew Cab",
                    "requirements": [
                        "4WD",
                        "Towing Package",
                        "Leather Seats"
                    ]
                }
            }
        }
    }
