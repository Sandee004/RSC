from core.imports import Blueprint, jsonify, jwt_required, request, get_jwt_identity
from models.userModel import User
from core.extensions import db

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    """
    Get All Users
    ---
    tags:
      - Admin
    summary: Retrieve all registered users
    description: Returns a list of all users in the system, regardless of their role.
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
        description: List of all users retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              username:
                type: string
              email:
                type: string
              phone:
                type: string
              role:
                type: string
              kyc_status:
                type: string
              referral_code:
                type: string
              referred_by:
                type: string
              credits:
                type: integer
              created_at:
                type: string
                format: date-time
    """
    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append({
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
        })
    return jsonify(user_list), 200


@admin_bp.route('/api/admin/vendors', methods=['GET'])
@jwt_required()
def get_all_vendors():
    """
    Get All Vendors
    ---
    tags:
      - Admin
    summary: Retrieve all vendor accounts
    description: Returns a list of all users with the role 'vendor'.
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
        description: List of all vendors retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              username:
                type: string
              email:
                type: string
              phone:
                type: string
              role:
                type: string
              kyc_status:
                type: string
              referral_code:
                type: string
              referred_by:
                type: string
              credits:
                type: integer
              created_at:
                type: string
                format: date-time
    """
    vendors = User.query.filter(User.role.ilike("vendor")).all()
    vendor_list = []
    for vendor in vendors:
        vendor_list.append({
            "id": vendor.id,
            "username": vendor.name,
            "email": vendor.email,
            "phone": vendor.phone,
            "role": vendor.role,
            "kyc_status": vendor.kyc_status,
            "referral_code": vendor.referral_code,
            "referred_by": vendor.referred_by,
            "credits": vendor.credits,
            "created_at": vendor.created_at.isoformat()
        })
    return jsonify(vendor_list), 200


@admin_bp.route('/api/admin/kyc/<int:user_id>', methods=['PATCH'])
@jwt_required()
def update_kyc_status(user_id):
    """
    Update User KYC Status
    ---
    tags:
      - Admin
    summary: Update the KYC status of a user
    description: >
      Allows an admin to update a user's KYC status.  
      Possible values: `"unverified"`, `"rejected"`, `"accepted"`.
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
      - name: user_id
        in: path
        description: The ID of the user whose KYC status is being updated
        required: true
        schema:
          type: integer
      - in: body
        name: body
        required: true
        description: JSON body containing the new KYC status
        schema:
          type: object
          required:
            - kyc_status
          properties:
            kyc_status:
              type: string
              enum: [unverified, rejected, accepted]
              example: accepted
    responses:
      200:
        description: KYC status updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: KYC status updated successfully
            user:
              type: object
              properties:
                id:
                  type: integer
                username:
                  type: string
                kyc_status:
                  type: string
      400:
        description: Invalid KYC status
      403:
        description: Forbidden — only admins can perform this action
      404:
        description: User not found
    """
    current_user = User.query.get(get_jwt_identity())

    data = request.get_json()
    kyc_status = data.get("kyc_status")

    if kyc_status not in ["unverified", "rejected", "accepted"]:
        return jsonify({"error": "Invalid KYC status. Either rejected or accepted is permitted"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.kyc_status = kyc_status
    db.session.commit()

    return jsonify({
        "message": "KYC status updated successfully",
        "user": {
            "id": user.id,
            "name": user.name,
            "kyc_status": user.kyc_status
        }
    }), 200
