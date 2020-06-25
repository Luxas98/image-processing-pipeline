import os
import logging


def create_logger():
    DEBUG = os.environ.get('DEBUG')
    log_level = logging.DEBUG if DEBUG == 'True' else logging.INFO
    log = logging.getLogger()
    log.setLevel(log_level)

    logging.basicConfig(
        level=log_level,
        format='(%(threadName)-10s) - %(asctime)s - %(name)s - %(levelname)s - %('
        'message)s',
    )

    return log
