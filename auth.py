from flask import Flask, request, jsonify, make_response
from flask_restx import Resource, fields, Namespace
from config import DevConfig
from models import User
from exts import db
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity



auth_ns=Namespace('auth',description="A namespace for our authentication")
#model (serializer)
signup_model = auth_ns.model(
    'SignUp',
    {
        "username":fields.String(),
        "email":fields.String(),
        "password":fields.String()
    }
)

login_model = auth_ns.model(
    'Login',
    {
        "username":fields.String(),
        "password":fields.String()
    }
)


def return_response(message, status_code, data=None, username=None):
    response = {
        "message": message,
        "data": data,
        "username": username,
    }
    return make_response(jsonify(response), status_code)


@auth_ns.route('/signup')
class SignUp(Resource):
    
    
    @auth_ns.expect(signup_model)
    def post(self):
        data=request.get_json()
        
        #check if the user already exists
        username=data.get('username')
        db_user=User.query.filter_by(username=username).first()
        if db_user is not None:
            return return_response(f"User already exists", 400, username=username)
        
        new_user=User(
            username=data.get('username'),
            email=data.get('email'),
            password=generate_password_hash(data.get('password'))
        )
        
        new_user.save()
        return return_response("User created successfully", 201, username=username)

    


@auth_ns.route('/login')
class Login(Resource):
    
    @auth_ns.expect(login_model)
    def post(self):
        data=request.get_json()
        username=data.get('username')
        password=data.get('password')
        
        db_user=User.query.filter_by(username=username).first()
        
        if db_user and check_password_hash(db_user.password,password):
            access_token=create_access_token(identity=db_user.username)
            refresh_token=create_refresh_token(identity=db_user.username)
            return jsonify({"message" : "Login successful", "status_code" : "200", "data" : {"access_token": access_token, "refresh_token": refresh_token}, "username" : username})

#creates a new access taken
#it requires the refresh token that we acquire when we log in
@auth_ns.route('/refresh')
class RefreshResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
         #to access the current login user
        current_user=get_jwt_identity()
        new_access_token=create_access_token(identity=current_user)
        return return_response("Token refreshed successfully", 200, {"access_token": new_access_token}, username=current_user)
