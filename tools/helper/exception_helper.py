# encoding: utf-8

import setting
from loguru import logger


def require(condition, error, remote=False):
    if not condition:
        if remote:
            logger.log(setting.LOG_REMOTE_LEVEL_NAME_ERROR, error)
        raise Exception(error)
