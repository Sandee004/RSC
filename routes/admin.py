from core.imports import Blueprint, get_jwt_identity, jsonify, jwt_required
from models.userModel import Buyers, Vendors

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    """
    Get all users (buyers and vendors).
    ---
    tags:
      - Admin
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
        description: List of all users (buyers and vendors)
      403:
        description: Forbidden (not an admin)
    """
    identity = get_jwt_identity()  # e.g. {"id": 1, "role": "admin"}
    
    # Fetch buyers
    buyers = Buyers.query.all()
    buyers_list = [
        {
            "id": b.id,
            "name": b.name,
            "email": b.email,
            "phone": b.phone,
            "role": b.role,
            "referral_code": b.referral_code,
            "referred_by": b.referred_by,
            
            "account_type": "buyer"
        }
        for b in buyers
    ]

    # Fetch vendors
    vendors = Vendors.query.all()
    vendors_list = [
        {
            "id": v.id,
            "firstname": v.firstname,
            "lastname": v.lastname,
            "business_name": v.business_name,
            "kyc_status": v.kyc_status,
            "business_type": v.business_type,
            "email": v.email,
            "phone": v.phone,
            "role": "vendor",
            "referral_code": v.referral_code,
            "referred_by": v.referred_by,
            "account_type": "vendor"
        }
        for v in vendors
    ]

    all_users = buyers_list + vendors_list

    return jsonify({"users": all_users}), 200
