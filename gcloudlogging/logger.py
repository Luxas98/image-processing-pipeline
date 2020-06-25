import os
import logging
from logging import config

LOG_CONFIG = {
    "version": 1,
    "formatters":
        {
            "json":
                {
                    "()":
                        "google_cloud_logger.GoogleCloudFormatter",
                    "application_info":
                        {
                            "type": "python-application",
                            "application_name": "GCloud Logger"
                        },
                    "format":
                        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
                }
        },
    "handlers":
        {
            "json": {
                "class": "logging.StreamHandler",
                "formatter": "json"
            }
        },
    "loggers":
        {
            # GCP threads log into root logger
            "root": {
                "level": "DEBUG" if os.environ.get('DEBUG') else "INFO",
                "handlers": ["json"]
            },
            "werkzeug": {
                    "level": "WARN",  # Disable werkzeug hardcoded logger
                    "handlers": ["json"]
            },
            "gcp-logger": {
                "level": "DEBUG" if os.environ.get('DEBUG') else "INFO",
                "handlers": ["json"]
            }
        }  # noqa: E122 # TODO: Some conflict between yapf and flake8 (not in a mood to investigate)
}


def create_logger(logger_name=None):
    logger_name = logger_name or "gcp-logger"
    if 'gunicorn.error' in logging.root.manager.loggerDict:
        log = logging.getLogger()
    else:
        config.dictConfig(LOG_CONFIG)
        log = logging.getLogger(logger_name)
    return log
