from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flasgger import Swagger
from flask_bcrypt import Bcrypt
from flask_cors import CORS


jwt = JWTManager()
db = SQLAlchemy()
swagger = Swagger()
cors = CORS()
bcrypt = Bcrypt()
