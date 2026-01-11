"""
统一异常处理中间件
"""

import logging
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.exceptions import ScheduleException

logger = logging.getLogger(__name__)


async def schedule_exception_handler(
    request: Request,
    exc: ScheduleException
) -> JSONResponse:
    """处理自定义业务异常"""
    logger.warning(f"Business exception: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """处理通用异常"""
    logger.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "internal_error",
            "message": "服务器内部错误",
            "data": None
        }
    )


def register_exception_handlers(app):
    """注册异常处理器"""
    from fastapi import status

    app.add_exception_handler(ScheduleException, schedule_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
