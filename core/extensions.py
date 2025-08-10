from core.imports import Bcrypt, Swagger, JWTManager, SQLAlchemy, CORS

jwt = JWTManager()
db = SQLAlchemy()
swagger = Swagger()
cors = CORS()
bcrypt = Bcrypt()
