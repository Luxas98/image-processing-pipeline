FROM eu.gcr.io/dev-lukas/data-api-flaskapp-base:pubsub

WORKDIR /app

COPY flaskapp flaskapp

# add your code

COPY wsgi.py wsgi.py
COPY uwsgi.ini uwsgi.ini
COPY manage.py manage.py
COPY entrypoint.sh entrypoint.sh

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]






