# coding: utf8
# flake8: noqa
"""
TODO: Write doc-string
"""
import json
import time
import os
from gcloudredis.storage import RedisClient
from gcloudredis.apimessages.status import METADATA_FIELD

from gcloudlogging.logger import create_logger
from gcloudlogging.errors import error_handler
from pubsubutils.pubsub import subscribe, callback_info, publisher, publish

log = create_logger()

INSTANCE_ID = os.environ.get("INSTANCE_ID", "instance-1")

redis_client = RedisClient(INSTANCE_ID, logger=log)

# Consumes messages from data processing to GCS
processing_topic_name = os.environ.get("TOPIC_NAME", "image-data-processing")
processing_subscription_name = os.environ.get(
    "SUB_NAME", f"{processing_topic_name}-sub"
)

# prediction
prediction_topic_name = os.environ.get(
    "PREDICTION_TOPIC_NAME", "image-model-prediction"
)
prediction_publisher, prediction_topic_path = publisher(prediction_topic_name)

# post-processing
postprocessing_topic_name = os.environ.get(
    "POSTPROCESSING_TOPIC_NAME", "image-prediction-post-processing"
)
postprocessing_publisher, postprocessing_topic_path = publisher(
    postprocessing_topic_name
)


def str_to_bool(string):
    if isinstance(string, bool):
        return string

    return string.lower() in ['true', 'yes']


# Filters incoming notifications and decides what to start
@error_handler
def callback(message):  # pylint: disable=too-many-statements
    data, file_metadata = callback_info(message)

    object_id = data["id"]
    object_id_parts = object_id.split("/")

    # staging-image-data-predicted -> staging-image-data
    app = "-".join(object_id_parts[0].split('-')[:-1]
                  ) if object_id_parts[0].endswith('-raw') or object_id_parts[
                      0].endswith('-predicted') else object_id_parts[0]
    user_id = object_id_parts[1]
    folder = object_id_parts[2]
    processing_step = object_id_parts[3]

    # object_id_parts[-1] is an additional ID after the file suffix
    object_uri = os.path.join(*object_id_parts[:-1])

    extra_log = {
        'app': app,
        'object_id': object_id,
        'object_uri': object_uri,
        'processing_step': processing_step,
        'user_id': user_id,
        'folder': folder
    }

    log.info('Processing callback start', extra=extra_log)
    log.debug(f'Data: {data} , filemetadata: {file_metadata}', extra=extra_log)

    # Publish notification to intiate data processing
    if "raw" == processing_step:
        """
        Raw processing step indicates file was uploaded and processing and
        prediction can start
        """
        redis_client.add_processing_key(app, user_id, folder)

        filename = object_id_parts[4]
        status = 'INGESTED'

        current_status = redis_client.get_status(app, user_id, folder, filename)
        extra_log.update({'_filename': filename, 'status': status})

        log.info(
            f"Processing {processing_step} {current_status}", extra=extra_log
        )
        if current_status.get('STATUS') != status:

            log.info(f'Updating status to {status}')
            redis_client.push_status(
                app,
                user_id,
                folder,
                filename,
                metadata=file_metadata,
                status=status,
                extra_log=extra_log
            )

            log.info(
                f'Publishing file {object_uri} for prediction on {prediction_topic_path}',
                extra=extra_log
            )

            metadata = {
                'STATUS':
                    status,
                'OBJECT_URI':
                    object_uri
            }
            current_status.update(metadata)

            predict = file_metadata.get('predict', 'false')
            if str_to_bool(predict):
                current_status[METADATA_FIELD] = json.dumps(file_metadata)
                publish(
                    prediction_publisher,
                    prediction_topic_path,
                    meta=current_status,
                    extra_log=extra_log
                )
        else:
            log.debug(
                f'Already ingested {processing_step} {current_status} {app} {user_id} {folder} {filename}'
            )

    elif 'processed' == processing_step:
        """
        Step after file were read and proccessed (for example image processing)
        """
        if 'METADATA' in object_id_parts[4]:
            log.info('Skipping metadata')
            message.ack()
            return

        filename = object_id_parts[5]
        status = "PROCESSED"
        current_status = redis_client.get_status(app, user_id, folder, filename)

        extra_log.update({'_filename': filename, 'status': status})

        log.info(
            f"Processing {processing_step} {current_status}", extra=extra_log
        )
        if current_status.get('STATUS') != status:
            log.info(
                f'Updating status to {status} for file {object_uri} {filename}',
                extra=extra_log
            )
            redis_client.push_status(
                app,
                user_id,
                folder,
                filename,
                status=status,
                extra_log=extra_log
            )

            model_params = current_status.get(METADATA_FIELD, {})
            predict = model_params.get('predict', 'false')
            if str_to_bool(predict):
                log.info(
                    f'Publishing file {object_uri} for prediction',
                    extra={
                        'status': status,
                        'processing_step': processing_step,
                        'filename': filename
                    }
                )
                metadata = {
                    'STATUS': status,
                    'OBJECT_URI': object_uri,
                    'COMBINE': 'N',
                    'INFO': "",
                }
                current_status.update(metadata)
                del current_status['LAST_UPDATED']

                current_status[METADATA_FIELD] = json.dumps(model_params)
                publish(
                    prediction_publisher,
                    prediction_topic_path,
                    meta=current_status
                )
            else:
                log.info('Not predicting, disabled')

        else:
            log.info(
                f'Already processed {processing_step} {current_status} {app} {user_id} {folder} {filename}'
            )

    elif 'predicted' == processing_step:
        """Prediction step, takes raw or processed files and triggers
        prediction-consumer """

        object_uri = os.path.join(*object_id_parts[:-2])
        filename = object_id_parts[4]
        status = 'PREDICTED'

        extra_log.update({'_filename': filename, 'status': status})

        statuses = redis_client.get_all_status(app, user_id, folder)
        log.debug(f"Statuses: {statuses}", extra=extra_log)
        log.debug(f"Looking for status for file {filename}", extra=extra_log)

        status_mappings = [s for (i, s, _) in statuses]
        try:
            current_status = [
                s for (i, s, _) in statuses if i == filename.split('.')[0]
            ][-1] if statuses else []
        except ValueError as e:
            log.error(f'Incorrect filename: {filename} {statuses}')
            message.ack()
            raise e

        log.info(
            f"Processing {processing_step} {current_status}", extra=extra_log
        )
        all_predicted = check_for_status(status, status_mappings)

        if not all_predicted:
            # Prediction folder/timestamp
            if current_status != status:
                log.info(
                    f"Updating status to {status} for file {object_uri} {filename}",
                    extra=extra_log
                )
                redis_client.push_status(
                    app,
                    user_id,
                    folder,
                    filename,
                    status=status,
                    extra_log=extra_log
                )

                statuses = redis_client.get_all_status(app, user_id, folder)
                execute_post_processing(
                    app, user_id, folder, object_uri, status, statuses,
                    extra_log
                )

        else:
            # This might happen if we receive doubled messages, either by
            # mistake, reuploading file, calling publish multiple times or
            # pubsub slow message can get deliver twice
            log.debug(f'Everything is already predicted', extra=extra_log)
            execute_post_processing(
                app, user_id, folder, object_uri, status, statuses, extra_log
            )

    elif "post-processed" == processing_step:
        """Post processing step, triggers generation of nrrd or stl from
        prediction files """

        filename = object_id_parts[4]
        status = "POST-PROCESSED"

        extra_log.update({'_filename': filename, 'status': status})

        log.info(
            f"Updating status for file {object_uri} {filename}",
            extra=extra_log
        )

        if "combined" in filename:
            identifiers = redis_client.list_identifiers(app, user_id, folder)
            log.info(
                f'Updating combined file multiple redis entries for {app} {user_id} {folder}',
                extra=extra_log
            )
            for identifier in identifiers:
                redis_client.push_status(
                    app,
                    user_id,
                    folder,
                    identifier,
                    status=status,
                    extra_log=extra_log
                )
        else:
            redis_client.push_status(
                app,
                user_id,
                folder,
                filename,
                status=status,
                extra_log=extra_log
            )

    else:
        log.error("UNKNOWN processing step !")

    log.info('Processing callback finished', extra=extra_log)
    message.ack()


