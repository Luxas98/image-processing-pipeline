ARG ADMIN_PROJECT_ID
FROM eu.gcr.io/${ADMIN_PROJECT_ID}/gcsfuse:alpine-1.10

FROM python:3.6-alpine
COPY --from=0 /usr/local/bin/gcsfuse /usr/local/bin/gcsfuse
RUN apk add --update --no-cache libc6-compat libstdc++ fuse && \
    apk add --update --virtual .build-deps build-base \
    gcc musl-dev python-dev linux-headers make && \
    pip install --upgrade pip && \
    pip install --no-cache-dir google-api-core google-cloud-pubsub google-cloud-storage && \
    rm -rf /var/cache/apk/* && apk del .build-deps

RUN mkdir -p /etc/secrets/consul
