#text/x-generic auth.py ( Python script, UTF-8 Unicode text executable, with CRLF line terminators )
#text/x-generic auth.py ( Python script, UTF-8 Unicode text executable, with CRLF line terminators )
from core.imports import Blueprint, jsonify, request, render_template, create_access_token, jwt_required, secrets, uuid, get_jwt_identity, get_jwt, requests, random, string, cloudinary, os, load_dotenv, datetime, Message, timedelta, IntegrityError
from core.config import Config
from core.extensions import db, bcrypt, mail
import traceback
from models.userModel import Buyers, Vendors, PendingBuyer, PendingVendor, Admins, PasswordResetToken
from models.vendorModels import Storefront
from werkzeug.utils import secure_filename
from sqlalchemy import func
load_dotenv() 


auth_bp = Blueprint('auth', __name__)

UPLOAD_FOLDER = '/home/realvlcj/api.bizengo.com/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_expired_pending():
    now = datetime.utcnow()
    expired_buyers = PendingBuyer.query.filter(PendingBuyer.otp_expires_at < now).all()
    expired_vendors = PendingVendor.query.filter(PendingVendor.otp_expires_at < now).all()
    
    for record in expired_buyers + expired_vendors:
        db.session.delete(record)
    db.session.commit()

def generate_referral_code(length=8, prefix=""):
    """Generate a secure random alphanumeric referral code with optional prefix."""
    alphabet = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(alphabet) for _ in range(length))
    unique_suffix = uuid.uuid4().hex[:6].upper()  # short unique part
    return f"{prefix}{code}{unique_suffix}"

def send_email(to, subject, body):
    msg = Message(subject=subject, recipients=[to])
    msg.html = body
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

def send_otp_email(email, otp, purpose="verification"):
    # Customize content based on purpose
    if purpose == "verification":
        subject = "Your Account Verification OTP"
        message = "Welcome to Bizengo! To complete your verification, please use the code below:"
        purpose_title = "Your Verification Code"
    elif purpose == "password_reset":
        subject = "Your Password Reset OTP"
        message = "We received a request to reset your password. Use the code below to proceed:"
        purpose_title = "Password Reset Code"
    else:
        raise ValueError("Invalid OTP purpose.")

    body = render_template(
        'email.html',
        otp=otp,
        message=message,
        purpose_title=purpose_title,
        year=datetime.now().year
    )

    send_email(email, subject, body)

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

def seed_demo_vendor():
    vendor = Vendors.query.filter_by(email="demo@vendor.com").first()
    if not vendor:
        raw_password = "password123"  # demo login password
        hashed_password = bcrypt.generate_password_hash(raw_password).decode('utf-8')

        vendor = Vendors(
            firstname="John",
            lastname="Doe",
            business_name="Demo Store",
            business_type="Retail",
            email="demo@vendor.com",
            phone="08012345678",
            password=hashed_password,
            state="Lagos",
            country="Nigeria",
            referral_code="DEMO123"
        )
        db.session.add(vendor)
        db.session.commit()

        print(f"✅ Demo vendor created (email=demo@vendor.com, password={raw_password})")
    else:
        print("ℹ️ Demo vendor already exists.")
    return vendor

def seed_demo_buyer():
    buyer = Buyers.query.filter_by(email="demo@buyer.com").first()
    if not buyer:
        raw_password = "password123"
        hashed_password = bcrypt.generate_password_hash(raw_password).decode('utf-8')

        buyer = Buyers(
            name="Jane Doe",
            email="demo@buyer.com",
            phone="08087654321",
            password=hashed_password,
            state="Lagos",
            country="Nigeria",
            role="buyer",
            referral_code="BUYER123"
        )
        db.session.add(buyer)
        db.session.commit()

        print(f"✅ Demo buyer created (email=demo@buyer.com, password={raw_password})")
    else:
        print("ℹ️ Demo buyer already exists.")
    return buyer

@auth_bp.route('/api/auth/signup/buyer', methods=['POST'])
def signup_buyer():

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    state = data.get('state')
    country = data.get('country')
    password = data.get('password')
    referral_code_used = data.get('referral_code')

    if not all([name, email, phone, password]):
        return jsonify({"message": "All required fields must be filled"}), 400

    if Buyers.query.filter_by(email=email).first():
        return jsonify({"message": "Account with this email already exists"}), 409

    elif PendingBuyer.query.filter_by(email=email).first():
         return jsonify({"message": "Account is pending verification"}), 409

    # IP-based location if missing
    if not state or not country:
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
        ip_state, ip_country = get_location_from_ip(ip_address)
        state = state or ip_state
        country = country or ip_country

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    otp_code = str(random.randint(100000, 999999))
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    send_otp_email(email, otp_code)    

    pending = PendingBuyer(
        name=name,
        email=email,
        phone=phone,
        state=state,
        country=country,
        password=hashed_password,
        referral_code=referral_code_used,
        otp_code=otp_code,
        otp_expires_at=otp_expiry
    )
    db.session.add(pending)
    db.session.commit()

    return jsonify({"message": "Verification code sent to email"}), 201


