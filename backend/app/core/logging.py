import logging
import logging.config
from pythonjsonlogger import jsonlogger
from fastapi import Request
import uuid
import time


# ============================================================
#  FORMATTERS
# ============================================================

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Add correlation_id and other metadata to JSON logs.
    """

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        if not log_record.get("level"):
            log_record["level"] = record.levelname

        log_record["module"] = record.module
        log_record["func"] = record.funcName
        log_record["line"] = record.lineno


# ============================================================
#  LOGGING CONFIG
# ============================================================

def setup_logging():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "json": {
                "()": CustomJsonFormatter,
                "format": "%(level)s %(name)s %(message)s %(module)s %(func)s %(line)s",
            },
            "console": {
                "format": "[%(levelname)s] %(name)s: %(message)s",
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": "INFO",
            },
            "json_console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "level": "INFO",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": "logs/app.log",
                "maxBytes": 5_000_000,
                "backupCount": 5,
                "level": "INFO",
            },
        },

        "loggers": {
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "WARNING",  # reduce noise
                "propagate": False,
            },
            "app": {
                "handlers": ["json_console", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


# ============================================================
#  REQUEST LOGGING MIDDLEWARE
# ============================================================

async def logging_middleware(request: Request, call_next):
    """
    Logs each request with correlation_id, path, method, duration, status.
    """

    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    logger = logging.getLogger("app")

    start_time = time.time()

    logger.info(
        "request_start",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host,
        },
    )

    response = await call_next(request)

    duration = round((time.time() - start_time) * 1000, 2)

    logger.info(
        "request_end",
        extra={
            "correlation_id": correlation_id,
            "status_code": response.status_code,
            "duration_ms": duration,
        },
    )

    response.headers["X-Correlation-ID"] = correlation_id
    return response
