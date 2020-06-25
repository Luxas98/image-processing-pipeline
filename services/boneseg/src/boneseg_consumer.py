# coding: utf8
"""
TODO: Write doc-string
"""
import os
import json
from time import sleep
import numpy as np
import tensorflow as tf
from skimage import measure
import trimesh
from _nrrd import load as load_nrrd, write as write_nrrd

from gcloudlogging.logger import create_logger
from gcloudlogging.errors import error_handler
from pubsubutils.pubsub import subscribe, callback_info

COMPRESSION_OPTIONS = tf.python_io.TFRecordOptions(
    tf.python_io.TFRecordCompressionType.ZLIB
)

PROJECT_ID = os.environ.get("GCP_PROJECT", "dev-lukas")

log = create_logger()

METADATA_NAMES = [
    'rescale_slope', 'rescale_intercept', 'space_origin', 'spacing',
    'slice_thinkness', 'patient_position'
]


def get_mesh(image, threshold=0):
    verts, faces, normals, values = measure.marching_cubes_lewiner(
        image, threshold
    )
    # Fancy indexing: `verts[faces]` to generate a collection of triangles
    return trimesh.Trimesh(verts, faces)


def get_list_or_scalar(x):
    return list(x) if len(x) > 1 else x[0]


def get_feature_values(feature):
    if feature.int64_list.value:
        return get_list_or_scalar(feature.int64_list.value)
    elif feature.float_list.value:
        return get_list_or_scalar(feature.float_list.value)
    elif feature.bytes_list.value:
        # return [tf.compat.as_str(x) for x in feature.bytes_list.value]
        return tf.compat.as_str(feature.bytes_list.value[0])
    else:
        raise TypeError


def decode_tfrecord_to_metadata(example, feature_names):
    return {
        feature_name:
        get_feature_values(example.features.feature[feature_name])
        for feature_name in feature_names
        if example.features.feature.get(feature_name, False)
    }


def decode_tfrecord_to_numpy(filename):
    log.info(f"Reading prediction from file: {filename}")

    record_iterator = tf.python_io.tf_record_iterator(
        path=filename, options=COMPRESSION_OPTIONS
    )

    example = tf.train.Example()
    example.ParseFromString(next(record_iterator))

    # c = example.features.feature['image_data'].bytes_list.value[0]
    # # get bytes
    # sz = len(c)  # get number of float64 entries
    # log.info('Bytes in file: {}'.format(sz))
    # # create array from packed entries which are at end of bytes -
    # assumes same endianness
    # raw_data = np.frombuffer(
    #     memoryview(c[-(sz * 8):]), dtype=np.uint8, count=sz, offset=0
    # )

    prediction = np.frombuffer(
        example.features.feature["prediction"].bytes_list.value[0],
        dtype="int8"
    )

    height = example.features.feature["height"].int64_list.value[0]
    width = example.features.feature["width"].int64_list.value[0]
    # depth = example.features.feature['depth'].int64_list.value[0]

    metadata = decode_tfrecord_to_metadata(example, METADATA_NAMES)

    prediction = prediction.reshape(height, width)

    log.info(f"Image shape: {prediction.shape}")
    if metadata:
        return prediction, metadata
    else:
        return prediction,


def read_metadata(filename):
    metadata_filename = filename.replace("/predicted", "/processed")
    metadata_filename = metadata_filename.replace("tfrecord", "json")
    metadata_filename = metadata_filename.replace('FILE', 'METADATA')
    log.info(f'Loading metadata {metadata_filename}')
    return json.loads(tf.gfile.GFile(metadata_filename, 'rb').read())


