from pydantic import BaseModel
from typing import Optional
from enum import Enum

class FileType(str, Enum):
    RECORDING = "recording"
    SYNOPSIS = "synopsis"
    TRANSCRIPT = "transcript"
    SUMMARY = "summary"

class GCPFileResponse(BaseModel):
    sid: str
    file_type: FileType
    content: bytes
    content_type: str
    filename: str

class GCPTextResponse(BaseModel):
    sid: str
    file_type: FileType
    content: str
    content_type: str
    filename: str
