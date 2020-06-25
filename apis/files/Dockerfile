# FROM eu.gcr.io/dev-lukas/data-api-flaskapp-base:pubsub
FROM eu.gcr.io/dev-lukas/data-api-flaskapp-base:dicom

WORKDIR /app

COPY flaskapp flaskapp
COPY apimessages apimessages
COPY gcloudredis gcloudredis
COPY gcloudstorage gcloudstorage
COPY pubsubutils pubsubutils

COPY apis/files/files flaskapp/files

COPY wsgi.py wsgi.py
COPY uwsgi.ini uwsgi.ini
COPY manage.py manage.py
COPY entrypoint.sh entrypoint.sh

RUN chmod +x entrypoint.sh

# ugly hack
RUN echo 'class DicomCleaner:' > /usr/local/lib/python3.6/site-packages/deid/dicom/pixels/clean.py
RUN echo '    pass' >> /usr/local/lib/python3.6/site-packages/deid/dicom/pixels/clean.py

ENTRYPOINT ["/app/entrypoint.sh"]






