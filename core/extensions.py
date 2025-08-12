from core.imports import Bcrypt, Swagger, JWTManager, SQLAlchemy, CORS, Migrate

jwt = JWTManager()
db = SQLAlchemy()
migrate = Migrate()
swagger = Swagger()
cors = CORS()
bcrypt = Bcrypt()
