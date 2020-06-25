from .errors import ATTRIBUTE_ERROR_TMP

APP_FIELD = 'APP'
USER_ID_FIELD = 'USER_ID'
FOLDER_FIELD = 'FOLDER'
INSTANCE_ID_FIELD = 'INSTANCE_ID'
STATUS_FIELD = 'STATUS'
ERROR_FIELD = 'ERROR'
LAST_UPDATE_FIELD = 'LAST_UPDATED'
IDENTFIER_FIELD = 'IDENTIFIER'
MESSAGE_FIELD = 'MESSAGE'
DATA_FIELD = 'DATA'
METADATA_FIELD = 'METADATA'
UPDATE_HISTORY = 'UPDATE_HISTORY'
INGESTION_START_TIME = 'INGESTION_START_TIME'


class API_MESSAGE_TEMPLATE(dict):
    init_params = [INSTANCE_ID_FIELD]
    required_params = [APP_FIELD, USER_ID_FIELD, FOLDER_FIELD, STATUS_FIELD]
    optional_params = [ERROR_FIELD, LAST_UPDATE_FIELD, IDENTFIER_FIELD, MESSAGE_FIELD, DATA_FIELD, METADATA_FIELD,
                       UPDATE_HISTORY]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for param in self.init_params:
            if param not in self:
                raise AttributeError(ATTRIBUTE_ERROR_TMP.format(param))

        for oparam in self.optional_params:
            if oparam not in self:
                self[oparam] = ''

    def __call__(self, **kwargs):
        self.update(**kwargs)
        for param in self.required_params:
            if param not in self:
                raise AttributeError(ATTRIBUTE_ERROR_TMP.format(param))

        for param in self.optional_params:
            if param not in self:
                self[param] = ''

        return dict(self)


class ResponseGenerator(object):
    def __init__(self, app_name='', user_id='', folder='', service_name='', instance_id=''):
        self.app_name = app_name
        self.user_id = user_id
        self.folder = folder

        self.service_name = service_name
        self.instance_id = instance_id

        self.RESPONSE_TEMPLATE = API_MESSAGE_TEMPLATE(
            SERVICE=service_name, INSTANCE_ID=instance_id
        )

    def missing_parameter(self, parameter_name):
        return self.RESPONSE_TEMPLATE(
                    **{
                        APP_FIELD: self.app_name,
                        USER_ID_FIELD: self.user_id,
                        FOLDER_FIELD: self.folder,
                        STATUS_FIELD: 'ERROR',
                        ERROR_FIELD: f'Required parameter {parameter_name}'
                    }
                )

    def error(self, error_message):
        return self.RESPONSE_TEMPLATE(
                    **{
                        APP_FIELD: self.app_name,
                        USER_ID_FIELD: self.user_id,
                        FOLDER_FIELD: self.folder,
                        STATUS_FIELD: 'ERROR',
                        ERROR_FIELD: f'{error_message}'
                    }
                )

    def prediction_status_response(self, current_statuses):
        return [self.RESPONSE_TEMPLATE(**{
            APP_FIELD: self.app_name,
            USER_ID_FIELD: self.user_id,
            FOLDER_FIELD: self.folder,
            STATUS_FIELD: 'INFO',
            **kwargs,
        }) for kwargs in current_statuses]

    def unsupported_type(self, type_name, possible_options):
        type_name = type_name.capitalize()
        error_message = f"{type_name} type not supported"

        if possible_options:
            error_message = f"{error_message}, please specify type, one of [{possible_options}]"

        return self.RESPONSE_TEMPLATE(
                    **{
                        APP_FIELD: self.app_name,
                        USER_ID_FIELD: self.user_id,
                        FOLDER_FIELD: self.folder,
                        STATUS_FIELD: 'ERROR',
                        ERROR_FIELD: error_message# pylint: disable=C0301
                    }
                )

    def response(self, status="", message="", data=""):
        return self.RESPONSE_TEMPLATE(**{
                    APP_FIELD: self.app_name,
                    USER_ID_FIELD: self.user_id,
                    FOLDER_FIELD: self.folder,
                    STATUS_FIELD: status,
                    MESSAGE_FIELD: message,
                    DATA_FIELD: data
                })
