from gcloudlogging.logger import create_logger

log = create_logger()


def error_handler(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e_origin:
            # TODO: possibly to use `inspect.getfullargspec` to access args by name, but that can harm performance for many messages
            try:
                message = args[0]
                extra_log_info = {
                    'attributes': message.properties(),
                    'data': message.value()
                }

                log.exception(f'Exception during processing: {e_origin}', extra=extra_log_info)
            except Exception as e_log:
                log.exception(f'Exception during processing: {e_origin}')
                log.exception(f'Exception during logging: {e_log}')

            message.nack()

    return func_wrapper
