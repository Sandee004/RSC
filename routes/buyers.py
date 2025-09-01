from core.imports import Blueprint, jsonify, get_jwt_identity, jwt_required, request, get_jwt
from core.extensions import db
from models.vendorModels import Products, Storefront
from models.favouriteModels import Favourites


buyers_bp = Blueprint("buyers", __name__)

@buyers_bp.route('/api/marketplace/favourites/<int:product_id>', methods=['POST'])
@jwt_required()
def toggle_favourite(product_id):
    """
    Toggle product in user's favourites (add if not in favourites, remove if already there)
    ---
    tags:
      - Marketplace
    parameters:
      - name: product_id
        in: path
        type: integer
        required: true
        description: The ID of the product to toggle in favourites
    responses:
      200:
        description: Favourite status updated
      403:
        description: Not allowed
      404:
        description: Product not found
    """
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_type = claims.get("role")

    if user_type != "buyer":
        return jsonify({"error": "Only buyers can manage favourites"}), 403

    product = Products.query.filter_by(id=product_id, status="active", visibility=True).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Check if already in favourites
    fav = Favourites.query.filter_by(buyer_id=user_id, product_id=product_id).first()

    if fav:  # already favourited → remove it
        db.session.delete(fav)
        db.session.commit()
        return jsonify({
            "message": "Product removed from favourites",
            "product_id": product_id,
            "favourited": False
        }), 200
    else:  # not favourited → add it
        new_fav = Favourites(buyer_id=user_id, product_id=product_id)
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({
            "message": "Product added to favourites",
            "product_id": product_id,
            "favourited": True
        }), 200


@buyers_bp.route('/api/marketplace/favourites', methods=['GET'])
@jwt_required()
def get_favourites():
    """
    Get all favourite products for the logged-in buyer
    ---
    tags:
      - Marketplace
    responses:
      200:
        description: List of favourite products
    """
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_type = claims.get("role")

    if user_type != "buyer":
        return jsonify({"error": "Only buyers can view favourites"}), 403

    favourites = Favourites.query.filter_by(buyer_id=user_id).all()

    product_list = []
    for fav in favourites:
        product = fav.product
        product_list.append({
            "id": product.id,
            "product_name": product.product_name,
            "product_price": product.product_price,
            "description": product.description,
            "images": product.product_images,
            "category": product.category.name if product.category else None,
            "vendor": {
                "id": product.vendor.id,
                "business_name": product.vendor.business_name,
                "email": product.vendor.email
            }
        })

    return jsonify({
        "favourites": product_list,
        "count": len(product_list)
    }), 200


@buyers_bp.route('/api/admin/storefronts', methods=['GET'])
@jwt_required()
def get_storefronts():
    """
    Get all storefronts
    ---
    tags:
      - Buyers
    responses:
      200:
        description: List of storefronts with vendor info
      403:
        description: Forbidden (not admin)
    """
    claims = get_jwt_identity()
    if claims.get("role") != "admin" or claims.get("role") != "buyer":
        return jsonify({"error": "Forbidden"}), 403

    storefronts = Storefront.query.all()

    data = []
    for sf in storefronts:
        data.append({
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
            }
        })

    return jsonify({
        "count": len(data),
        "storefronts": data
    }), 200
