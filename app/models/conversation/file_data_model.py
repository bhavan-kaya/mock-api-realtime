from pydantic import BaseModel


class FileData(BaseModel):
    file_name: str
    url: str
