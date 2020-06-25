import logging
import os
import redis
import json
from time import time
from .apimessages import status as api_status

DEBUG = os.environ.get('DEBUG', False)

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6378))

IDENTIFIERS_KEY = '{app}:{user_id}:{folder}'
STATUS_KEY = '{app}:{user_id}:{folder}:{identifier}'
PROCESSING_KEY = 'PROCESSING_KEYS'
UNACK_COUNTER = 'REQUEUE_COUNTER'

PROCESSING_LIMIT = int(os.environ.get('PROCESSING_LIMIT', 2))


class RedisClient(object):
    def __init__(self, instance_id, host=REDIS_HOST, port=REDIS_PORT, logger=logging.getLogger()):
        self.redis_client = redis.Redis(host=host, port=port)
        self.instance = instance_id
        self.log = logger

    def _gsk(self, app, user_id, folder, identifier):
        # GET STATUS KEY
        return STATUS_KEY.format(
            app=app, user_id=user_id, folder=folder, identifier=identifier)

    def _gik(self, app, user_id, folder):
        # GET IDENTIFIER KEY
        return IDENTIFIERS_KEY.format(app=app, user_id=user_id, folder=folder)

    def _gpk(self):
        return PROCESSING_KEY

    def _add_identifier(self, app, user_id, folder, identifier):
        identifier_key = self._gik(app, user_id, folder)
        self.redis_client.sadd(identifier_key, identifier)

    def get_status(self, app, user_id, folder, identifier):
        identifier = identifier.split('.')[0]
        status_raw = self.redis_client.get(
            self._gsk(app, user_id, folder, identifier))
        if not status_raw:
            return {}
        return json.loads(status_raw)

    def list_identifiers(self, app, user_id, folder):
        return [i.decode('utf-8') for i in self.redis_client.smembers(self._gik(app, user_id, folder))]

    def push_status(self,
                    app,
                    user_id,
                    folder,
                    identifier,
                    metadata=None,
                    error='',
                    status='',
                    extra_log=None):
        if DEBUG:
            start = time()
        extra_log = extra_log or {}
        if not identifier:
            self.log.warning(
                f'Trying to push to with empty identifier returning! {app}, {user_id} {folder} {identifier} {error} {status}',
                extra=extra_log
            )
            return

        metadata = metadata or {}
        # We want to use just a filename without extension as identifier even though stored files are with .dcm/.nrrd/.tfrecord
        identifier = identifier.split('.')[0]

        self._add_identifier(app, user_id, folder, identifier)

        message = {
            api_status.APP_FIELD: app,
            api_status.USER_ID_FIELD: user_id,
            api_status.FOLDER_FIELD: folder,
            api_status.STATUS_FIELD: status,
            api_status.INSTANCE_ID_FIELD: self.instance,
            api_status.ERROR_FIELD: error,
            api_status.METADATA_FIELD: metadata,
            api_status.LAST_UPDATE_FIELD: str(int(time())),
            api_status.INGESTION_START_TIME: str(int(time()))
        }

        status_key = self._gsk(app, user_id, folder, identifier)

        # Check is current status exists, if so update it
        current_status = self.redis_client.get(status_key)
        if current_status:
            json_message = json.loads(current_status)
            if status:
                json_message.update({api_status.STATUS_FIELD: status})
            if metadata:
                json_message.update({api_status.METADATA_FIELD: metadata})
            if error:
                json_message.update({api_status.ERROR_FIELD: error})

            last_updated = json_message[api_status.LAST_UPDATE_FIELD]

            if api_status.UPDATE_HISTORY not in json_message:
                json_message.update({api_status.UPDATE_HISTORY: [(last_updated, status)]})
            else:
                json_message[api_status.UPDATE_HISTORY].append((last_updated, status))

            json_message.update({api_status.LAST_UPDATE_FIELD: str(int(time()))})
            current_status = json_message
        else:
            current_status = message

        self.redis_client.set(status_key, json.dumps(current_status))
        if DEBUG:
            extra_log['REDIS_STATUS_UPDATE_TIME'] = time() - start

        self.log.debug('Updating status in redis', extra=extra_log)

    def get_all_status(self, app, user_id, folder):
        identifiers = self.list_identifiers(app, user_id, folder)
        results = []
        for identifier in identifiers:
            self.log.debug(f"Identifier: {identifier}")
            status = self.get_status(app, user_id, folder, identifier)
            s = status.get('STATUS')

            if s:
                metadata = status.get(api_status.METADATA_FIELD)
                results.append((identifier, s, metadata))

        return results

    def push_status_for_all(self, app, user_id, folder, identifiers=None, error='', status=''):
        identifiers = identifiers or self.list_identifiers(app, user_id, folder)
        for identifier in identifiers:
            self.push_status(app, user_id, folder, identifier, error, status)

    def add_processing_key(self, app, user_id, folder):
        identifier_key = self._gik(app, user_id, folder)
        self.redis_client.sadd(self._gpk(), identifier_key)  # O(1)

    def is_processing_key(self, app, user_id, folder):
        identifier_key = self._gik(app, user_id, folder)
        return self.redis_client.sismember(self._gpk(), identifier_key)  # O(1)

    def remove_processing_key(self, app, user_id, folder, extra_log=None):
        identifier_key = self._gik(app, user_id, folder)
        response = self.redis_client.srem(self._gpk(), identifier_key)  # O(1)
        self.log.info(f"Removed key from processing {identifier_key} {response}", extra=extra_log)

    def unack_counter(self):
        self.redis_client.incr(UNACK_COUNTER)

    def can_process_more(self):
        current_processing_count = self.redis_client.scard(self._gpk())  # O(1)
        if current_processing_count >= PROCESSING_LIMIT:
            return False
        return True
