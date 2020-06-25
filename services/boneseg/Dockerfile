FROM eu.gcr.io/dev-lukas/gcsfuse:alpine-1.10

FROM eu.gcr.io/dev-lukas/data-services-boneseg-base:alpine-tf1.12.0
COPY --from=0 /usr/local/bin/gcsfuse /usr/local/bin/gcsfuse
RUN mkdir -p /etc/secrets/consul
RUN apk add --no-cache fuse
RUN pip install --no-cache-dir --upgrade --no-deps pynrrd==0.4.0

WORKDIR /app

COPY pubsubutils pubsubutils
COPY gcloudlogging gcloudlogging
COPY services/boneseg/requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN pip install -r gcloudlogging/requirements.txt

COPY services/boneseg/src/boneseg_consumer.py boneseg_consumer.py
COPY services/boneseg/src/_nrrd.py _nrrd.py
COPY services/boneseg/src/utils.py utils.py

# use -u so the stdout is sent to docker logs
CMD ["python", "-u", "boneseg_consumer.py"]
