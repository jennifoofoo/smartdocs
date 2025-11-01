# -*- coding: utf-8 -*-
"""
SmartDocs - Flow Manager

Controls the pipeline for pre-processing files with structured and unstructured data.

Manages:
- Pipeline execution
- Result dictionary initialization
- Processing orchestration
- Session management

"""

import json
import os
import time
import uuid

from werkzeug.utils import secure_filename

from src.core.email_handler import parse_email
from src.core.file_handler import parse_file
from src.utilities.app_config import UPLOAD_FOLDER
from src.utilities.logger_config import logger
from src.utilities.parser_tools import is_email


def execute_pipeline(file,
                     base_url: str = '/'):
    rst = init_result_dict(base_url)

    mime_type = file.content_type
    filename = file.filename
    secured_filename = secure_filename(filename)
    rst['requestParameters'] = {"mimeType": mime_type,
                                "originalFileName": filename,
                                "securedFileName": secured_filename}

    file_as_bytes = file.file.read()
    if is_email(filename, mime_type):
        rst = parse_email(file_as_bytes, rst)
    else:
        rst = parse_file(file_as_bytes, rst)
        
    # rst = save_result(rst, base_url)

    rst = finish_result_dict(rst)

    return rst


def init_result_dict(base_url: str = '/'):
    """
    Create the result structure and initialize some timestamps

    Returns:
        dict: Initial structure for the analysis results.
    """
    start_ts = time.time()
    ts_formatted = time.strftime('%Y%m%d-%H%M%S', time.localtime(start_ts))
    session_id = str(uuid.uuid1()).split('-')[0]
    session_id = f'{ts_formatted}-{session_id}'

    rst = {'session_id': session_id}
    rst['startTime'] = start_ts
    rst['processingTimes'] = {'totalAnalysisTime': 0.0}
    rst['version'] = '0.9.0'

    output_path = os.path.join(UPLOAD_FOLDER, rst["session_id"])
    rst['outputPath'] = output_path
    os.makedirs(output_path, exist_ok=True)
    link_path = f'{base_url}static/results/{rst["session_id"]}'
    rst['linkPath'] = link_path
    return rst


def save_result(rst: dict, base_url: str = '/'):
    if 'email' in rst and rst['email'] is not None:
        logger.debug(f'Save email and attachments')
        # rst = save_email(rst, base_url)
        rst['email'] = rst['email'].subject
    
    return rst

def finish_result_dict(rst):
    end_ts = time.time()
    start_ts = rst['startTime']

    ts_formatted = time.strftime('%Y%m%d-%H%M%S', time.localtime(start_ts))
    rst['startTime'] = ts_formatted
    ts_formatted = time.strftime('%Y%m%d-%H%M%S', time.localtime(end_ts))
    rst['endTime'] = ts_formatted

    rst['processingTimes']['totalAnalysisTime'] = (end_ts - start_ts) * 1000

    rst['success'] = False
    if rst['status'] == "ok":
        msg = 'status ok, but nothing implemented yet'
    elif rst['status'] == 'ioError':
        msg = rst['message']
        logger.info(msg)
    else:
        rst['status'] = 'failed'
        msg = 'detection not called'

    rst['message'] = msg

    # save json data
    output_path = os.path.join(UPLOAD_FOLDER, rst["session_id"], 'result.json')
    with open(output_path, 'w') as f:
        json.dump(rst, f, indent=2)

    return rst
