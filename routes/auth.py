from core.imports import Blueprint, jsonify, request, create_access_token, jwt_required, get_jwt_identity, requests, random, string, cloudinary, os, load_dotenv
from core.config import Config
from core.extensions import db, bcrypt
from models.userModel import Buyers, Vendors
load_dotenv() 

auth_bp = Blueprint('auth', __name__)


def generate_referral_code(length=8):
    """Generate a random alphanumeric referral code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_location_from_ip(ip_address):
    """
    Get state and country from IP address using ipinfo.io (or any GeoIP service).
    """
    try:
        response = requests.get(f"https://ipinfo.io/{ip_address}/json")
        if response.status_code == 200:
            data = response.json()
            return data.get("region"), data.get("country")  # state, country
    except Exception:
        pass
    return None, None

@auth_bp.route('/api/auth/signup/buyer', methods=['POST'])
def signup_buyer():
    """
    Buyer Signup
    ---
    tags:
      - Authentication
    summary: Register a new buyer account
    description: >
      This endpoint registers a new buyer with a name, email, and phone number.  
      Upon successful registration, the buyer is assigned a unique referral code.  
      If state and/or country are not provided, they will be automatically detected  
      from the user's IP address. If a referral code is provided, it will be recorded as the referrer.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Buyer registration data
        schema:
          type: object
          required:
            - name
            - email
            - phone
            - password
          properties:
            name:
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
              example: pass123
            state:
              type: string
              example: Lagos
              description: Optional. If not provided, will be determined from IP
            country:
              type: string
              example: Nigeria
              description: Optional. If not provided, will be determined from IP
            referral_code:
              type: string
              example: "ABCD1234"
              description: Optional referral code from another buyer
    responses:
      201:
        description: Buyer created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Buyer created successfully
            access_token:
              type: string
              example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
            referral_code:
              type: string
              example: XYZ789AB
              description: The referral code assigned to the new buyer
            state:
              type: string
              example: Lagos
            country:
              type: string
              example: Nigeria
      400:
        description: Missing required fields
      409:
        description: Email already exists
    """

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    referral_code_used = data.get('referral_code')

    if not name or not email or not phone or not password:
        return jsonify({"message": "All fields are required"}), 400

    if Buyers.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists. Try logging in."}), 409

    # Remember to revisit this logic
    referrer = None
    if referral_code_used:
        referrer = Buyers.query.filter_by(referral_code=referral_code_used).first()
        if not referrer:
            return jsonify({"message": "Invalid referral code"}), 400

    # Generate a unique referral code
    new_referral_code = generate_referral_code()
    while Buyers.query.filter_by(referral_code=new_referral_code).first():
        new_referral_code = generate_referral_code()

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = Buyers(
        name=name,
        email=email,
        phone=phone,
        password=hashed_password,
        role="buyer",
        referral_code=new_referral_code,
        referred_by=referrer.referral_code if referrer else None
    )

    db.session.add(new_user)
    db.session.commit()
    access_token = create_access_token(identity={"id": new_user.id, "role": "buyer"})

    return jsonify({
        "message": "User created successfully",
        "access_token": access_token,
        "referral_code": new_user.referral_code
    }), 201


@auth_bp.route('/api/auth/signup/vendor', methods=['POST'])
def signup_vendor():
    """
    Vendor Signup
    ---
    tags:
      - Authentication
    summary: Register a new vendor account
    description: >
      This endpoint registers a new vendor with personal and business details.  
      Upon successful registration, the vendor is assigned a unique referral code.  
      If state and/or country are not provided, they will be automatically detected  
      from the user's IP address. If a referral code is provided, it will be recorded as the referrer.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Vendor registration data
        schema:
          type: object
          required:
            - firstname
            - lastname
            - business_name
            - business_type
            - email
            - phone
            - password
          properties:
            firstname:
              type: string
              example: John
            lastname:
              type: string
              example: Doe
            business_name:
              type: string
              example: Doe Enterprises
            business_type:
              type: string
              example: Retail
            email:
              type: string
              example: vendor@example.com
            phone:
              type: string
              example: "08012345678"
            password:
              type: string
              example: pass123
            state:
              type: string
              example: Lagos
              description: Optional. If not provided, will be determined from IP
            country:
              type: string
              example: Nigeria
              description: Optional. If not provided, will be determined from IP
            referral_code:
              type: string
              example: "ABCD1234"
              description: Optional referral code from another vendor
    responses:
      201:
        description: Vendor created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Vendor created successfully
            access_token:
              type: string
              example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
            referral_code:
              type: string
              example: XYZ789AB
              description: The referral code assigned to the new vendor
            state:
              type: string
              example: Lagos
            country:
              type: string
              example: Nigeria
      400:
        description: Missing required fields
      409:
        description: Email already exists
    """
    data = request.get_json()
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    business_name = data.get('business_name')
    phone = data.get('phone')
    business_type = data.get('business_type')
    email = data.get('email')
    password = data.get('password')
    state = data.get("state")
    country = data.get("country")

    referral_code_used = data.get('referral_code')

    if not all([firstname, lastname, business_name, business_type, email, phone, password]):
        return jsonify({"message": "All fields except state and country are required"}), 400

    if Vendors.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists. Try logging in."}), 409

    # Remember to revisit this logic
    referrer = None
    if referral_code_used:
        referrer = Vendors.query.filter_by(referral_code=referral_code_used).first()
        if not referrer:
            return jsonify({"message": "Invalid referral code"}), 400

    if not state or not country:
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
        ip_state, ip_country = get_location_from_ip(ip_address)
        state = state or ip_state
        country = country or ip_country

    # Generate a unique referral code
    new_referral_code = generate_referral_code()
    while Vendors.query.filter_by(referral_code=new_referral_code).first():
        new_referral_code = generate_referral_code()

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = Vendors(
        firstname=firstname,
        lastname=lastname,
        business_name=business_name,
        business_type=business_type,
        email=email,
        phone=phone,
        state=state,
        country=country,
        password=hashed_password,
        referral_code=new_referral_code,
        referred_by=referrer.referral_code if referrer else None
    )

    db.session.add(new_user)
    db.session.commit()
    access_token = create_access_token(identity={"id": new_user.id, "role": "vendor"})

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
    description: Logs in a user (Buyer or Vendor) using their email and password, returning a JWT access token if successful.
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
            - email
            - password
          properties:
            email:
              type: string
              example: example@example.com
            password:
              type: string
              example: pass123
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
                email:
                  type: string
                  example: johndoe@example.com
                role:
                  type: string
                  example: buyer
      400:
        description: Missing email or password
      401:
        description: Invalid credentials
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    # Try to fnd it in eiter buyers or vendors table
    user = Buyers.query.filter_by(email=email).first()
    role = "buyer"

    if not user:
        user = Vendors.query.filter_by(email=email).first()
        role = "vendor"

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    # Generate JWT
    access_token = create_access_token(identity={"id": user.id, "role": role})

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "email": user.email,
            "role": role
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
    identity = get_jwt_identity()   # {"id": user.id, "type": "buyer" or "vendor"}
    print(identity)
    user_id = identity.get("id")
    user_type = identity.get("role")

    user_data = {}

    if user_type == "buyer":
        user = Buyers.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_data = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "referral_code": user.referral_code,
            "referred_by": user.referred_by,
        }

    elif user_type == "vendor":
        user = Vendors.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_data = {
            "id": user.id,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "business_name": user.business_name,
            "business_type": user.business_type,
            "email": user.email,
            "phone": user.phone,
            "role": "vendor",
            "kyc_status": user.kyc_status,
            "referral_code": user.referral_code,
            "referred_by": user.referred_by,
        }

    else:
        return jsonify({"error": "Invalid user type"}), 400

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
    description: Allows the authenticated user to update one or more details like name, email, or phone.
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
            name:
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
      400:
        description: No update data provided
      404:
        description: User not found
      409:
        description: Email already in use
    """
    identity = get_jwt_identity()  # {"id": ..., "type": ...}
    user_id = identity.get("id")
    user_type = identity.get("type")

    data = request.get_json()
    if not data:
        return jsonify({"message": "No data provided"}), 400

    updated = False

    if user_type == "buyer":
        user = Buyers.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        if 'name' in data and data['name']:
            user.name = data['name']
            updated = True

        if 'email' in data and data['email']:
            # check conflict across BOTH Buyers and Vendors
            email_conflict = (Buyers.query.filter(Buyers.email == data['email'], Buyers.id != user.id).first() or
                              Vendors.query.filter_by(email=data['email']).first())
            if email_conflict:
                return jsonify({"message": "Email already in use"}), 409
            user.email = data['email']
            updated = True

        if 'phone' in data and data['phone']:
            user.phone = data['phone']
            updated = True

    elif user_type == "vendor":
        user = Vendors.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        if 'firstname' in data and data['firstname']:
            user.firstname = data['firstname']
            updated = True

        if 'lastname' in data and data['lastname']:
            user.lastname = data['lastname']
            updated = True

        if 'business_name' in data and data['business_name']:
            user.business_name = data['business_name']
            updated = True

        if 'business_type' in data and data['business_type']:
            user.business_type = data['business_type']
            updated = True

        if 'email' in data and data['email']:
            # check conflict across BOTH Vendors and Buyers
            email_conflict = (Vendors.query.filter(Vendors.email == data['email'], Vendors.id != user.id).first() or
                              Buyers.query.filter_by(email=data['email']).first())
            if email_conflict:
                return jsonify({"message": "Email already in use"}), 409
            user.email = data['email']
            updated = True

        if 'phone' in data and data['phone']:
            user.phone = data['phone']
            updated = True

    else:
        return jsonify({"message": "Invalid user type"}), 400

    if not updated:
        return jsonify({"message": "No fields were updated"}), 204

    db.session.commit()

    return jsonify({
        "message": "User details updated successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            **(
                {"name": user.name, "role": user.role, "referral_code": user.referral_code}
                if user_type == "buyer"
                else {
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "business_name": user.business_name,
                    "business_type": user.business_type,
                    "referral_code": user.referral_code,
                }
            )
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
    summary: Retrieve the authenticated vendor's KYC status
    description: Returns the current KYC verification status for the logged-in vendor.
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
        description: Successfully retrieved the vendor's KYC status
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
      403:
        description: Forbidden — only vendors can access this endpoint
      404:
        description: Vendor not found
    """
    identity = get_jwt_identity()   # {"id": ..., "type": ...}
    user_id = identity.get("id")

    vendor = Vendors.query.get(user_id)
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    return jsonify({
        "id": vendor.id,
        "kyc_status": vendor.kyc_status,
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
    user = Vendors.query.get(current_user_id)

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


"""
@auth_bp.route('/api/referrals', methods=['GET'])
@jwt_required()
def referral_stat():
    ""
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
    "
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    referral_count = User.query.filter_by(referred_by=user.referral_code).count()

    return jsonify({
        "referral_code": user.referral_code,
        "referral_count": referral_count
    }), 200
"""