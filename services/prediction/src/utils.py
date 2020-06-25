# coding: utf8
"""
TODO: Write doc-string
"""
import numpy as np

# TODO: phase out tf, phase 3
# try:
import tensorflow as tf

# def open_file(filename):
#     return tf.gfile.GFile(filename, 'rb')

# except Exception:
from io import BytesIO
import zlib
from gcloudstorage import storage

decompressor = zlib.decompressobj()

def open_file(data_location, decompression=False):
    # 0: gs, 1: '', 2: app_name, rest: filename
    location_parts = data_location.split('/')
    app_name = location_parts[2]
    filename = "/".join(location_parts[3:])
    binary_data = storage.get_file(filename, app_name)
    if decompression:
        return BytesIO(decompressor.decompress(binary_data))
    else:
        return BytesIO(binary_data)


# TF < 1.14.0
# COMPRESSION_OPTIONS = tf.python_io.TFRecordOptions(
#     tf.python_io.TFRecordCompressionType.ZLIB
# )

# TF >= 1.14.0
COMPRESSION_OPTIONS = tf.io.TFRecordOptions(tf.io.TFRecordCompressionType.ZLIB)
MAX_SIZE = 256


def read_tfrecord(data_location):
    record_iterator = tf.python_io.tf_record_iterator(
        path=data_location, options=COMPRESSION_OPTIONS
    )
    return next(record_iterator)


def is_list(x):
    return isinstance(x, list)


def is_type(x, t):
    return is_list(x) and all([isinstance(y, t) for y in x]) or isinstance(x, t)


def _int64_feature(x):
    value_list = x if is_list(x) else [x]
    return tf.train.Feature(int64_list=tf.train.Int64List(value=value_list))


def _float64_feature(x):
    value_list = x if is_list(x) else [x]
    return tf.train.Feature(float_list=tf.train.FloatList(value=value_list))


def _bytes_feature(x):
    if isinstance(x, str):
        x = tf.compat.as_bytes(x)
    value_list = x if is_list(x) else [x]
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=value_list))


def serialize_feature_to_proto(x):
    if is_type(x, int):
        return _int64_feature(x)
    elif is_type(x, float):
        return _float64_feature(x)
    elif is_type(x, (str, bytes)):
        return _bytes_feature(x)
    else:
        raise TypeError


def serialize_data_to_tfrecord(data_array, metadata={}):
    depth, height, width = data_array.shape
    return tf.train.Example(
        features=tf.train.Features(
            feature={
                'image_height':
                    _int64_feature(height),
                'image_width':
                    _int64_feature(width),
                'image_depth':
                    _int64_feature(depth),
                'image_raw':
                    _bytes_feature(
                        data_array.astype('int32').ravel().tostring()
                    ),
                **{
                    k: serialize_feature_to_proto(v)
                    for k, v in metadata.items()
                }
            }
        )
    ).SerializeToString()  # noqa: E122


def deserialize_tfrecord_to_data(filename):
    example = tf.train.Example()
    example.ParseFromString(read_tfrecord(filename))

    height = example.features.feature["image_height"].int64_list.value[0]
    width = example.features.feature["image_width"].int64_list.value[0]
    # depth = example.features.feature["image_depth"].int64_list.value[0]
    data = np.frombuffer(
        example.features.feature["image_raw"].bytes_list.value[0],
        dtype="int32"
    )
    return data.reshape(height, width)


def serialize_prediction_to_tfrecord(data_array, metadata={}):
    depth, height, width = data_array.shape
    return tf.train.Example(
        features=tf.train.Features(
            feature={
                'height':
                    _int64_feature(height),
                'width':
                    _int64_feature(width),
                'depth':
                    _int64_feature(depth),
                'prediction':
                    _bytes_feature(
                        data_array.astype('int8').ravel().tostring()
                    ),
                **{
                    k: serialize_feature_to_proto(v)
                    for k, v in metadata.items()
                }
            }
        )
    ).SerializeToString()  # noqa: E122


def get_slice(patch_size, i, shape, max_i, offset=0):
    max_shape = patch_size * (i + 1)
    if i == 0:
        start = patch_size * i
    else:
        start = patch_size * i - offset

    if i < max_i:
        stop = min(max_shape, shape) + offset
    else:
        stop = min(max_shape, shape)
    return slice(start, stop)


def get_divisor(x):
    return x // MAX_SIZE + int(x % MAX_SIZE > 0)


def get_patches(shape, offset):
    num_rows, num_cols = num_rows_cols = np.array(
        [get_divisor(x) for x in shape]
    )
    max_sizes = shape // num_rows_cols
    patches = [
        (
            get_slice(max_sizes[0], row, shape[0], num_rows - 1, offset),
            get_slice(max_sizes[1], col, shape[1], num_cols - 1, offset)
        ) for row in range(num_rows) for col in range(num_cols)
    ]
    return patches


def fix_slice(sl, i, offset, max_index=1):
    if i == 0:
        start = sl.start
    else:
        start = sl.start + offset

    if i < max_index:
        stop = sl.stop - offset
    else:
        stop = sl.stop

    return slice(start, stop)


def assemble_prediction(prediction_patches, shape, offset):
    prediction = np.zeros(shape)
    num_rows, num_cols = np.array([get_divisor(x) for x in shape])
    rc_indices = [
        (row, col) for row in range(num_rows) for col in range(num_cols)
    ]
    for rc, slices, patch in zip(
        rc_indices, get_patches(shape, offset), prediction_patches
    ):
        sl_1 = fix_slice(slices[0], rc[0], offset)
        sl_2 = fix_slice(slices[1], rc[1], offset)
        #         print(sl_1, sl_2)

        diff_x = slices[0].stop - slices[0].start
        diff_y = slices[1].stop - slices[1].start
        sl_x = slice(0, diff_x)
        sl_y = slice(0, diff_y)
        #         print(sl_x, sl_y)

        sl_x = fix_slice(sl_x, rc[0], offset)
        sl_y = fix_slice(sl_y, rc[1], offset)
        #         print(sl_x, sl_y)

        prediction[sl_1, sl_2] = patch.squeeze()[sl_x, sl_y]

    return prediction[..., None]


# TODO: phase out tf, phase 3
# def make_tensor_proto(X, shape):
#     from protos.tensorflow.core.framework import tensor_pb2
#     from protos.tensorflow.core.framework import tensor_shape_pb2
#     from protos.tensorflow.core.framework import types_pb2

#     dims = [tensor_shape_pb2.TensorShapeProto.Dim(size=dim) for dim in shape]
#     tensor = tensor_pb2.TensorProto(
#         dtype=types_pb2.DT_STRING if isinstance(X, (str, bytes)) types_pb2.DT_FLOAT,
#         tensor_shape=tensor_shape_pb2.TensorShapeProto(dim=dims),
#     )
#     if isinstance(X, bytes):
#         tensor_proto.string_val.extend([X])
#     elif isinstance(X, str):
#         tensor_proto.string_val.extend([X.encode('utf-8')])
#     else:
#         tensor_proto.tensor_content = X.tostring()

#     return tensor
