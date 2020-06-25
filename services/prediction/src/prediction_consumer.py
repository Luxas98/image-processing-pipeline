# coding: utf8
"""
TODO: Write doc-string
"""
import os
import json
import time
import base64

import numpy as np
import tensorflow as tf

from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2_grpc

from seldon_core.seldon_client import grpc_predict_gateway, \
    microservice_api_grpc_seldon_message as grpc_predict
from seldon_core.seldon_client import rest_predict_gateway, \
    microservice_api_rest_seldon_message as rest_predict
from seldon_core.utils import seldon_message_to_json

import grpc
import googleapiclient.discovery

from gcloudlogging.logger import create_logger
from gcloudlogging.errors import error_handler
from pubsubutils.pubsub import subscribe, callback_info
from gcloudstorage.storage import file_exists, upload_file

from _dicom import load as load_dcm
from _nrrd import write as write_nrrd
from utils import get_patches, assemble_prediction
from utils import COMPRESSION_OPTIONS, serialize_prediction_to_tfrecord, \
    read_tfrecord, deserialize_tfrecord_to_data, serialize_data_to_tfrecord

# HOST = os.environ.get("ML_GATEWAY_HOST", "model-serving-ambassador")
HOST = os.environ.get("ML_GATEWAY_HOST", "boneseg-model-{}")
PORT = os.environ.get("ML_GATEWAY_PORT", 5000)
ENDPOINT = os.environ.get("ML_GATEWAY", f"{HOST}:{PORT}")
TIMEOUT = os.environ.get("PREDICTION_TIMEOUT", None)
# NAMESPACE = os.environ.get("NAMESPACE", "seldon-model-serving")

log = create_logger()


@error_handler
def callback(message):
    _, _ = callback_info(message)

    data_uri = message.attributes['OBJECT_URI']
    data_location = "gs://{}".format(data_uri)
    log.info(f'Predicting file {data_location}')
    model_params = message.attributes.get('METADATA')
    model_server = message.attributes.get('MODEL_SERVER', 'tfserving')
    from_raw = 'raw' in data_location and data_location.endswith('dcm')

    if model_params is not None:
        model_params = json.loads(model_params)
        app_name = model_params.get('app')

        if from_raw:
            # data_location endswith .dcm
            save_location = data_location.replace('raw', 'predicted').replace(
                'dcm', 'nrrd'
            )
            # save_location = data_location.replace('raw', 'predicted').replace(
            #     'dcm', 'tfrecord'
            # )
            # save_location endswith .tfrecord
        else:
            resample = model_params['resample']
            folder = 'processed/resampled' if 'true' == resample else 'processed/original'
            # data_location endswith .nrrd
            save_location = data_location.replace(folder, 'predicted')
            # save_location endswith .nrrd
            save_location = "/".join(save_location.split('/')[3:])

        if not file_exists(app_name, save_location):
            # tfrecord = make_prediction(
            prediction, metadata = make_prediction(
                data_location, model_params['model'], model_server, from_raw
            )

            # log.info('Parsing prediction to tfrecord')
            # tfrecord = serialize_prediction_to_tfrecord(prediction)
            # if 'seldon' == model_server:
            #     tfrecord = serialize_prediction_to_tfrecord(prediction)
            # else:
            #     tfrecord = serialize_prediction_to_tfrecord(prediction[..., None])

            log.info('Storing prediction to file: %s' % save_location)
            # store_tfrecord(save_location, tfrecord)
            store_nrrd(save_location, prediction, metadata)
            # upload_file(
            #     prediction,
            #     save_location,
            #     app_name,
            #     metadata=model_params
            # )

        else:
            log.info(f'Prediction already exists {app_name} {save_location}')

    message.ack()


def make_prediction(data_location, model, model_server, from_raw):
    if 'seldon' == model_server:
        serialized = read_tfrecord(data_location)
        prediction = make_seldon_prediction(serialized, model)
        return serialize_prediction_to_tfrecord(prediction)
    elif 'tfserving' == model_server:
        # serialized = read_tfrecord(data_location)
        # return make_tfserving_prediction(serialized, model)
        log.info('Parsing tfrecord to data')
        if data_location.endswith('dcm'):
            image, metadata = load_dcm(data_location)
            image = image.T[None]
        else:
            image = deserialize_tfrecord_to_data(data_location)[
                None]  # (depth, height, width)
            metadata = {}
        log.info('Making prediction')
        logits = make_concurrent_tfserving_prediction(image, model, offset=5)
        del image
        return post_predict(logits), metadata
        # prediction = post_predict(logits)[None]
        # del logits
        # log.info('Serializing prediction to tfrecord')
        # return serialize_prediction_to_tfrecord(prediction, metadata)
    else:
        # raise NotImplementedError('GCP engine not implemented')
        serialized = read_tfrecord(data_location)
        prediction = make_gcp_prediction(serialized, model)
        return serialize_prediction_to_tfrecord(prediction)


