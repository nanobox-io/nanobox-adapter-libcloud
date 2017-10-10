import logging
import os
from flask import Flask
from flask_cors import CORS
from celery import Celery
from werkzeug.contrib.fixers import ProxyFix


# Create and set up celery instance
def make_celery(app):
    celery = Celery(app.import_name,
                    backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


# Instantiate Flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
CORS(app)
app.config.update(
    CELERY_BROKER_URL='redis://%s:6379' % (os.getenv('DATA_REDIS_HOST')),
    CELERY_RESULT_BACKEND='redis://%s:6379' % (os.getenv('DATA_REDIS_HOST'))
)
celery = make_celery(app)
logging.basicConfig(level=os.getenv('FLASK_LOG_LEVEL', logging.WARNING))


# Load controllers and tasks
import nanobox_libcloud.controllers
import nanobox_libcloud.tasks
