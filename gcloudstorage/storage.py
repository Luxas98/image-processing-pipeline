import gzip
import io
import os
from google.cloud import storage
import six
import logging

log = logging.getLogger()

PROJECT_ID = os.environ.get('PROJECT_ID', 'my-project')
MODEL_STORAGE_BUCKET = 'TODO'  # TODO: where/how are we going to store models


def _get_storage_client():
    if hasattr(_get_storage_client, 'client'):
        return _get_storage_client.client

    _get_storage_client.client = storage.Client(project=PROJECT_ID)
    return _get_storage_client.client


def _distinct_folders(blobs):
    folders = [f.name for f in blobs]
    folders = [f.split('/') for f in folders]
    folders = list(set([f[1] for f in folders if len(f) > 1]))
    return folders


def file_exists(app_name, filepath):
    client = _get_storage_client()
    bucket = client.bucket(app_name)
    blob = bucket.blob(filepath)
    return blob.exists()


def get_file(filename, app_name):
    client = _get_storage_client()
    bucket = client.bucket(app_name)
    blob = bucket.get_blob(filename)
    return blob.download_as_string()


def upload_file(file_stream, filename, app_name, metadata, compress=False):
    """
    Uploads a file to a given Cloud Storage bucket and returns the public url
    to the new object.
    """
    log.info('Uploading file %s' % filename)

    client = _get_storage_client()
    bucket = client.bucket(app_name)

    if not compress:
        blob = bucket.blob(filename)
        blob.metadata = dict(**metadata)
        # test if we are trying to upload FILE or string into file
        if isinstance(file_stream, io.IOBase):
            blob.upload_from_file(file_stream, content_type="application/json")
        else:
            blob.upload_from_string(file_stream, content_type="application/octet-stream")

        blob.reload()
    else:
        fgz = io.BytesIO()
        gzip_obj = gzip.GzipFile(filename=filename, mode='wb', fileobj=fgz)
        gzip_obj.write(file_stream)
        gzip_obj.close()

        blob = bucket.blob(filename + '.gz')
        blob.upload_from_string(fgz.read())

    url = blob.public_url

    if isinstance(url, six.binary_type):
        url = url.decode('utf-8')

    return url


def list_all_files(user_id, folder, app_name):
    client = _get_storage_client()
    bucket = client.bucket(app_name)

    prefix = os.path.join(*[str(user_id), folder])

    files = list(bucket.list_blobs(prefix=prefix))
    return files


def list_all_folders(user_id, app_name):
    client = _get_storage_client()

    bucket = client.bucket(app_name)
    prefix = os.path.join(*[str(user_id)])
    folders = list(bucket.list_blobs(prefix=prefix))
    return folders


def list_all_models():
    client = _get_storage_client()
    bucket = client.bucket(MODEL_STORAGE_BUCKET)
    blobs = bucket.list_blobs(prefix='models/experiment')
    folders = _distinct_folders(blobs)
    return folders


def upload(user_id, folder, files, app_name):
    current_folder = folder
    folder = ["{user_id}/{folder}/".format(user_id=user_id, folder=current_folder)]
    directory = os.path.join(*folder)

    files_uploaded = []

    for name, f in files.items():
        parts = [directory, 'dcm', f.filename]
        filepath = os.path.join(*parts)
        upload_file(f.read(), filepath, app_name, {})
        files_uploaded.append(f.filename)

    return files_uploaded


def list_files(user_id, folder, app_name):
    return [f.name for f in list_all_files(user_id, folder, app_name)]


def list_folders(user_id, app_name):
    folders = [f.name for f in list_all_folders(user_id, app_name)]
    folders = [f.split('/') for f in folders]
    folders = list(set([f[1] for f in folders if len(f) > 1]))
    return folders


def delete_folder(user_id, app_name, folder):
    client = _get_storage_client()
    bucket = client.bucket(app_name)
    folders = bucket.list_blobs(prefix=f'{user_id}{folder}')

    for f in folders:
        f.delete()

    return [f.name for f in folders]
