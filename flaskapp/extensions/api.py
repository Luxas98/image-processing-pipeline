import os
from flaskapp.api import Api
# Flask-Restful must be initialized _AFTER_ the SQLAlchemy extension has
# been initialized, AND after all views, models, and serializers have
# been imported. This is because the @api decorators create deferred
# registrations that depend upon said dependencies having all been
# completed before Api('api').init_app() gets called

api_route = os.environ.get('API_ROUTE')
api_version = os.environ.get('API_VERSION', 'v1')
if api_route:
    api = Api('api', prefix=f'/api/{api_version}/{api_route}')
else:
    api = Api('api', prefix=f'/api/{api_version}')
