from core.imports import Blueprint, jsonify, request, create_access_token, jwt_required, get_jwt_identity, random, string, cloudinary, os, load_dotenv
from core.config import Config
from core.extensions import db, bcrypt
from models.userModel import User
load_dotenv() 

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
      This endpoint registers a new user with a username, email, and phone number.
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
    name = data.get('username')  # store as User.name
    email = data.get('email')
    phone = data.get('phone')
    referral_code_used = data.get('referral_code')

    if not name or not email or not phone:
        return jsonify({"message": "All fields are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists. Try logging in."}), 409

    if User.query.filter_by(name=name).first():
        return jsonify({"message": "Username already exists. Please choose another."}), 409

    # Validate referral code
    referrer = None
    if referral_code_used:
        referrer = User.query.filter_by(referral_code=referral_code_used).first()
        if not referrer:
            return jsonify({"message": "Invalid referral code"}), 400

    # Generate a unique referral code
    new_referral_code = generate_referral_code()
    while User.query.filter_by(referral_code=new_referral_code).first():
        new_referral_code = generate_referral_code()

    # Create new user
    new_user = User(
        name=name,
        email=email,
        phone=phone,
        role="user",
        referral_code=new_referral_code,
        referred_by=referrer.referral_code if referrer else None
    )

    db.session.add(new_user)
    db.session.commit()

    # JWT token
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
    description: Logs in a user using their name and email, returning a JWT access token if successful.
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
            - email
          properties:
            username:
              type: string
              example: johndoe
            email:
              type: string
              example: johndoe@example.com
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
        description: Missing username or email
      401:
        description: Invalid credentials
    """
    data = request.get_json()
    name = data.get('username')
    email = data.get('email')

    if not name or not email:
        return jsonify({"message": "Username and email are required"}), 400

    # Match against existing user
    user = User.query.filter_by(name=name, email=email).first()

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "username": user.name,
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
        "username": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "kyc_status": user.kyc_status,
        "referral_code": user.referral_code,
        "referred_by": user.referred_by,
        "credits": user.credits,
        "created_at": user.created_at.isoformat()
    }
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
    description: Allows the authenticated user to update one or more details like username, email, or phone.
    consumes:
      - application/json
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
        user.name = data['username']
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

    if not updated:
        return jsonify({"message": "No fields were updated"}), 204

    db.session.commit()

    return jsonify({
        "message": "User details updated successfully",
        "user": {
            "username": user.name,
            "email": user.email,
            "phone": user.phone,
            "referral_code": user.referral_code
        }
    }), 200



@auth_bp.route('/api/user/kyc-status', methods=['GET'])
@jwt_required()
def get_kyc_status():
    """
    Get KYC Verification Status
    ---
    tags:
      - User
    summary: Retrieve the authenticated user's KYC status
    description: Returns the current KYC verification status for the logged-in user.
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
        description: Successfully retrieved the user's KYC status
        schema:
          type: object
          properties:
            id:
              type: integer
              example: 123
            kyc_status:
              type: string
              example: "verified"
      401:
        description: Unauthorized — missing or invalid JWT token
      404:
        description: User not found
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "kyc_status": user.kyc_status,
    }), 200



@auth_bp.route('/api/user/kyc', methods=['POST'])
@jwt_required()
def submit_kyc_documents():
    """
Submit KYC Documents
---
tags:
  - User
summary: Upload and submit KYC documents for verification
description: |
  Allows the authenticated user to upload KYC documents such as ID card, passport, or proof of address.
  Files are uploaded to Cloudinary, and the returned URLs are stored with the user's KYC status.
consumes:
  - multipart/form-data
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
  - in: formData
    name: id_document
    type: file
    required: true
    description: Government-issued ID (passport, driver’s license, national ID)
  - in: formData
    name: proof_of_address
    type: file
    required: false
    description: Document proving address (utility bill, bank statement)
responses:
  200:
    description: KYC documents uploaded successfully
    schema:
      type: object
      properties:
        message:
          type: string
          example: KYC documents submitted successfully
        kyc_status:
          type: string
          example: pending
        uploaded_files:
          type: object
          properties:
            id_document_url:
              type: string
              example: "https://res.cloudinary.com/demo/image/upload/v1690000000/id_card.jpg"
            proof_of_address_url:
              type: string
              example: "https://res.cloudinary.com/demo/image/upload/v1690000000/proof_address.jpg"
  400:
    description: Missing required file
  404:
    description: User not found
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    id_document = request.files.get('id_document')
    proof_of_address = request.files.get('proof_of_address')

    if not id_document:
        return jsonify({"error": "ID document is required"}), 400
    
    if not proof_of_address:
      return jsonify({"error": "Proof of address is needed"}), 400

    uploaded_files = {}

    try:
        id_upload = cloudinary.uploader.upload(id_document, folder="kyc_documents")
        uploaded_files["id_document_url"] = id_upload.get("secure_url")

        proof_upload = cloudinary.uploader.upload(proof_of_address, folder="kyc_documents")
        uploaded_files["proof_of_address_url"] = proof_upload.get("secure_url")

        user.kyc_status = "pending"
        user.id_document_url = uploaded_files.get("id_document_url")
        user.proof_of_address_url = uploaded_files.get("proof_of_address_url")

        db.session.commit()

        return jsonify({
            "message": "KYC documents submitted successfully",
            "kyc_status": user.kyc_status,
            "uploaded_files": uploaded_files
        }), 200

    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@auth_bp.route('/api/referrals', methods=['GET'])
@jwt_required()
def referral_stat():
    """
    Get Referral Statistics
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
      401:
        description: Unauthorized — missing or invalid JWT token
      404:
        description: User not found
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    referral_count = User.query.filter_by(referred_by=user.referral_code).count()

    return jsonify({
        "referral_code": user.referral_code,
        "referral_count": referral_count
    }), 200
