from pydantic import BaseModel
from typing import List

from app.models.conversation.customer_data_request_model import CustomerDataRequestModel
from app.models.enum.response_status import ResponseStatus


class CustomerResponseModel(BaseModel):
    customer_id: int
    data: CustomerDataRequestModel
    status: ResponseStatus


class MetadataModel(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    per_page: int


class CustomerDataResponseModel(BaseModel):
    data: List[CustomerDataRequestModel]
    metadata: MetadataModel
    status: ResponseStatus
