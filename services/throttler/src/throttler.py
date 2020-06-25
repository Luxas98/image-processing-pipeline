import os
import time
from google.cloud import pubsub_v1
from pubsubutils.pubsub import subscribe, publisher, publish, credentials
from gcloudlogging.logger import create_logger
from gcloudlogging.errors import error_handler
from gcloudredis.storage import RedisClient
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3 import query
from google.cloud.monitoring_v3 import _dataframe
import json

SUBSCRIPTION_MESSAGE_LIMIT = int(
    os.environ.get("SUBSCRIPTION_MESSAGE_LIMIT", 100)
)
SUBSCRIPTION_TIME_INTERVAL = int(
    os.environ.get("SUBSCRIPTION_TIME_INTERVAL", 2)
)
MONITOR_TOPIC = os.environ.get("MONITOR_TOPIC", "image-model-prediction")

client = monitoring_v3.MetricServiceClient()

consumer = pubsub_v1.SubscriberClient()
consumer_topic_name = os.environ.get("TOPIC_NAME", "image-data-ingestion")

consumer_subscription_name = os.environ.get(
    "SUB_NAME", f"{consumer_topic_name}-sub"
)

# Publishes notifications to start processing
publisher_topic_name = os.environ.get(
    "PROCESSING_TOPIC_NAME", "image-data-processing"
)
publisher, publisher_topic_path = publisher(publisher_topic_name)

log = create_logger()

redis_client = RedisClient('throttler', logger=log)

project_id = credentials.project_id


def extract_metric_data(query_data):
    for x in query_data:
        return _dataframe._extract_value(x.points[0].value)


# Filters incoming notifications and decides what to start
@error_handler
def callback(message):  # pylint: disable=too-many-statements
    log.debug('Message received')

    # TODO: optimize how often we query metrics API -> there is quota we might hit in high load
    # we should cache this and re-query only once in a 2 minutes or so
    result = query.Query(
        client,
        project_id,
        'pubsub.googleapis.com/subscription/num_undelivered_messages',
        minutes=SUBSCRIPTION_TIME_INTERVAL
    )

    query_data_monitor = result.select_resources(
        resource_type="pubsub_subscription",
        subscription_id=f"{MONITOR_TOPIC}-sub"
    )

    query_data_target = result.select_resources(
        resource_type="pubsub_subscription",
        subscription_id=f"{publisher_topic_name}-sub"
    )

    current_undelivered_count_monitor = extract_metric_data(query_data_monitor)

    current_undelivered_count_target = extract_metric_data(query_data_target)

    log.info(
        f'Current undelivered count monitor {current_undelivered_count_monitor}'
    )
    log.info(
        f'Current undelivered count target {current_undelivered_count_target}'
    )

    if (
            current_undelivered_count_target and  # noqa: W504 - caused by yapf
            current_undelivered_count_target > SUBSCRIPTION_MESSAGE_LIMIT
    ) or (
            current_undelivered_count_monitor and  # noqa: W504 - caused by yapf
            current_undelivered_count_monitor > SUBSCRIPTION_MESSAGE_LIMIT
    ):
        log.info("Message queue length limit reached - skipping message")
        message.nack()
    else:
        data = json.loads(
            message.data
        )  # TODO: How expensive is to do this? Can we use attributes instead?

        object_id = data["id"]
        object_id_parts = object_id.split("/")

        # staging-image-data-predicted -> staging-image-data
        app = "-".join(object_id_parts[0].split('-')[:-1]) \
            if object_id_parts[0].endswith('-raw') or \
               object_id_parts[0].endswith('-predicted') else object_id_parts[0]

        user_id = object_id_parts[1]
        folder = object_id_parts[2]

        extra_log = {'app': app, 'user_id': user_id, 'folder': folder}

        if not redis_client.is_processing_key(
                app, user_id, folder
        ) and not redis_client.can_process_more():
            log.debug(
                f"Concurrent user processing limit reached, message skipped "
                f"{app} {user_id} "
                f"{folder}",
                extra=extra_log
            )
            # redis_client.unack_counter()
            message.nack()
        else:
            publish(
                publisher,
                publisher_topic_path,
                data=message.data,
                meta=message.attributes
            )
            message.ack()


subscribe(consumer_topic_name, consumer_subscription_name, callback=callback)

# The subscriber is non-blocking, so we must keep the main thread from
# exiting to allow it to process messages in the background.
while True:
    time.sleep(5)