@auth_bp.route('/api/auth/signup/vendor', methods=['POST'])
def signup_vendor():
    data = request.get_json()
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    business_name = data.get('business_name')
    business_type = data.get('business_type')
    email = data.get('email')
    phone = data.get('phone')
    state = data.get("state")
    country = data.get("country")
    password = data.get('password')
    referral_code_used = data.get('referral_code')

    if not all([firstname, lastname, business_name, business_type, email, phone, password]):
        return jsonify({"message": "Missing required fields"}), 400
    
    if Vendors.query.filter_by(email=email).first():
        return jsonify({"message": "Account with this email already exists"}), 409

    elif PendingVendor.query.filter_by(email=email).first():
         return jsonify({"message": "Pending verification for this email exists"}), 409

    if not state or not country:
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
        ip_state, ip_country = get_location_from_ip(ip_address)
        state = state or ip_state
        country = country or ip_country

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    otp_code = str(random.randint(100000, 999999))
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    send_otp_email(email, otp_code)

    pending = PendingVendor(
        firstname=firstname,
        lastname=lastname,
        business_name=business_name,
        business_type=business_type,
        email=email,
        phone=phone,
        state=state,
        country=country,
        password=hashed_password,
        referral_code=referral_code_used,
        otp_code=otp_code,
        otp_expires_at=otp_expiry
    )
    db.session.add(pending)
    db.session.commit()

    # TODO: send email with otp_code
    print(f"Sending OTP {otp_code} to {email}")

    return jsonify({"message": "Verification code sent to email"}), 201


@auth_bp.route('/api/auth/verify-email', methods=['POST'])
def verify_email():
    
    data = request.get_json()
    email = data.get("email")
    otp_code = data.get("otp")

    pending_buyer = PendingBuyer.query.filter_by(email=email).first()
    pending_vendor = PendingVendor.query.filter_by(email=email).first()

    if pending_buyer:
        pending = pending_buyer
        role = "buyer"
    elif pending_vendor:
        pending = pending_vendor
        role = "vendor"
    else:
        return jsonify({"message": "No pending registration found for this account"}), 404

    if datetime.utcnow() > pending.otp_expires_at:
        db.session.delete(pending)
        db.session.commit()
        return jsonify({"error": "OTP expired. Please request a new one."}), 400

    if pending.otp_code != otp_code:
        return jsonify({"message": "Invalid OTP"}), 400

    new_user = None
    if role == "buyer":
        new_user = Buyers(
            name=pending.name,
            email=pending.email,
            phone=pending.phone,
            state=pending.state,
            country=pending.country,
            password=pending.password,
            referral_code=generate_referral_code(),
            referred_by=pending.referral_code,
            role="buyer"
        )
        db.session.add(new_user)
    else:  # vendor
        new_user = Vendors(
            firstname=pending.firstname,
            lastname=pending.lastname,
            business_name=pending.business_name,
            business_type=pending.business_type,
            email=pending.email,
            phone=pending.phone,
            state=pending.state,
            country=pending.country,
            password=pending.password,
            referral_code=generate_referral_code(),
            referred_by=pending.referral_code
        )
        db.session.add(new_user)
        db.session.flush()

        new_storefront = Storefront(
            business_name=new_user.business_name,
            description="",
            established_at=datetime.utcnow(),
            vendor_id=new_user.id
        )
        db.session.add(new_storefront)

    db.session.delete(pending)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "This email address is already in use by another account."}), 409
    except Exception as e:
        db.session.rollback()
        print(f"An unexpected error occurred during email verification: {e}")
        return jsonify({"message": "An internal error occurred."}), 500

    token = create_access_token(
        identity=str(new_user.id), 
        additional_claims={"role": role}
    )
    
    return jsonify({
        "message": "Email verified successfully",
        "access_token": token,
        "role": role
    }), 200


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = None
    role = None

    # Check Admins first
    user = Admins.query.filter_by(email=email).first()
    if user:
        role = "admin"
    else:
        # Check Buyers
        user = Buyers.query.filter_by(email=email).first()
        if user:
            role = "buyer"
        else:
            # Check Vendors
            user = Vendors.query.filter_by(email=email).first()
            if user:
                role = "vendor"

    # If no user found or password mismatch
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": role}
    )

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "email": user.email,
            "role": role
        }
    }), 200
    
