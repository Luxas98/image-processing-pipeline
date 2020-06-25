import os
import io
from flask import request, jsonify, send_file
from flask.views import MethodView

from flaskapp.extensions.api import api
from apimessages.status import ResponseGenerator
from gcloudstorage.storage import (  # pylint: disable=E0611
    get_file, list_folders, list_files, upload_file, delete_folder
)
from gcloudredis.storage import RedisClient  # pylint: disable=E0611

from .blueprint import files
from .utils import get_metadata
from ..pubsub.files_publisher import publish_file

from pubsubutils.logger import create_logger

log = create_logger()

# TODO: instance id should be get from env, or kubectl pod id?
SERVICE_NAME = 'files'
INSTANCE_ID = 'instance-1'

redis_client = RedisClient(INSTANCE_ID)


class FilesAPI(MethodView):
    def get(self, folder):
        user_id = request.args.get('user')
        app_name = request.args.get('app')
        url = request.args.get('path')

        responses = ResponseGenerator(
            app_name, user_id, "", SERVICE_NAME, INSTANCE_ID
        )

        if not user_id:
            return jsonify(responses.missing_parameter('user'))

        if not app_name:
            return jsonify(responses.missing_parameter('app'))

        if url:
            file = io.BytesIO(get_file(f'{user_id}/{folder}/{url}', app_name))
            return send_file(file, mimetype='application/octet-stream')

        if folder is None:
            return jsonify(list_folders(user_id, app_name))
        else:
            return jsonify(list_files(user_id, folder, app_name))

    def post(self, folder):
        user_id = request.args.get('user')
        app_name = request.args.get('app')
        reupload = request.args.get('reupload', False)
        queue = request.args.get('queue', False)
        metadata = get_metadata(request, app_name)

        log.info(f'Received params: {user_id} {app_name} {reupload} {queue}')

        responses = ResponseGenerator(
            app_name, user_id, "", SERVICE_NAME, INSTANCE_ID
        )

        if not user_id:
            return jsonify(responses.missing_parameter('user'))

        if not app_name:
            return jsonify(responses.missing_parameter('app'))

        log.info(f'Received files {request.files}')
        data_type = request.args.get('type', 'raw')
        filenames = []

        try:
            for name, f in request.files.items():
                current_status = redis_client.get_status(
                    app_name, user_id, folder, f.name
                )
                filenames.append(name)
                # if there are existing status for files it means
                # something is processing them
                if current_status and not reupload:
                    return jsonify(current_status)

                if queue:
                    # option A: used by Dataflow arch.
                    # log.info('Publishing file %s' % name)
                    publish_file(user_id, data_type, folder, f)
                else:
                    log.info('Uploading file %s' % name)
                    # TODO: create file uploader in Dataflow or
                    # upload service / cloud function
                    # option B: used by Microservices arch.
                    filepath = os.path.join(
                        *[f"{user_id}/{folder}/", data_type, f.filename]
                    )
                    upload_file(
                        f.stream.read(), filepath, app_name, metadata
                    )
        except NotImplementedError as e:  # noqa
            return jsonify(
                responses.error(
                    'File type not supported please specify type one of [raw, label]'
                )
            )
        except Exception as e:
            return jsonify(responses.error(f'{e}'))

        current_statuses = [
            redis_client.get_status(app_name, user_id, folder, name)
            for name in filenames
        ]
        return jsonify(responses.prediction_status_response(current_statuses))

    def delete(self, folder):
        app_name = request.args.get('app')
        user_id = request.args.get('user')

        responses = ResponseGenerator(
            app_name, user_id, "", SERVICE_NAME, INSTANCE_ID
        )

        if not user_id:
            return jsonify(responses.missing_parameter('user'))

        if not app_name:
            return jsonify(responses.missing_parameter('app'))

        return jsonify(delete_folder(user_id, app_name, folder))


files_view = FilesAPI.as_view('files')

api.add_url_rule(
    files.url_prefix,
    defaults={
        'folder': None,
    },
    view_func=files_view,
    methods=['GET']
)
api.add_url_rule(
    files.url_prefix + '/<string:folder>',
    view_func=files_view,
    methods=['GET', 'POST', 'DELETE']
)
