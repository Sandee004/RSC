from core.imports import Blueprint, jsonify, request, create_access_token, jwt_required, get_jwt_identity, random, string
from core.config import Config
from core.extensions import db, bcrypt
from models.userModel import User
auth_bp = Blueprint('auth', __name__)


def generate_referral_code(length=8):
    """Generate a random alphanumeric referral code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


@auth_bp.route('/api/auth/signup', methods=['POST'])
def signup():
    """
User Signup
---
tags:
  - Authentication
summary: Create a new user account
description: >
  This endpoint registers a new user with a username, email, phone, and password.
  Upon successful registration, the user is assigned a unique referral code. 
  If a referral code is provided during signup, it will be recorded as the referrer.
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
          example: example@example.com
        phone:
          type: string
          example: "08012345678"
        password:
          type: string
          example: "12345"
        referral_code:
          type: string
          example: "ABCD1234"
          description: Optional referral code from another user
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
        referral_code:
          type: string
          example: XYZ789AB
          description: The referral code assigned to the new user
  400:
    description: Missing required fields
  409:
    description: Email or username already exists
    """
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    referral_code_used = data.get('referral_code')

    if not username or not email or not phone or not password:
        return jsonify({"message": "All fields are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists. Try logging in."}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists. Please choose another."}), 409
    
    #Validate referral code
    referrer = None
    if referral_code_used:
        referrer = User.query.filter_by(referral_code=referral_code_used).first()
        if not referrer:
            return jsonify({"message": "Invalid referral code"}), 400

    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    new_referral_code = generate_referral_code()
    while User.query.filter_by(referral_code=new_referral_code).first():
        new_referral_code = generate_referral_code()

    new_user = User(
        username=username,
        email=email,
        phone=phone,
        password=password_hash,
        referral_code=new_referral_code,
    )

    db.session.add(new_user)

    # If referral code was used, update referrer's stats
    if referrer:
        try:
            referrer.referral_stat = int(referrer.referral_stat) + 1
        except ValueError:
            referrer.referral_stat = 1
        db.session.add(referrer)

    db.session.commit()
    access_token = create_access_token(identity=new_user.id)

    return jsonify({
        "message": "User created successfully",
        "access_token": access_token,
        "referral_code": new_user.referral_code
    }), 201


@auth_bp.route('/api/auth/login', methods=['POST'])
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


@auth_bp.route('/api/user/profile', methods=['GET'])
@jwt_required()
def profile():
    """
    Get current user profile
    ---
    tags:
      - User
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token as: Bearer <your_token>'
        required: true
        schema:
          type: string
          example: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6..."
    responses:
      200:
        description: User profile retrieved successfully
      404:
        description: User not found
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
    }
    print("Sent data")
    return jsonify(user_data), 200


@auth_bp.route('/api/user/profile', methods=['PATCH'])
@jwt_required()
def update_profile_details():
    """
    Partially Update User Profile Details
    ---
    tags:
      - User
    summary: Partially update the authenticated user's details
    description: Allows the authenticated user to update one or more details like username, email, phone, or password.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: At least one field is required
        schema:
          type: object
          properties:
            username:
              type: string
              example: johndoe_updated
            email:
              type: string
              example: johndoe_new@example.com
            phone:
              type: string
              example: "+2348098765432"
            password:
              type: string
              example: "newSecurePassword123"
    responses:
      200:
        description: User updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: User details updated successfully
            user:
              type: object
              properties:
                username:
                  type: string
                email:
                  type: string
                phone:
                  type: string
      400:
        description: No update data provided
      409:
        description: Email already in use
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({"message": "No data provided"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    updated = False

    if 'username' in data and data['username']:
        user.username = data['username']
        updated = True

    if 'email' in data and data['email']:
        existing_email = User.query.filter(User.email == data['email'], User.id != user.id).first()
        if existing_email:
            return jsonify({"message": "Email already in use"}), 409
        user.email = data['email']
        updated = True

    if 'phone' in data and data['phone']:
        user.phone = data['phone']
        updated = True

    if 'password' in data and data['password']:
        user.password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        updated = True

    if not updated:
        return jsonify({"message": "No fields were updated"}), 200

    db.session.commit()

    return jsonify({
        "message": "User details updated successfully",
        "user": {
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "referral_code": user.referral_code,
            "referral_stat": user.referral_stat
        }
    }), 200


@auth_bp.route('/api/user/kyc-status', methods=['GET'])
@jwt_required()
def get_kyc_status():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user_data = {
        "id": user.id,
        "kyc_status": user.kyc_status,
    }
    return jsonify(user_data), 200


@auth_bp.route('/api/user/kyc', methods=['POST'])
@jwt_required()
def seubmit_kyc_documents():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user_data = {
        "id": user.id,
    }
    return jsonify(user_data), 200


@auth_bp.route('/api/referrals', methods=['GET'])
@jwt_required()
def referral_stat():
    """
    Get Referral Statistics
    ---
    tags:
      - User
    summary: Get the number of people who have used your referral code
    description: Returns the authenticated user's referral code and how many signups have been made with it.
    responses:
      200:
        description: Referral statistics retrieved successfully
        schema:
          type: object
          properties:
            referral_code:
              type: string
              example: ABCD1234
            referral_count:
              type: integer
              example: 5
      404:
        description: User not found
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({
        "referral_code": user.referral_code,
        "referral_count": int(user.referral_stat) if user.referral_stat else 0
    }), 200

