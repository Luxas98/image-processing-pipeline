ADMIN_PROJECT_ID=${ADMIN_PROJECT_ID:=dev-lukas}
docker build -t eu.gcr.io/${ADMIN_PROJECT_ID}/gcsfuse:alpine-1.10 .