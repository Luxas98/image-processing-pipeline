#!/bin/sh
PROFILING=${PROFILING:="False"}
case ${PROFILING} in
    "True") python3 manage.py run --host 0.0.0.0 --port 5000;;
    *) PYTHONUNBUFFERED=0 gunicorn -w 2 -b 0.0.0.0:5000 wsgi:application --enable-stdio-inheritance --log-config gunicorn.conf --access-logfile "-";
esac

