ARG ADMIN_PROJECT_ID
FROM eu.gcr.io/${ADMIN_PROJECT_ID}/gcsfuse:alpine-1.10

FROM hashicorp/consul-template:alpine
USER root
COPY --from=0 /usr/local/bin/gcsfuse /usr/local/bin/gcsfuse
RUN apk add fuse
RUN mkdir -p /etc/secrets/consul
COPY entrypoint.sh /bin/docker-entrypoint.sh
RUN chmod +x /bin/docker-entrypoint.sh
