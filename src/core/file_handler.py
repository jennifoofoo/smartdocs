# -*- coding: utf-8 -*-
"""
SmartDocs - File Handler

Parses documents and extracts relevant information.

Supports multiple formats including PDF, DOCX, XLSX, PPTX and extracts metadata like 
    - sender,
    - receivers,
    - subject, and 
    - body
    
and returns it in a result dictionary.
"""

import os

from src.core.email_handler import parse_email
from src.utilities.logger_config import logger
from src.utilities.parser_tools import is_email


def parse_file(file_as_bytes: bytes, rst: dict):
    """
    Parses a file from a bytes object and extracts relevant information.

    Args:
        file_as_bytes (bytes): The file already read into bytes.
        rst (dict): The result dictionary with the current status data.

    Returns:
        dict: A dictionary containing the file as object
    """
    try:
        param = rst['requestParameters']
        filename = param['originalFileName']
        mime_type = param['mimeType']
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if is_email(filename, mime_type):
            rst = parse_email(file_as_bytes, rst)
            return rst

        logger.debug(f'Start processing file: {filename}')

        rst['status'] = 'not_ok'
        return rst

    except Exception as e:
        logger.error(f"Error parsing email from file {file_as_bytes}: {e}")
        raise
