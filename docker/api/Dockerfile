ARG ADMIN_PROJECT_ID
ARG IMAGE=eu.gcr.io/${ADMIN_PROJECT_ID}/pubsub-base:python3.6-alpine
FROM ${IMAGE}

COPY ./requirements.txt requirements.txt

RUN apk update \
    && apk --virtual .build-deps add build-base musl-dev libffi-dev \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps


RUN pip uninstall -y marshmallow \
  && pip install --no-cache-dir marshmallow==2.19.2

CMD []