@auth_bp.route('/api/auth/resend-verification', methods=['POST'])
def resend_verification():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"message": "Email is required"}), 400

    pending_buyer = PendingBuyer.query.filter_by(email=email).first()
    pending_vendor = None if pending_buyer else PendingVendor.query.filter_by(email=email).first()

    if not pending_buyer and not pending_vendor:
        return jsonify({"message": "No pending account found for this email"}), 404

    otp_code = str(random.randint(100000, 999999))
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    if pending_buyer:
        pending_buyer.otp_code = otp_code
        pending_buyer.otp_expires_at = otp_expiry
        db.session.commit()
        send_otp_email(email, otp_code)

    elif pending_vendor:
        pending_vendor.otp_code = otp_code
        pending_vendor.otp_expires_at = otp_expiry
        db.session.commit()
        send_otp_email(email, otp_code)

    return jsonify({"message": "A new verification code has been sent to your email"}), 200



@auth_bp.route('/api/auth/request-password-reset', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    email = data.get("email")
    
    if not email:
        return jsonify({"message": "Email is required"}), 400
    email = email.strip().lower()

    user_exists = Buyers.query.filter(func.lower(Buyers.email) == email).first() or \
                  Vendors.query.filter(func.lower(Vendors.email) == email).first()

    if not user_exists:
        return jsonify({"message": "If an account with this email exists, a reset OTP has been sent."}), 200

    otp_code = str(random.randint(100000, 999999))
    otp_expiry = datetime.utcnow() + timedelta(minutes=360)

    reset_token = PasswordResetToken.query.filter_by(email=email).first()
    if not reset_token:
        reset_token = PasswordResetToken(email=email)
    
    reset_token.otp_code = otp_code
    reset_token.expires_at = otp_expiry
    
    db.session.add(reset_token)
    db.session.commit()

    send_otp_email(email, otp_code, purpose="password_reset")
    return jsonify({"message": "If an account with this email exists, a reset OTP has been sent."}), 200


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    new_password = data.get("new_password")
    otp_code_from_request = str(data.get("otp")) if data.get("otp") else None
    email = data.get("email")

    if not email or not otp_code_from_request or not new_password:
        return jsonify({"message": "Email, OTP, and new password are required"}), 400

    email = email.strip().lower()

    reset_token = (
        PasswordResetToken.query
        .filter(PasswordResetToken.email == email)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )

    if not reset_token or str(reset_token.otp_code) != otp_code_from_request:
        return jsonify({"message": "Invalid OTP"}), 400

    if datetime.utcnow() > reset_token.expires_at:
        db.session.delete(reset_token)
        db.session.commit()
        return jsonify({"message": "OTP expired"}), 400

    user = (
        Buyers.query.filter(Buyers.email == email).first() or
        Vendors.query.filter(Vendors.email == email).first()
    )
    if not user:
        return jsonify({"message": "Account not found"}), 404

    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.password = hashed_password

    db.session.delete(reset_token)
    db.session.commit()

    return jsonify({"message": "Password reset successful"}), 200


@auth_bp.route('/api/user/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()

    claims = get_jwt()
    user_type = claims.get("role")

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
            "state": user.state,
            "country": user.country,
            "referral_code": user.referral_code,
            "referred_by": user.referred_by,
            "profile_pic": user.profile_pic,
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
            "state": user.state,
            "country": user.country,
            "role": "vendor",
            "kyc_status": user.kyc_status,
            "referral_code": user.referral_code,
            "referred_by": user.referred_by,
            "profile_pic": user.profile_pic,
        }

    else:
        return jsonify({"error": "Invalid user type"}), 400

    return jsonify(user_data), 200


@auth_bp.route('/api/user/update-profile', methods=['PATCH'])
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
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_type = claims.get("role")

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
        # Status 204 means success but no content, which fits here.
        return jsonify({"message": "No fields were updated"}), 200 

    db.session.commit()

    return jsonify({"message": "User details updated successfully"}), 200


@auth_bp.route("/api/upload-profile-pic", methods=["POST"])
@jwt_required()
def upload_profile_pic():
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    user = None
    if role == "buyer":
        user = Buyers.query.get(user_id)
    elif role == "vendor":
        user = Vendors.query.get(user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404

    if "profile_pic" not in request.files:
        return jsonify({"message": "No image part in the request"}), 400

    file = request.files["profile_pic"]

    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        original_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{role}_{user.id}_profile.{original_ext}")
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        try:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            file.save(file_path)

            profile_pic_url = f"https://api.bizengo.com/images/{filename}"

            user.profile_pic = profile_pic_url
            db.session.commit()

            return jsonify({"profile_pic_url": profile_pic_url}), 200

        except Exception as e:
            print("File upload error:", e)
            traceback.print_exc()
            return jsonify({"message": "Failed to save image on server"}), 500

    return jsonify({"message": "File type not allowed"}), 400


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
