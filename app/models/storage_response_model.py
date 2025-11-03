from pydantic import BaseModel


class FileData(BaseModel):
    file_name: str
    url: str
    last_modified: str


class StorageResponse(BaseModel):
    sid: str
    data: list[FileData]
