from pydantic import BaseModel
from typing import List, Dict, Any

from app.models.enum.response_status import ResponseStatus


class CustomerResponseModel(BaseModel):
    customer_id: int
    status: ResponseStatus


class MetadataModel(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    per_page: int


class CustomerDataResponseModel(BaseModel):
    data: List[Dict[str, Any]]
    metadata: MetadataModel
    status: ResponseStatus
