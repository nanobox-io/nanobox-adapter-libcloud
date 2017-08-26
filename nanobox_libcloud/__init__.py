from flask import Flask
from flask_cors import CORS


# Instantiate Flask app
app = Flask(__name__)
CORS(app)

import nanobox_libcloud.controllers
