# -*- coding: utf-8 -*-
"""
SmartDocs - Application Configuration

Application configuration and environment variables.

Centralizes settings for:
- File paths and directories
- Upload configurations
- Environment variables

"""
import os

from src.utilities.logger_config import logger

cur_dir = os.path.dirname(os.path.realpath(__file__))
SRC_DIR = os.path.abspath(os.path.join(cur_dir, '..'))
UPLOAD_FOLDER = os.path.abspath(
    os.path.join(SRC_DIR, '..', "static", "results"))

TEST_DATA_DIR = os.path.abspath(
    os.path.join(SRC_DIR, '..', 'test_data'))
TEST_RESULTS_DIR = os.path.abspath(
    os.path.join(SRC_DIR, '..', 'test_results'))

MANDATORY_ENV = {'LOG_LEVEL': 'DEBUG',
                 "LLM_MODEL": 'granite3.3:latest',
                 "TEXT_EMBEDDING_MODEL": 'nomic-embed-text'}

# Verify mandatory ENV exists
env_not_found = False
for env_name in MANDATORY_ENV.keys():
    if os.getenv(env_name) is None:
        logger.error(
            f'Environment variable {env_name} not set. Should be something like {MANDATORY_ENV[env_name]}')
        env_not_found = True

if env_not_found:
    logger.error('Mandatory environment not set! See errors above!')
    exit()

for dir in [UPLOAD_FOLDER, TEST_DATA_DIR, TEST_RESULTS_DIR]:
    os.makedirs(dir, exist_ok=True)

logger.info('Application configured')
