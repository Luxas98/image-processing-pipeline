FROM eu.gcr.io/dev-lukas/gcsfuse:alpine-1.10

FROM eu.gcr.io/dev-lukas/pubsub-base:python3.6-alpine
COPY --from=0 /usr/local/bin/gcsfuse /usr/local/bin/gcsfuse
RUN apk add --no-cache fuse
RUN pip install --no-cache-dir redis

WORKDIR /app

COPY gcloudredis gcloudredis
COPY pubsubutils pubsubutils
COPY gcloudlogging gcloudlogging
RUN pip install -r gcloudlogging/requirements.txt

COPY services/observer/src/status_observer.py status_observer.py

# use -u so the stdout is sent to docker logs
CMD ["python", "-u", "status_observer.py"]
