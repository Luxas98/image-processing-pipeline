# coding: utf8
"""
TODO: Write doc-string
"""
# TODO: phase out tf, phase 3
# try:
import tensorflow as tf

def open_file(filename):
    return tf.gfile.GFile(filename, 'rb')

# except Exception:
#     from io import BytesIO
#     import zlib
#     import numpy as np
#     from gcloudstorage import storage

#     decompressor = zlib.decompressobj()


#     def open_file(data_location, decompression=False):
#         # 0: gs, 1: '', 2: app_name, rest: filename
#         location_parts = data_location.split('/')
#         app_name = location_parts[2]
#         filename = "/".join(location_parts[3:])
#         binary_data = storage.get_file(filename, app_name)
#         if decompression:
#             return BytesIO(decompressor.decompress(binary_data))
#         else:
#             return BytesIO(binary_data)
