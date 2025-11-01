# -*- coding: utf-8 -*-
"""
SmartDocs - Main Service Module

FastAPI service for document upload and processing functionality.

"""
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.file_handling import uploaders
from src.api.operations import operators

load_dotenv(verbose=True)


openapi_tags = [
    {
        "name": "ops",
        "description": "Operational/monitoring endpoints."
    },
    {
        "name": "upload",
        "description": "Endpoints to post unstructured data files.",
    },
]

app = FastAPI(
    title="SmartDocs API Service",
    description="Backend for uploading and handling unstructured documents.",
    version="0.0.9",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(operators.router)
app.include_router(uploaders.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=int(os.getenv("PORT", "4000")))
