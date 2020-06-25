from six.moves import http_client

from flaskapp.logger import logger


def swagger_2_unexpected_error(e):
    """Handle exceptions by returning swagger-compliant json."""
    logger.exception('An error occured while processing the request.')
    response = jsonify({
        'code': http_client.INTERNAL_SERVER_ERROR,
        'message': 'Exception: {}'.format(e)
    })
    response.status_code = http_client.INTERNAL_SERVER_ERROR
    return response
