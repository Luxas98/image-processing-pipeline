from flaskapp.app import create_app
from werkzeug.debug import DebuggedApplication
from werkzeug.contrib.profiler import ProfilerMiddleware
import os

application = create_app()

DEBUG = os.environ.get('DEBUG', False)

if DEBUG:
    application.debug = True
    application.wsgi_app = DebuggedApplication(application.wsgi_app, True)

    application.config['PROFILE'] = True

    application.wsgi_app = ProfilerMiddleware(
        application.wsgi_app, restrictions=[30]
    )
