FROM eu.gcr.io/dev-lukas/gcsfuse:alpine-1.10

# FROM eu.gcr.io/dev-lukas/image-services-prediction-base:alpine-tf1.14.0-pydicom
FROM eu.gcr.io/dev-lukas/dicom-predictor:tf1.12.0-py36-alpine
COPY --from=0 /usr/local/bin/gcsfuse /usr/local/bin/gcsfuse
RUN mkdir -p /etc/secrets/consul
RUN apk add --no-cache fuse

WORKDIR /app


COPY pubsubutils pubsubutils
COPY gcloudstorage gcloudstorage
COPY gcloudlogging gcloudlogging
COPY services/prediction/requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN pip install -r gcloudlogging/requirements.txt

COPY services/prediction/src/prediction_consumer.py prediction_consumer.py
COPY services/prediction/src/_nrrd.py _nrrd.py
COPY services/prediction/src/_dicom.py _dicom.py
COPY services/prediction/src/utils.py utils.py

# use -u so the stdout is sent to docker logs
CMD ["python", "-u", "prediction_consumer.py"]
