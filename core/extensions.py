from core.imports import Bcrypt, Swagger, JWTManager, SQLAlchemy, CORS, Migrate, Mail

jwt = JWTManager()
db = SQLAlchemy()
migrate = Migrate()
swagger = Swagger()
cors = CORS()
mail = Mail()
bcrypt = Bcrypt()
