from pydantic import BaseModel

from app.models.response_status import ResponseStatus


class FileData(BaseModel):
    file_name: str
    url: str
    last_modified: str


class StorageResponse(BaseModel):
    sid: str
    data: list[FileData]
    status: ResponseStatus
