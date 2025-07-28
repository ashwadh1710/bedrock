
from flask import Flask
from app.api.routes import api_bp

def create_app():
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(api_bp)

    return app