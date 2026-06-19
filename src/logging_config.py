import logging
from pprint import pformat
import warnings
from logging.config import dictConfig


class PrettyConsoleFormatter(logging.Formatter):
    """Pretty-print structured log arguments without changing log call sites."""

    def format(self, record: logging.LogRecord) -> str:
        original_args = record.args

        if original_args:
            record.args = self._format_args(record.msg, original_args)

        try:
            return super().format(record)
        finally:
            record.args = original_args

    def formatMessage(self, record: logging.LogRecord) -> str:
        message = super().formatMessage(record)

        if "\n" not in message:
            return message

        lines = message.splitlines()
        indent = " " * 34

        return "\n".join(
            [lines[0], *[f"{indent}{line}" for line in lines[1:]]]
        )

    def _format_args(self, message, args):
        if isinstance(args, dict):
            if "%(" not in str(message):
                return (self._pretty_value(args),)

            return {
                key: self._pretty_value(value)
                for key, value in args.items()
            }

        if isinstance(args, tuple):
            return tuple(self._pretty_value(value) for value in args)

        return self._pretty_value(args)

    def _pretty_value(self, value):
        if isinstance(value, (dict, list, tuple, set)):
            return "\n" + pformat(value, width=100, compact=False, sort_dicts=False)

        return value


APP_LOGGERS = [
    "agent",
    "agent.nodes",
    "agent.graph",
    "agent.runtime",
    "agent.streaming",
    "chat.state_builder",
    "chat_ops",
    "chat_stream_service",
    "fts_search",
    "hybrid_merge",
    "job_ops",
    "query_parser",
    "retrieval_pipeline",
    "reranker",
    "resume_embedding",
    "resume_ops",
    "resume_parser",
    "resume_reader",
    "resume_upload_service",
    "summarizer",
    "warmup",
]


NOISY_LOGGERS = [
    "httpx",
    "httpcore",
    "openai",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "uvicorn.access",
]


def configure_runtime_logs() -> None:
    """Keep framework noise low while showing application logs."""

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "()": "src.logging_config.PrettyConsoleFormatter",
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    })

    warnings.filterwarnings(
        "ignore",
        message="Pydantic serializer warnings:*",
        category=UserWarning,
        module="pydantic.main",
    )

    for logger_name in APP_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
