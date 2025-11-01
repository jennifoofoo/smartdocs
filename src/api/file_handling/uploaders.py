# -*- coding: utf-8 -*-
"""
SmartDocs - File Uploaders

Endpoints for uploading files and starting the parsing of unstructured data.

"""

from fastapi import APIRouter, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse

from src.core.flow_manager import execute_pipeline
from src.utilities.logger_config import logger

router = APIRouter(
    prefix="/api",
    tags=["upload"]
)


@router.post("/email", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(file: UploadFile,
                      request: Request) -> Response:
    """
    Endpoint to upload the email as .eml or .msg file.

    The email will be split into the meta information like:
    - sender,
    - receivers,
    - subject, and 
    - body

    If the email has attachments they will be detached and stored in a folder 
    with a secure filename created from sender and subject

    :param file: The uploaded file
    :param request: The API request given by FastAPI
    """
    logger.debug(f'File received: {file.filename}')

    rst = execute_pipeline(file, request.base_url)

    if rst['status'] == 'ioError':
        return JSONResponse(
            content=rst, status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )

    return JSONResponse(
        content=rst, status_code=status.HTTP_202_ACCEPTED
    )


@router.post("/unstructured_data", status_code=status.HTTP_202_ACCEPTED)
async def upload_unstructured(file: UploadFile,
                              request: Request) -> Response:
    """
    Endpoint to upload unstructured data (e.g. pdf, txt).

    :param file: The uploaded file
    """
    # TODO: Add validation for mimetype and filesize
    # TODO: Add parsing of files
    logger.debug(f'File received: {file.filename}')
    pass
