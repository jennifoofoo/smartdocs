# -*- coding: utf-8 -*-
"""
SmartDocs - API Operators

Endpoints for health and monitoring the REST API service.

"""
import os

from fastapi import APIRouter

from src.utilities.app_config import UPLOAD_FOLDER
from src.utilities.logger_config import logger

router = APIRouter(
    prefix="/api",
    tags=["ops"]
)


@router.get("/health")
async def health():
    logger.debug('Call of operations API for health status')
    return {"isHealthy": True}


@router.get("/ready")
async def ready():
    logger.debug('Call of operations API for ready status')
    if os.path.exists(UPLOAD_FOLDER):
        return {"isReady": True}
    else:
        msg = {"message": "Upload folder missing", "isReady": False}
        return msg
