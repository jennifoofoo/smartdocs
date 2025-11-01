# -*- coding: utf-8 -*-
"""
SmartDocs - Parser Tools

Collection of functions to help with parsing of files.

Utilities for:
- File type detection
- Email format validation
- MIME type handling

"""

import os

from src.utilities.logger_config import logger

VALID_MIMETYPES = {"email": ['message/rfc822', 'application/octet-stream'],
                   "text": ['text/plain', 'text/csv', 'text/richtext',
                            'text/markdown', 'text/xml']}
VALID_EXTENSIONS = {"email": [".eml", ".msg"],
                    "text": [".docx", ".txt", ".odt", ".pdf"],
                    "image": [".png", ".jpg", ".jpeg"],
                    "unstructured": ['.abw', '.bmp', '.csv', '.cwk', '.dbf',
                                     '.dif', '.diff', '.doc', '.docm', '.docx',
                                     '.dot', '.dotm', '.eml', '.epub', '.et',
                                     '.eth', '.fods', '.heic', '.htm', '.html',
                                     '.hwp', '.jpeg', '.jpg', '.md', '.mcw',
                                     '.msg', '.mw', '.odt', '.org', '.p7s',
                                     '.pbd', '.pdf', '.png', '.pot', '.ppt',
                                     '.pptm', '.pptx', '.prn', '.rst', '.rtf',
                                     '.sdp', '.sxg', '.tiff', '.txt', '.tsv',
                                     '.xls', '.xlsx', '.xml', '.zabw']}


UNSUPPORTED_MIMETYPES = ['application/zip',
                         'application/pkcs7-signature',
                         'application/octet-stream']


def is_valid_mimetype(mime_type: str, type_list_key: str = 'text') -> bool:

    discrete_type = mime_type.split('/')[0]
    sub_type = mime_type.split('/')[1]

    is_valid = (mime_type in VALID_MIMETYPES[type_list_key])
    if not is_valid:
        logger.warning(
            f'Mimetype {discrete_type} with subtype {sub_type} is not in validation list.')
    is_text_type = (discrete_type == 'text')

    return (is_valid or (is_text_type and type_list_key == 'text'))


def has_valid_extension(filename: str, type_list_key: str = 'unstructured') -> bool:
    if filename is None or len(filename) == 0:
        return False

    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    return (ext in VALID_EXTENSIONS[type_list_key])


def is_image_mimetype(mime_type: str) -> bool:
    discrete_type = mime_type.split('/')[0]
    return (discrete_type.lower() == 'image')


def is_text_mimetype(mime_type: str) -> bool:
    discrete_type = mime_type.split('/')[0]
    return (discrete_type.lower() == 'text')


def is_unsupported_mimetype(mime_type: str) -> bool:
    return mime_type in UNSUPPORTED_MIMETYPES


def is_email(filename: str, mimetype: str) -> bool:
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    is_email = is_valid_mimetype(mimetype,
                                 'email') or (ext in VALID_EXTENSIONS['email'])

    return is_email
