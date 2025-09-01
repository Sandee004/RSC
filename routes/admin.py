from core.imports import Blueprint, get_jwt_identity, jsonify, jwt_required, request, get_jwt
from models.userModel import Buyers, Vendors, Admins
from models.vendorModels import Products, Storefront
from core.extensions import db, bcrypt

admin_bp = Blueprint('admin', __name__)

def seed_admin_accounts():
    """
    Populate the Admins table with 2 default admin accounts.
    Run this only once (e.g. in Flask shell or migration script).
    """
    admins_data = [
        {
            "name": "Super Admin One",
            "email": "admin1@example.com",
            "password": "AdminPass123"
        },
        {
            "name": "Super Admin Two",
            "email": "admin2@example.com",
            "password": "AdminPass456"
        }
    ]

    for data in admins_data:
        existing = Admins.query.filter_by(email=data["email"]).first()
        if not existing:
            hashed_pw = bcrypt.generate_password_hash(data["password"]).decode('utf-8')
            new_admin = Admins(
                name=data["name"],
                email=data["email"],
                password=hashed_pw,
                role="admin"
            )
            db.session.add(new_admin)

    db.session.commit()
    print("✅ Admin accounts seeded successfully")

# =========================
# /api/admin/stats (GET)
# =========================
@admin_bp.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def get_admin_stats():
    """
    Admin: Get platform statistics
    ---
    tags:
      - Admin
    summary: Get platform statistics (Admin only)
    description: Returns counts of users, storefronts, and products.
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token in format: Bearer <your_token>'
        required: true
        type: string
        default: "Bearer "
    responses:
      200:
        description: Platform stats
        schema:
          type: object
          properties:
            users:
              type: object
              properties:
                buyers: { type: integer, example: 120 }
                vendors: { type: integer, example: 45 }
                total_accounts: { type: integer, example: 165 }
            storefronts: { type: integer, example: 30 }
            products:
              type: object
              properties:
                total: { type: integer, example: 500 }
                active: { type: integer, example: 420 }
                inactive_or_hidden: { type: integer, example: 80 }
      403:
        description: Forbidden (not admin)
        schema:
          type: object
          properties:
            error: { type: string, example: Forbidden }
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    total_buyers = Buyers.query.count()
    total_vendors = Vendors.query.count()
    total_storefronts = Storefront.query.count()
    total_products = Products.query.count()
    active_products = Products.query.filter_by(status="active", visibility=True).count()
    inactive_products = Products.query.filter(
        (Products.status != "active") | (Products.visibility == False)
    ).count()

    return jsonify({
        "users": {
            "buyers": total_buyers,
            "vendors": total_vendors,
            "total_accounts": total_buyers + total_vendors
        },
        "storefronts": total_storefronts,
        "products": {
            "total": total_products,
            "active": active_products,
            "inactive_or_hidden": inactive_products
        }
    }), 200


# =========================
# /api/admin/users (GET)
# =========================
@admin_bp.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    """
    Get all users (buyers and vendors).
    ---
    tags:
      - Admin
    summary: List all users (Admin only)
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token in format: Bearer <your_token>'
        required: true
        type: string
        default: "Bearer "
    responses:
      200:
        description: List of all users (buyers and vendors)
      403:
        description: Forbidden (not an admin)
        schema:
          type: object
          properties:
            error: { type: string, example: Forbidden }
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

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
        } for b in buyers
    ]

    vendors = Vendors.query.all()
    vendors_list = [
        {
            "id": v.id,
            "name": f"{v.firstname} {v.lastname}".strip(),
            "business_name": v.business_name,
            "kyc_status": v.kyc_status,
            "business_type": v.business_type,
            "email": v.email,
            "phone": v.phone,
            "role": "vendor",
            "referral_code": v.referral_code,
            "referred_by": v.referred_by,
            "account_type": "vendor"
        } for v in vendors
    ]

    all_users = sorted(buyers_list + vendors_list, key=lambda x: x["id"])
    return jsonify({"count": len(all_users), "users": all_users}), 200


