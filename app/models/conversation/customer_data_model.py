import re
from datetime import datetime, time
from typing import List, Dict, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.models.conversation.file_data_model import FileData
from app.models.enum.customer_type import CustomerType


class CoreModel(BaseModel):
    """Base model with standard configuration."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='ignore'
    )

class CustomerDataModel(CoreModel):
    first_name: str = Field(
        ..., 
        min_length=1, 
        description="Customer's first name."
    )
    phone_number: str = Field(
        ..., 
        min_length=7, 
        max_length=20, 
        description="Primary contact number."
    )
    customer_type: CustomerType = Field(
        ..., 
        description="Classification of the customer."
    )

    @field_validator('first_name')
    @classmethod
    def validate_name_characters(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z\s\-.]+$", v):
            raise ValueError("First name contains invalid characters.")
        return v

class CallDataModel(CoreModel):
    created_time: datetime = Field(
        ..., 
        description="Timestamp when the call record was created."
    )
    sid: str = Field(
        ..., 
        min_length=5, 
        max_length=50, 
        description="Unique session/call ID."
    )
    duration: time = Field(
        ..., 
        description="Total duration of the call."
    )
    artifacts: List[FileData] = Field(
        default_factory=list, 
        description="Associated files like recordings or transcripts."
    )
    live_agent_transfer: bool = Field(
        False, 
        description="Whether the call was transferred to a human agent."
    )
    abandoned: bool = Field(
        False, 
        description="Whether the caller hung up before resolution."
    )
    e_lead: bool = Field(False, description="Whether this call qualified as an electronic lead.")

    @field_validator('sid')
    @classmethod
    def validate_sid_format(cls, v: str) -> str:
        if not re.match(r'^[A-Za-z0-9_\-]+$', v):
            raise ValueError("SID contains invalid characters.")
        return v


class VehicleDataModel(CoreModel):
    vehicle: str = Field(
        ..., 
        min_length=1, 
        description="Vehicle make (e.g., Toyota)."
    )
    model: str = Field(
        ..., 
        min_length=1, 
        description="Vehicle model (e.g., Corolla)."
    )
    requirements: List[str] = Field(
        ..., 
        min_length=1, 
        description="Specific customer vehicle requirements."
    )

    @field_validator('requirements')
    @classmethod
    def validate_requirements_items(cls, v: List[str]) -> List[str]:
        # Remove empty strings from the list
        cleaned = [item.strip() for item in v if item.strip()]
        if not cleaned:
             raise ValueError('Requirements list must contain at least one valid item.')
        return cleaned

class ConversationSummaryModel(CoreModel):
    summary: str = Field(
        ..., 
        min_length=10, 
        description="High-level summary of the conversation."
    )
    intent: str = Field(
        ..., 
        min_length=1, 
        description="Detected primary intent of the caller."
    )
    resolution: str = Field(
        ..., 
        min_length=1, 
        description="How the call was resolved."
    )
    escalation: str = Field(
        default="",
        min_length=0,
        description="Details if the call was escalated."
    )
    next_steps: str = Field(
        ..., 
        min_length=1, 
        description="Action items following the call."
    )
    flags: List[str] = Field(
        default_factory=list, 
        description="Urgent markers (e.g., 'angry customer')."
    )
    tags: List[str] = Field(
        default_factory=list, 
        description="Categorization tags for reporting."
    )
    average_handle_time: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Metrics on handle time components."
    )

class SentimentDataModel(CoreModel):
    score: float = Field(
        ..., 
        ge=0, 
        le=100, 
        description="AI-calculated sentiment score (0-100)."
    )
    tone_summary: str = Field(
        ..., 
        min_length=1, 
        description="Brief description of the caller's tone."
    )
    ai_interpretation: str = Field(
        ..., 
        min_length=10, 
        description="AI's detailed analysis of the sentiment."
    )
    emotion_breakdown: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Granular scoring of specific emotions."
    )
    key_phrases: List[str] = Field(
        default_factory=list, 
        description="Notable phrases used by the customer indicating sentiment."
    )
    