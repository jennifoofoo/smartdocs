# -*- coding: utf-8 -*-
"""
SmartDocs - Logger Configuration

Centralized logging configuration for the SmartDocs application.

Provides consistent logging format and level management across all modules.

"""
import logging
import os

from dotenv import load_dotenv

load_dotenv(verbose=True)

logger_name = os.environ.get('LOGGER_NAME', 'mtf-tools-logger')
logger = logging.getLogger(logger_name)
format = '%(asctime)s [%(levelname)-10s] '
format += '[%(filename)-20s] [%(funcName)-25s] %(message)s'

log_formatter = logging.Formatter(format)

logger.setLevel(logging.DEBUG)

console_logger = logging.StreamHandler()
console_logger.setFormatter(log_formatter)
console_logger.setLevel(logging.DEBUG)

logger.addHandler(console_logger)

LOG_LEVEL = os.environ.get('LOG_LEVEL', logging.DEBUG)
logger.setLevel(LOG_LEVEL)