def make_concurrent_tfserving_prediction(image, model, offset):
    patch_slices = get_patches(np.array(image.squeeze().shape), offset)
    result_futures = [
        (
            j,
            predict_tfserving_api(
                serialize_data_to_tfrecord(image[..., slices[0], slices[1]]),
                shape=[1],
                model_name=model,
                model_input='serialized_example'
            )
        ) for j, slices in enumerate(patch_slices)
    ]

    predictions = collect_async_predictions(result_futures)
    shape = np.array(image.squeeze().shape)

    return assemble_prediction(predictions, shape, offset)


def collect_async_predictions(result_futures):
    predictions = []
    i = 0
    while len(result_futures) > 0:
        is_done = result_futures[i][1].done()
        if is_done:
            j, result_future = result_futures.pop(i)
            predictions.append(
                (
                    j,
                    collect_async_prediction(
                        result_future, model_output='logits'
                    )
                )
            )

        if i < len(result_futures) - 1:
            i += 1
        else:
            i = 0

    predictions = sorted(predictions, key=lambda x: x[0])
    # rank, preds = zip(*predictions)
    return [x[1] for x in predictions]


def collect_async_prediction(result_future, model_output):
    result = result_future.result().outputs[model_output]
    return np.array(result.float_val).reshape(
        tf.TensorShape(result.tensor_shape).as_list()
    )


def predict_tfserving_api(
    X,
    shape,
    model_name,
    model_input,
    host=f"{HOST}-tfserving",
    port=8500,
    timeout=None
):
    # TODO: phase out tf, phase 3
    # from protos.tensorflow_serving.apis import predict_pb2
    # from protos.tensorflow_serving.apis import prediction_service_pb2_grpc
    channel = grpc.insecure_channel("{}:{}".format(host, port))
    stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)

    request = predict_pb2.PredictRequest()
    request.model_spec.name = model_name
    request.model_spec.signature_name = 'serving_default'
    request.inputs[model_input].CopyFrom(tf.make_tensor_proto(X, shape=shape))
    # request.inputs[model_input].CopyFrom(make_tensor_proto(X, shape=shape))

    result_future = stub.Predict.future(request, timeout)
    return result_future


def make_seldon_prediction(serialized, model):
    endpoint = ENDPOINT

    kwargs = {
        # SELDON API GATEWAY
        # "deployment_name": model,
        # "namespace": NAMESPACE,
        # "namespace": model_params.get('namespace', NAMESPACE),
        # "gateway_endpoint": endpoint,
        # NAIVE API GATEWAY
        "method": "predict",
        "microservice_endpoint": endpoint,
        "payload_type": "tensor",
        # "bin_data": serialized,
        "bin_data": serialized,
        #     grpc_max_send_message_length: int = 4 * 1024 * 1024,
        #     grpc_max_receive_message_length: int = 4 * 1024 * 1024,
        #     names: Iterable[str] = None,
    }

    # return rest_predict_gateway(**kwargs)
    # return grpc_predict_gateway(**kwargs)
    response = grpc_predict(**kwargs)

    if response.success:
        log.info('GRPC - Prediction request successful')
        response = seldon_message_to_json(response.response)
        shape, values = response['data'].get('tensor').values()
        return np.array(values).reshape(shape[:-1])
    else:
        # log.info('REST request not succesfull.')
        log.info('GRPC - Prediction request not succesfull')


# def predict_seldon_grpc_request(data, endpoint="localhost:5000"):
#     tftensor = tf.make_tensor_proto(serialized_beam, shape=[1])
#     datadef = prediction_pb2.DefaultData(tftensor=tftensor)
#     request = prediction_pb2.SeldonMessage(data=datadef)
#     response = tf_proxy.predict_grpc(request)

#     request = prediction_pb2.SeldonMessage(data=datadef)
#     channel = grpc.insecure_channel(endpoint)
#     stub = prediction_pb2_grpc.ModelStub(channel)
#     response = stub.Predict(request=request)

#     return response

