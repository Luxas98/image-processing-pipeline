FROM eu.gcr.io/dev-lukas/data-api-flaskapp-base:pubsub

WORKDIR /app

COPY flaskapp flaskapp

COPY apimessages apimessages
COPY gcloudredis gcloudredis
COPY gcloudstorage gcloudstorage
COPY pubsubutils pubsubutils

COPY apis/prediction/prediction flaskapp/prediction

COPY wsgi.py wsgi.py
COPY uwsgi.ini uwsgi.ini
COPY manage.py manage.py
COPY entrypoint.sh entrypoint.sh

RUN chmod +x entrypoint.sh

CMD ["/app/entrypoint.sh"]
