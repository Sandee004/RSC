from flask import Flask, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from core.config import Config
from core.extensions import db, jwt, swagger, cors, bcrypt
from core.models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    swagger.init_app(app)
    cors.init_app(app)
    bcrypt.init_app(app)

    return app

app = create_app()

@app.route('/api/signup', methods=['POST'])
def signup():
    """
    User Signup
    ---
    tags:
      - Authentication
    summary: Create a new user account
    description: This endpoint registers a new user with a username, email, phone, and password.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: User registration data
        schema:
          type: object
          required:
            - username
            - email
            - phone
            - password
          properties:
            username:
              type: string
              example: johndoe
            email:
              type: string
              example: johndoe@example.com
            phone:
              type: string
              example: "+2348012345678"
            password:
              type: string
              example: "securePassword123"
    responses:
      201:
        description: User created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: User created successfully
            access_token:
              type: string
              example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
      400:
        description: Missing required fields
      409:
        description: Email already exists
    """
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')

    if not username or not email or not phone or not password:
        return jsonify({"message": "All fields are required"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"message": "Email already exists. Try logging in."}), 409

    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, email=email, phone=phone, password=password_hash)
    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.id)
    return jsonify({
        "message": "User created successfully",
        "access_token": access_token
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    """
    User Login
    ---
    tags:
      - Authentication
    summary: Authenticate user and get JWT
    description: Logs in a user using their username and password, returning a JWT access token if successful.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: User login credentials
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: johndoe
            password:
              type: string
              example: "securePassword123"
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            message:
              type: string
              example: Login successful
            access_token:
              type: string
              example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
            user:
              type: object
              properties:
                username:
                  type: string
                  example: johndoe
                email:
                  type: string
                  example: johndoe@example.com
                phone:
                  type: string
                  example: "+2348012345678"
      400:
        description: Missing username or password
      401:
        description: Invalid credentials
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    username = username.lower()
    user = User.query.filter_by(username=username).first()

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
        }
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