# def make_tfserving_prediction(serialized, model):
#     response = predict_tfserving_api(serialized, [1], model, 'serialized_example', 'logits')
#     return post_predict(
#         np.array(response.float_val).reshape(tf.TensorShape(response.tensor_shape).as_list())
#     )

# def predict_tfserving_api(X, shape, model_name, model_input, model_output):
#     # host, port = HOST.format(model_name), int(PORT)
#     host, port = f"{HOST}-tfserving", 8500
#     channel = implementations.insecure_channel(host, port)
#     stub = prediction_service_pb2_grpc.PredictionServiceStub(channel._channel)

#     request = predict_pb2.PredictRequest()
#     request.model_spec.name = model_name
#     request.model_spec.signature_name = 'serving_default'
#     request.inputs[model_input].CopyFrom(
#         tf.make_tensor_proto(X, shape=shape)
#     )

#     timeout = int(TIMEOUT) if TIMEOUT is not None else TIMEOUT
#     # result_future = stub.Predict.future(request, timeout)
#     # return result_future.result().outputs[model_output]
#     result = stub.Predict(request, timeout)
#     return result.outputs[model_output]


def make_gcp_prediction(serialized, model):
    instances = [
        {
            "serialized_example": {
                "b64": base64.b64encode(serialized).decode()
            }
        }
    ]
    predictions = predict_json(instances, model)
    return post_predict(np.array(predictions))


def predict_json(
    instances,
    model='test_model',
    version='optimized_model_quad_core',
    project='dev-lukas'
):
    """Send json data to a deployed model for prediction.

    Args:
        project (str): project where the Cloud ML Engine Model is deployed.
        model (str): model name.
        instances ([Mapping[str: Any]]): Keys should be the names of Tensors
            your deployed model expects as inputs. Values should be datatypes
            convertible to Tensors, or (potentially nested) lists of datatypes
            convertible to tensors.
        version: str, version of the model to target.
    Returns:
        Mapping[str: any]: dictionary of prediction results defined by the
            model.
    """
    # Create the ML Engine service object.
    # To authenticate set the environment variable
    # GOOGLE_APPLICATION_CREDENTIALS=<path_to_service_account_file>
    service = googleapiclient.discovery.build('ml', 'v1')
    name = f'projects/{project}/models/{model}'

    if version is not None:
        name += f'/versions/{version}'

    response = service.projects().predict(
        name=name, body={
            'instances': instances
        }
    ).execute()

    if 'error' in response:
        raise RuntimeError(response['error'])

    return response['predictions']


def post_predict(response, threshold=0.6):
    def softmax(x):
        y = x - x.max(axis=-1, keepdims=True)
        return np.exp(y) / np.sum(np.exp(y), axis=-1, keepdims=True)

    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    if isinstance(response, dict):
        logits = response['logits']
    else:
        logits = response

    if logits.shape[-1] > 1:
        preds = np.argmax(softmax(logits), axis=-1)
    else:
        preds = np.uint8(sigmoid(logits.squeeze()) > threshold)

    return preds


def store_nrrd(filename, data, metadata):
    space_origin = metadata.pop('space_origin')  # if metadata else 0
    z_spacing = metadata.pop('slice_thickness') if metadata else 0
    spacing = metadata.pop('spacing') + [z_spacing] if metadata else 0
    # z_spacing = metadata.pop('slice_thickness') if metadata else 1.
    # spacing = metadata.pop('spacing') + [z_spacing] if metadata else [1.]*3

    header = {
        'type': 'int8',
        'dimension': data.ndim,
        'space': 'left-posterior-superior',
        'sizes': data.shape,
        'kinds': ['domain', 'domain', 'domain'],
        'endian': 'little',
        'encoding': 'gzip',
        # (x, y, z)
        'space origin': space_origin,
        'space directions': np.diag(spacing),
        # 'space directions': np.diag(spacing) if spacing else "",
        **metadata
    }

    if not tf.gfile.Exists(filename):
        write_nrrd(filename, data, header)


def store_tfrecord(filename, tfrecord):
    tf_writer = tf.python_io.TFRecordWriter(
        filename, options=COMPRESSION_OPTIONS
    )
    tf_writer.write(tfrecord)
    tf_writer.close()


if __name__ == "__main__":
    topic_name = os.environ.get("TOPIC_NAME", "image-model-prediction")
    subscription_name = os.environ.get("SUB_NAME", f"{topic_name}-sub")

    subscribe(topic_name, subscription_name, callback)

    while True:
        # Dont sleep too much or too little :-) sleeping too much -> container reacts on commands only when awake
        time.sleep(5)
