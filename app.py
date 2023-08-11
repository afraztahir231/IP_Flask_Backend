from flask import Flask
from flask_restx import Api, Resource
from config import DevConfig
from models import User
from exts import db
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from auth import auth_ns
from upload import upload_ns
from flask_cors import CORS


def create_app(config):
    app=Flask(__name__)

    app.config.from_object(DevConfig)
    
    CORS(app)

    db.init_app(app)

    migrate=Migrate(app,db)

    JWTManager(app)

    api=Api(app,doc='/docs')

    api.add_namespace(auth_ns)
    api.add_namespace(upload_ns)
        
    @app.shell_context_processor
    def make_shell_context():
        return {
            "db":db,
            "User":User
        }
        
    return app
        
    