@error_handler
def callback(message):
    _, _ = callback_info(message)

    prediction_uri = message.attributes["OBJECT_URI"]
    prediction_location = "gs://{}".format(prediction_uri)
    if message.attributes["COMBINE"] == "Y":
        log.debug("Combining!")
        # OBJECT_URL is a folder with tfrecords
        # files = tf.gfile.Glob(prediction_location + "/*.tfrecord")
        files = tf.gfile.Glob(prediction_location + "/*.nrrd")
        result_url = prediction_location

        log.info(
            f"Post-processing predictions from folder: {prediction_location}"
        )
        log.info(f"File count to post-process: {len(files)}")

        filename = result_url.replace("/predicted", "/post-processed")
        filename = f"{filename}/combined.mesh.stl"
    else:
        log.debug("Not combining!")
        # OBJECT_URL is a tfrecord filename
        files = [prediction_location]
        prediction_url_parts = prediction_location.split("/")[:-1]
        result_url = os.path.join(*prediction_url_parts)

        filename = result_url.replace("/predicted", "/post-processed")
        filename = filename.replace("tfrecord", "stl")

        log.info(f"Post-processing prediction for: {prediction_location}")

    sorted_files = sorted(files)
    decoded = list(
        zip(*[load_nrrd(filename) for filename in sorted_files])
        # zip(*[decode_tfrecord_to_numpy(filename) for filename in sorted_files])
    )
    image = np.dstack(decoded[0])  # depth as the last dimension
    log.debug(f"Image shape non-unique: {image.shape}")

    unique_values = np.unique(image)
    log.info(f"Data received {image.shape}")
    log.info(f"Unique values {unique_values}")

    if len(unique_values) == 1:
        log.error(f"ERROR - Predicted SINGLE value: {unique_values[0]}")
    else:
        log.info(f"Storing labelmap to file: {filename.replace('stl', 'nrrd')}")
        log.info(f'Headers loding test {decoded}')
        if len(decoded) == 2:
            headers = decoded[1]
        else:
            headers = [read_metadata(filename) for filename in sorted_files]

        # dicom_tags = headers[0].pop('dcm.PatientPosition')
        # dicom_tags['Patient Position']
        if headers and headers[0]:
            patient_position = headers[0].pop('patient_position')
        else:
            patient_position = None
            log.warning(f'No headers found {headers}, {decoded}')

        if patient_position:
            if patient_position.startswith('HF'):
                metadata = headers[-1]
                image = image[..., ::-1]
            # elif patient_position.startswith('RF'):
            #     # TODO?
            # elif patient_position.startswith('LF'):
            #     # TODO?
            else:
                # patient_position.startswith('FF') is True
                metadata = headers[0]
                # image is image
        else:
            metadata = {}
            image = image[..., ::-1]

        # space_origin = metadata.pop('space_origin') if metadata else 0
        # z_spacing = metadata.pop('slice_thinkness') if metadata else 0
        # spacing = metadata.pop('spacing') + [z_spacing] if metadata else 0

        header = {
            'type': 'int8',
            'dimension': 3,
            'space': 'left-posterior-superior',
            'sizes': image.shape,
            'kinds': ['domain', 'domain', 'domain'],
            'endian': 'little',
            'encoding': 'gzip',
            # (x, y, z)
            # 'space origin': space_origin,
            # 'space directions': np.diag(spacing) if spacing else "",
            'space origin': metadata['space origin'],
            'space directions': metadata['space directions']
        }
        if not tf.gfile.Exists(filename.replace('stl', 'nrrd')):
            write_nrrd(filename.replace('stl', 'nrrd'), image, header)
            log.info('Finished generating NRRD')

        log.info('Finished prediction')

        # log.info(f"Generating mesh")
        # export_blob = get_mesh(1 - image, 0).export(None, file_type="stl")
        #
        # log.info(f"Storing mesh to file: {filename}")
        # # TODO: do we always want to store stl?
        #
        # if not tf.gfile.Exists(filename):
        #     with tf.gfile.GFile(filename, "wb") as fh:
        #         fh.write(export_blob)
        #     fh.close()

    message.ack()


if __name__ == "__main__":
    app_name = os.environ.get("APP_NAME", "test-image")
    topic_name = os.environ.get(
        "POSTPROCESSING_TOPIC_NAME", "image-prediction-post-processing"
    )
    subscription_name = os.environ.get(
        "POSTPROCESSING_SUB_NAME", f"{topic_name}-sub"
    )

    subscribe(topic_name, subscription_name, callback=callback)

    while True:
        sleep(5)
