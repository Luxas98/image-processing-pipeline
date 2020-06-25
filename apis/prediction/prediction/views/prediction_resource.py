from flask import request, jsonify
from flask.views import MethodView
from flaskapp.extensions.api import api
from flaskapp.prediction.views.blueprint import prediction
from gcloudredis.storage import RedisClient
from gcloudstorage.storage import list_files
from pubsubutils.logger import create_logger
from apimessages.status import ResponseGenerator

log = create_logger()

# TODO: instance id should be get from env, or kubectl pod id?
SERVICE_NAME = 'prediction-api'
INSTANCE_ID = 'instance-1'

redis_client = RedisClient(INSTANCE_ID, logger=log)


class PredictAPI(MethodView):
    def get(self, folder):
        user_id = request.args.get('user')
        app = request.args.get('app')

        statuses = redis_client.get_all_status(app, user_id, folder)
        tf_status_mappings = [s for (_, s, _) in statuses]

        responses = ResponseGenerator(
            app, user_id, folder, SERVICE_NAME, INSTANCE_ID
        )

        if not user_id:
            return jsonify(responses.missing_parameter('user')), 422

        if not tf_status_mappings:
            return jsonify(
                responses.response(
                    'ERROR',
                    'No files for prediction found, please upload files first',
                    f'/api/v1/files/{folder}'
                )
            ), 422

        if tf_status_mappings and all(
            [s == 'POST-PROCESSED' for s in tf_status_mappings]
        ):
            files = list_files(user_id, f'{folder}/post-processed', app)
            files_parts = [file.split('/') for file in files]
            result_urls = ['/'.join(parts[-2:]) for parts in files_parts]
            return jsonify(
                responses.response(
                    'POST-PROCESSED', 'Prediction finished.', result_urls
                )
            )

        if tf_status_mappings and any(
            [s == 'POST-PROCESSED' for s in tf_status_mappings]
        ):
            return jsonify(
                responses.response(
                    statuses, 'Prediction post processing in progress.'
                )
            )

        if tf_status_mappings and any(
            [s == 'INGESTED' for s in tf_status_mappings]
        ):
            return jsonify(
                responses.response(statuses, 'Pre processing in progress.')
            )

        return jsonify(
            responses.response(
                statuses, 'Prediction schedule, please check again in a while'
            )
        )


predict_view = PredictAPI.as_view('prediction')

api.add_url_rule(
    prediction.url_prefix + '/<string:folder>',
    view_func=predict_view,
    methods=['GET']
)