def execute_post_processing(
    app, user_id, folder, object_uri, status, statuses, extra_log=None
):
    status_mappings, metadata_mappings = zip(
        *[(s, m['postprocess']) for (i, s, m) in statuses if i]
    )
    all_predicted = check_for_status(status, status_mappings)
    log.debug(
        f"all predicted ? {all_predicted}\n{status_mappings}", extra=extra_log
    )
    all_postprocess = check_for_status('true', metadata_mappings)
    log.debug(
        f"all postprocess ? {all_postprocess}\n{metadata_mappings}",
        extra=extra_log
    )

    log.debug(f'all predicted {all_predicted}', extra=extra_log)

    log.debug(f'all postprocess {all_postprocess}', extra=extra_log)

    if all_predicted:
        # All predictions done waiting for post-processing
        redis_client.remove_processing_key(
            app, user_id, folder, extra_log=extra_log
        )

    if all_predicted and all_postprocess:
        log.info(
            f"Publishing to folder {object_uri} for post-processing",
            extra=extra_log
        )
        metadata = {
            "STATUS": status,
            "OBJECT_URI": object_uri,
            "COMBINE": "Y",
            "INFO": "",
        }
        publish(
            postprocessing_publisher,
            postprocessing_topic_path,
            meta=metadata,
            extra_log=extra_log
        )


def check_for_status(check_status, statuses):
    # Check if all statuses are equal to the specified one, using lower to
    # handle true/True/TRUE
    return all([status.lower() == check_status.lower()
                for status in statuses]) and len(statuses) > 0


subscribe(
    processing_topic_name, processing_subscription_name, callback=callback
)

# The subscriber is non-blocking, so we must keep the main thread from
# exiting to allow it to process messages in the background.
while True:
    time.sleep(5)
