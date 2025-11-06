from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SaveContactRequest(BaseModel):
    """Request model for saving contact information"""
    customer_name: str = Field(..., description="Name of the customer", min_length=1)
    contact_number: str = Field(..., description="Phone number of the customer")
    date: Optional[datetime] = Field(None, description="Date of contact (defaults to current time)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_name": "John Smith",
                "contact_number": "+947036252123",
                "date": "2025-10-28T10:30:00"
            }
        }


class GetContactRequest(BaseModel):
    """Request model for getting contact information"""
    contact_number: str = Field(..., description="Phone number to search", )
    
    class Config:
        json_schema_extra = {
            "example": {
                "contact_number": "+947036252123"
            }
        }


class DeleteContactRequest(BaseModel):
    """Request model for deleting contact information"""
    contact_number: str = Field(..., description="Phone number to delete")
    
    class Config:
        json_schema_extra = {
            "example": {
                "contact_number": "+947036252123"
            }
        }


class ContactResponse(BaseModel):
    """Response model for contact information"""
    id: str = Field(..., description="Unique identifier")
    customer_name: str = Field(..., description="Name of the customer")
    contact_number: str = Field(..., description="Phone number of the customer")
    date: datetime = Field(..., description="Date of contact")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "customer_name": "John Smith",
                "contact_number": "+947036252123",
                "date": "2025-10-28T10:30:00"
            }
        }


class ContactListResponse(BaseModel):
    """Response model for list of contacts"""
    contacts: list[ContactResponse] = Field(..., description="List of contact records")
    total: int = Field(..., description="Total number of contacts")
    
    class Config:
        json_schema_extra = {
            "example": {
                "contacts": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "customer_name": "John Smith",
                        "contact_number": "+947036252123",
                        "date": "2025-10-28T10:30:00"
                    },
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "customer_name": "Jane Doe",
                        "contact_number": "+94764184251",
                        "date": "2025-10-28T14:15:00"
                    }
                ],
                "total": 2
            }
        }


class StatusResponse(BaseModel):
    """Generic response model for operations"""
    status: str = Field(..., description="Status of the operation (success/error)")
    message: str = Field(..., description="Descriptive message")
    id: Optional[str] = Field(None, description="Record ID if applicable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Contact saved successfully",
                "id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }