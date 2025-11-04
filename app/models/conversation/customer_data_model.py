import re
from datetime import datetime
from typing import List

from pydantic import BaseModel, field_validator, ValidationInfo

from app.models.conversation.file_data_model import FileData
from app.models.enum.customer_type import CustomerType


class CustomerDataModel(BaseModel):
    first_name: str
    phone_number: str
    customer_type: CustomerType

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        """Validate that first_name is not empty and contains only letters/spaces."""
        stripped_v = v.strip()
        if not stripped_v:
            raise ValueError('First name must not be empty.')
        if not re.match(r'^[a-zA-Z\s]+$', stripped_v):
            raise ValueError('First name must contain only letters and spaces.')
        return stripped_v

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format"""
        stripped_phone_number = v.strip()
        if not stripped_phone_number:
            raise ValueError('Phone number must not be empty.')
        return stripped_phone_number


class CallDataModel(BaseModel):
    created_time: str
    sid: str
    duration: str
    sentiment: str
    artifacts: List[FileData]
    summary: str
    transferred: bool
    abandoned: bool
    e_lead: bool

    @field_validator('created_time')
    @classmethod
    def validate_created_time(cls, v: str) -> str:
        """Validate that created_time is a valid ISO 8601 datetime string."""
        try:
            # This checks if the string can be parsed as an ISO datetime
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError('created_time must be in ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SS).')
        return v

    @field_validator('sentiment', 'duration', 'sid')
    @classmethod
    def validate_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """Validate that the field is not empty."""
        stripped_v = v.strip()
        if not stripped_v:
            raise ValueError(f'{info.field_name} must not be empty.')
        return stripped_v


class VehicleDataModel(BaseModel):
    vehicle: str
    model: str
    requirements: List[str]

    @field_validator('vehicle', 'model')
    @classmethod
    def validate_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """Validate that vehicle and model fields are not empty."""
        stripped_v = v.strip()
        if not stripped_v:
            raise ValueError(f'{info.field_name} must not be empty.')
        return stripped_v

    @field_validator('requirements')
    @classmethod
    def validate_requirements(cls, v: List[str]) -> List[str]:
        """Validate that the requirements list is not empty and its items are not empty."""
        if not v:
            raise ValueError('Requirements list must not be empty.')

        validated_list = []
        for item in v:
            stripped_item = item.strip()
            if not stripped_item:
                raise ValueError('Requirement item must not be empty.')
            validated_list.append(stripped_item)

        return validated_list