# =========================
# DELETE /api/admin/users/<account_type>/<user_id>
# =========================
@admin_bp.route('/api/admin/users/<string:account_type>/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(account_type, user_id):
    """
    Admin: Delete a user (buyer/vendor)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token in format: Bearer <your_token>'
        required: true
        type: string
        default: "Bearer "
      - name: account_type
        in: path
        type: string
        enum: [buyer, vendor]
        required: true
        description: Type of user account
      - name: user_id
        in: path
        type: integer
        required: true
        description: The ID of the user
    responses:
      200:
        description: User deleted
        schema:
          type: object
          properties:
            message: { type: string, example: Buyer 5 deleted successfully }
      400:
        description: Invalid account type
        schema:
          type: object
          properties:
            error: { type: string, example: Invalid account type }
      403:
        description: Forbidden (not admin)
        schema:
          type: object
          properties:
            error: { type: string, example: Forbidden }
      404:
        description: User not found
        schema:
          type: object
          properties:
            error: { type: string, example: User not found }
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    model = Buyers if account_type == "buyer" else Vendors if account_type == "vendor" else None
    if not model:
        return jsonify({"error": "Invalid account type"}), 400

    user = model.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"{account_type.capitalize()} {user_id} deleted successfully"}), 200


# =========================
# GET /api/admin/users/<account_type>/<user_id>
# =========================
@admin_bp.route('/api/admin/users/<string:account_type>/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_details(account_type, user_id):
    """
    Admin: Get details of a single user (buyer/vendor).
    Includes favourites for buyers and products for vendors.
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token in format: Bearer <your_token>'
        required: true
        type: string
        default: "Bearer "
      - name: account_type
        in: path
        type: string
        enum: [buyer, vendor]
        required: true
        description: Type of user account
      - name: user_id
        in: path
        type: integer
        required: true
        description: The ID of the user
    responses:
      200:
        description: User details with related info
      403:
        description: Forbidden (not admin)
        schema:
          type: object
          properties:
            error: { type: string, example: Forbidden }
      404:
        description: User not found
        schema:
          type: object
          properties:
            error: { type: string, example: Buyer not found }
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    if account_type == "buyer":
        buyer = Buyers.query.get(user_id)
        if not buyer:
            return jsonify({"error": "Buyer not found"}), 404

        favourites = [
            {
                "id": fav.product.id,
                "product_name": fav.product.product_name,
                "product_price": fav.product.product_price,
                "description": fav.product.description,
                "images": fav.product.product_images,
                "category": fav.product.category.name if fav.product.category else None,
                "vendor": {
                    "id": fav.product.vendor.id,
                    "business_name": fav.product.vendor.business_name,
                    "email": fav.product.vendor.email
                }
            } for fav in buyer.favourites
        ]

        return jsonify({
            "id": buyer.id,
            "name": buyer.name,
            "email": buyer.email,
            "phone": buyer.phone,
            "role": buyer.role,
            "referral_code": buyer.referral_code,
            "referred_by": buyer.referred_by,
            "account_type": "buyer",
            "favourites": favourites,
            "favourites_count": len(favourites)
        }), 200

    elif account_type == "vendor":
        vendor = Vendors.query.get(user_id)
        if not vendor:
            return jsonify({"error": "Vendor not found"}), 404

        products = [
            {
                "id": p.id,
                "product_name": p.product_name,
                "product_price": p.product_price,
                "description": p.description,
                "images": p.product_images,
                "category": p.category.name if p.category else None,
                "status": p.status,
                "visibility": p.visibility
            } for p in vendor.products
        ]

        return jsonify({
            "id": vendor.id,
            "firstname": vendor.firstname,
            "lastname": vendor.lastname,
            "business_name": vendor.business_name,
            "email": vendor.email,
            "phone": vendor.phone,
            "kyc_status": vendor.kyc_status,
            "business_type": vendor.business_type,
            "referral_code": vendor.referral_code,
            "referred_by": vendor.referred_by,
            "account_type": "vendor",
            "products": products,
            "products_count": len(products)
        }), 200

    else:
        return jsonify({"error": "Invalid account type"}), 400


# =========================
# DELETE /api/admin/storefronts/<storefront_id>
# =========================
@admin_bp.route('/api/admin/storefronts/<int:storefront_id>', methods=['DELETE'])
@jwt_required()
def delete_storefront(storefront_id):
    """
    Admin: Delete a storefront
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token in format: Bearer <your_token>'
        required: true
        type: string
        default: "Bearer "
      - name: storefront_id
        in: path
        type: integer
        required: true
        description: Storefront ID to delete
    responses:
      200:
        description: Storefront deleted
        schema:
          type: object
          properties:
            message: { type: string, example: Storefront 3 deleted successfully }
      403:
        description: Forbidden (not admin)
        schema:
          type: object
          properties:
            error: { type: string, example: Forbidden }
      404:
        description: Storefront not found
        schema:
          type: object
          properties:
            error: { type: string, example: Storefront not found }
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    storefront = Storefront.query.get(storefront_id)
    if not storefront:
        return jsonify({"error": "Storefront not found"}), 404

    db.session.delete(storefront)
    db.session.commit()
    return jsonify({"message": f"Storefront {storefront_id} deleted successfully"}), 200


# =========================
# PATCH /api/admin/products/<product_id>/status
# =========================
@admin_bp.route('/api/admin/products/<int:product_id>/status', methods=['PATCH'])
@jwt_required()
def update_product_status(product_id):
    """
    Admin: Set product inactive or toggle visibility
    ---
    tags:
      - Admin
    consumes:
      - application/json
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token in format: Bearer <your_token>'
        required: true
        type: string
        default: "Bearer "
      - name: product_id
        in: path
        type: integer
        required: true
        description: Product ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [active, inactive]
              example: inactive
            visibility:
              type: boolean
              example: false
    responses:
      200:
        description: Product status updated
        schema:
          type: object
          properties:
            message: { type: string, example: Product 12 updated successfully }
            status: { type: string, example: inactive }
            visibility: { type: boolean, example: false }
      400:
        description: Invalid status
        schema:
          type: object
          properties:
            error: { type: string, example: Invalid status }
      403:
        description: Forbidden (not admin)
        schema:
          type: object
          properties:
            error: { type: string, example: Forbidden }
      404:
        description: Product not found
        schema:
          type: object
          properties:
            error: { type: string, example: Product not found }
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    product = Products.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json() or {}

    if "status" in data:
        if data["status"] not in ["active", "inactive"]:
            return jsonify({"error": "Invalid status"}), 400
        product.status = data["status"]

    if "visibility" in data:
        product.visibility = bool(data["visibility"])

    db.session.commit()
    return jsonify({
        "message": f"Product {product_id} updated successfully",
        "status": product.status,
        "visibility": product.visibility
    }), 200


# =========================
# GET /api/admin/storefronts/<storefront_id>
# =========================
@admin_bp.route('/api/admin/storefronts/<int:storefront_id>', methods=['GET'])
@jwt_required()
def get_storefront_details(storefront_id):
    """
    Admin: Get details of a single storefront (vendor info + products)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token in format: Bearer <your_token>'
        required: true
        type: string
        default: "Bearer "
      - name: storefront_id
        in: path
        type: integer
        required: true
        description: ID of the storefront
    responses:
      200:
        description: Storefront details with vendor and products
      403:
        description: Forbidden (not admin)
        schema:
          type: object
          properties:
            error: { type: string, example: Forbidden }
      404:
        description: Storefront not found
        schema:
          type: object
          properties:
            error: { type: string, example: Storefront not found }
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    sf = Storefront.query.get(storefront_id)
    if not sf:
        return jsonify({"error": "Storefront not found"}), 404

    products = [
        {
            "id": p.id,
            "product_name": p.product_name,
            "product_price": p.product_price,
            "description": p.description,
            "images": p.product_images,
            "status": p.status,
            "visibility": p.visibility,
            "category": p.category.name if p.category else None
        } for p in sf.vendor.products
    ]

    return jsonify({
        "id": sf.id,
        "business_name": sf.business_name,
        "business_banner": sf.business_banner,
        "description": sf.description,
        "established_at": sf.established_at,
        "ratings": sf.ratings,
        "vendor": {
            "id": sf.vendor.id,
            "firstname": sf.vendor.firstname,
            "lastname": sf.vendor.lastname,
            "business_name": sf.vendor.business_name,
            "email": sf.vendor.email,
            "phone": sf.vendor.phone
        },
        "products": products,
        "products_count": len(products)
    }), 200
