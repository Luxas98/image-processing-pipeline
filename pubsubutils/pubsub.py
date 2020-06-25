from google.cloud import pubsub_v1
from google.api_core import exceptions as gexceptions
import os
from google.oauth2 import service_account
import json
from gcloudlogging.logger import create_logger

log = create_logger()

PUB_SUB_CREDENTIALS = os.environ.get('PUB_SUB_CREDENTIALS')
MAX_MESSAGES = int(os.environ.get('MAX_MESSAGES', 4))


if PUB_SUB_CREDENTIALS:
    log.info('PUB SUB CRED: %s' % PUB_SUB_CREDENTIALS)
    with open(PUB_SUB_CREDENTIALS, 'r') as f:
        info = json.load(f)

    credentials = service_account.Credentials.from_service_account_info(info)
    # Scopes are not set by default anymore and RefreshToken api requires them
    credentials = credentials.with_scopes(['email', 'https://www.googleapis.com/auth/pubsub', 'https://www.googleapis.com/auth/monitoring', 'https://www.googleapis.com/auth/cloud-platform'])
else:
    credentials = None

project_id = credentials.project_id

default_batch_settings = pubsub_v1.types.BatchSettings()

default_flow_control = pubsub_v1.types.FlowControl(max_messages=MAX_MESSAGES)


def subscribe(topic_name, subscription_name, callback, flow_control=()):
    flow_control = flow_control or default_flow_control
    subscription_client = pubsub_v1.SubscriberClient(credentials=credentials)

    subscription_path = subscription_client.subscription_path(
        project_id,
        subscription_name
    )

    topic_path = subscription_client.topic_path(
        project_id,
        topic_name
    )

    try:
        subscription_client.create_subscription(subscription_path, topic_path)
    except gexceptions.AlreadyExists as e:
        log.debug(f'Subscription already exists {subscription_path}')

    subscription_client.subscribe(
        subscription_path,
        callback=callback,
        flow_control=flow_control
    )
    log.info(f'Listening for messages on {subscription_path}')


def publisher(topic_name, batch_settings=()):
    batch_settings = batch_settings or default_batch_settings
    publisher_client = pubsub_v1.PublisherClient(credentials=credentials, batch_settings=batch_settings)
    topic_path = publisher_client.topic_path(
        project_id,
        topic_name
    )

    try:
        topic = publisher_client.get_topic(topic_path)
        if topic:
            log.info(f'Topic found {topic_path}')
        else:
            log.info(f'Topic not found {topic_path}')
    except gexceptions.AlreadyExists as e:
        log.info(f'Topic found {topic_path}')
    except gexceptions.PermissionDenied as e:
        log.error(f'Permission denied to access {topic_path} {PUB_SUB_CREDENTIALS}')

    return publisher_client, topic_path


# Publishing message Done callback
def _publish_callback(message_future, topic_path, extra_log=None):
    if message_future.exception(timeout=30):
        log.error(
            f'Publishing message on {topic_path} threw an Exception {message_future.exception()}.',
            extra=extra_log
        )
    else:
        log.debug(message_future.result(), extra=extra_log)


def publish(publisher, topic_path, data=b'', meta=None, extra_log=None):
    meta = meta or {}

    log.info(f'Publishing data on topic {topic_path} with meta {meta}', extra=extra_log)
    try:
        message_future = publisher.publish(topic_path, data=data, **meta)
    except Exception as e:
        log.error(f'Could not publish: {topic_path} {data} {meta}', extra=extra_log)
        raise e

    message_future.add_done_callback(
        lambda msg: _publish_callback(message_future, topic_path, extra_log)
    )


def callback_info(message):
    log.debug(f"Received message: {len(message.data)}")
    data = {}
    if message.attributes:
        log.debug("Attributes:")
        for key in message.attributes:
            value = message.attributes.get(key)
            log.debug(f"{key}: {value}")
            data[key] = value

    # if message.data:
    #     data.update(json.loads(message.data))  # TODO: how expensive is this? can we use attributes for everything?
    #     log.debug(f'Data {data}')
    #
    #     metadata = data.get('metadata', data.get('METADATA', {}))
    #     if isinstance(metadata, str):
    #         metadata = json.loads(metadata)
    #
    #     log.debug(f'Metadata: {metadata}')

    return data
