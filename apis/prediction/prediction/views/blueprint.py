from flask import Blueprint

prediction = Blueprint('prediction', __name__, url_prefix='/predict')
