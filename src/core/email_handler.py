# -*- coding: utf-8 -*-
"""
SmartDocs - Email Handler

Parses emails and extracts relevant information.

Extracts metadata including:
- sender
- receivers
- subject
- body
- attachments

Supports both EML and MSG formats.
"""


import os

from src.datatypes.emails_types import EmlEmailMessage, MsgEmailMessage
from src.utilities.logger_config import logger
from src.utilities.parser_tools import is_email


def parse_email(email_as_bytes: bytes, rst: dict):
    """Parses an email from a bytes object and extracts relevant information.

    Args:
        email_as_bytes (bytes): The email file already read into bytes.
        rst (dict): The result dictionary with the current status data.

    Returns:
        dict: A dictionary containing the e-mail as object
    """
    try:
        param = rst['requestParameters']
        filename = param['originalFileName']
        mime_type = param['mimeType']
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if not is_email(filename, mime_type):
            rst['status'] = 'ioError'
            logger.error(f'File has not recognized as e-mail.')
            msg = f"""{filename} is not recognized as e-mail.
            Wrong mimeType {mime_type} or unknown extension {ext}."""
            rst['message'] = msg
            return rst

        logger.debug(f'Start processing email: {filename}')
        if ext == ".eml":
            email = EmlEmailMessage(email_as_bytes)
        elif ext == ".msg":
            email = MsgEmailMessage(email_as_bytes)
        rst['email'] = email
        rst['hasAttachments'] = (len(email.attachments) > 0)
        rst['status'] = 'ok'
        return rst

    except Exception as e:
        logger.error(f"Error parsing email from file {email_as_bytes}: {e}")
        raise
