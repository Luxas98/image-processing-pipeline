import os
from pubsubutils.logger import create_logger
from pubsubutils.pubsub import publisher, publish

log = create_logger()

PROJECT_ID = os.environ.get("GCP_PROJECT", "dev-lukas")
topic_name = os.environ.get('TOPIC_NAME', "image-data-ingestion")

file_publisher, file_topic_path = publisher(PROJECT_ID, topic_name)


def file_upload_callback(message_future):
    if message_future.exception(timeout=30):
        log.error(
            f'Publishing message on {topic_name} threw an Exception {message_future.exception()}.'
        )
    else:
        log.info(f'Published message on {topic_name}')
        log.debug(message_future.result())


def publish_file(user_id, data_type, folder, f, metadata=None):
    if data_type not in ['raw', 'label']:
        raise NotImplementedError

    metadata = metadata or {}

    folder = f"{user_id}/{folder}/"
    filepath = os.path.join(*[folder, data_type, f.filename])
    file_attributes = {
        'filename': f.filename,
        'filepath': filepath,
        'extension': f.filename.split('.')[-1],
        'user_id': user_id
    }

    metadata.update(file_attributes)

    # TODO: limit file size to 10MB
    log.info(f'Publishing file {f.name}')
    message_future = publish(
        file_publisher, file_topic_path, data=f.stream.read(), meta=metadata
    )
    message_future.add_done_callback(file_upload_callback)
