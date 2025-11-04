import random
from datetime import datetime
from itertools import islice
from typing import List, Optional
from urllib.parse import unquote
import uvicorn

from fastapi import FastAPI, Query
from langchain_community.document_loaders.csv_loader import CSVLoader


from app.api import api_router
from config import HOST, PORT


app = FastAPI()


app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
