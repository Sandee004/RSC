from flask import request, Blueprint, jsonify, requests
from core.extensions import db
from models.vendorModels import Store, Product
from flask_jwt_extended import jwt_required, get_jwt_identity

vendor_bp = Blueprint('vendor', __name__)

def get_location_from_ip(ip):
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}")
        data = res.json()
        if data.get("status") == "success":
            return data["lat"], data["lon"]
    except Exception:
        return None, None
    return None, None

@vendor_bp.route('/api/vendor/storefront', methods=["POST"])
@jwt_required()
def set_store_info():
    """
    Create or Update Store Information
    ---
    tags:
      - Vendor
    summary: Create or update a store for the logged-in vendor
    description: >
      This endpoint creates a new store or updates the store information 
      linked to the authenticated vendor.  
      The vendor is determined from the JWT token.
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Store details
        schema:
          type: object
          required:
            - store_name
            - store_description
          properties:
            store_name:
              type: string
              example: My Awesome Store
            store_description:
              type: string
              example: We sell awesome products.
    responses:
      200:
        description: Store details updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Store details have been updated successfully
      401:
        description: Unauthorized — missing or invalid JWT token
      400:
        description: Missing required fields
    """
    vendor_id = get_jwt_identity()
    store_name = request.json.get('store_name')
    store_description = request.json.get('store_description')

    ip = request.remote_addr
    latitude, longitude = get_location_from_ip(ip)

    store_details = Store.query.filter_by(vendor_id=vendor_id).first()
    if store_details:
        store_details.store_name = store_name
        store_details.store_description = store_description
        if latitude and longitude:
            store_details.latitude = latitude
            store_details.longitude = longitude
    else:
        slug = store_name.lower().replace(" ", "-")
        store_details = Store(
            vendor_id=vendor_id,
            store_name=store_name,
            store_description=store_description,
            slug=slug,
            latitude=latitude,
            longitude=longitude
        )
        db.session.add(store_details)

    db.session.commit()
    return jsonify({"message": "Store details have been updated successfully"}), 200


@vendor_bp.route('/api/vendor/storefront/<slug>', methods=["GET"])
def get_store_info(slug):
    """
    Get Store Information by Slug
    ---
    tags:
      - Vendor
    summary: Retrieve store details using the store's slug
    description: >
      This endpoint returns the store information for a given slug.  
      Slugs are unique identifiers for stores, often generated from the store name.
    parameters:
      - name: slug
        in: path
        required: true
        type: string
        description: The unique slug of the store
        example: my-awesome-store
    responses:
      200:
        description: Store details retrieved successfully
        schema:
          type: object
          properties:
            store_name:
              type: string
              example: My Awesome Store
            store_description:
              type: string
              example: We sell awesome products.
            contact_email:
              type: string
              example: owner@example.com
      404:
        description: Store not found
    """
    store_details = Store.query.filter_by(slug=slug).first()

    if not store_details:
        return jsonify({"error": "Store not found"}), 404

    return jsonify({
        "store_name": store_details.store_name,
        "store_description": store_details.store_description,
        "contact_email": store_details.admin_email
    }), 200


@vendor_bp.route('/api/vendor/products', methods=['POST'])
@jwt_required()
def add_products_to_store():
    """
    Add a Product to the Vendor's Store
    ---
    tags:
      - Vendor
    summary: Add a new product to the logged-in vendor's store
    description: >
      This endpoint creates a new product in the store linked to the authenticated vendor.
      The vendor is determined from the JWT token.
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Product details
        schema:
          type: object
          required:
            - name
            - price
            - stock
          properties:
            name:
              type: string
              example: Premium Coffee Beans
            description:
              type: string
              example: Freshly roasted Arabica beans.
            price:
              type: number
              example: 19.99
            stock:
              type: integer
              example: 50
    responses:
      201:
        description: Product added successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Product added successfully
      401:
        description: Unauthorized — missing or invalid JWT token
      404:
        description: Store not found for vendor
    """
    vendor_id = get_jwt_identity()
    store = Store.query.filter_by(vendor_id=vendor_id).first()

    if not store:
        return jsonify({"message": "Store not found for this vendor"}), 404

    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    stock = data.get('stock', 0)

    if not name or price is None:
        return jsonify({"message": "Product name and price are required"}), 400

    product = Product(
        store_id=store.id,
        name=name,
        description=description,
        price=price,
        stock=stock
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({"message": "Product added successfully"}), 201


@vendor_bp.route('/api/vendor/products/<int:product_id>', methods=['PATCH'])
@jwt_required()
def update_product(product_id):
    """
    Update a Product
    ---
    tags:
      - Vendor
    summary: Update an existing product in the vendor's store
    description: >
      Updates product details (name, description, price, stock) for a product
      that belongs to the logged-in vendor's store.
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        required: true
        type: integer
        description: The ID of the product to update
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        description: Fields to update
        schema:
          type: object
          properties:
            name:
              type: string
              example: Updated Coffee Beans
            description:
              type: string
              example: Now even fresher and more aromatic!
            price:
              type: number
              example: 21.99
            stock:
              type: integer
              example: 40
    responses:
      200:
        description: Product updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Product updated successfully
      404:
        description: Product not found for this vendor
    """
    vendor_id = get_jwt_identity()

    store = Store.query.filter_by(vendor_id=vendor_id).first()
    if not store:
        return jsonify({"message": "Store not found"}), 404

    product = Product.query.filter_by(id=product_id, store_id=store.id).first()
    if not product:
        return jsonify({"message": "Product not found"}), 404

    data = request.get_json()

    if "name" in data:
        product.name = data["name"]
    if "description" in data:
        product.description = data["description"]
    if "price" in data:
        product.price = data["price"]
    if "stock" in data:
        product.stock = data["stock"]

    db.session.commit()

    return jsonify({"message": "Product updated successfully"}), 200


@vendor_bp.route('/api/vendor/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """
    Delete a Product
    ---
    tags:
      - Vendor
    summary: Delete a product from the vendor's store
    description: >
      Removes a product that belongs to the logged-in vendor's store.
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        required: true
        type: integer
        description: The ID of the product to delete
    responses:
      200:
        description: Product deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Product deleted successfully
      404:
        description: Product not found for this vendor
    """
    vendor_id = get_jwt_identity()

    store = Store.query.filter_by(vendor_id=vendor_id).first()
    if not store:
        return jsonify({"message": "Store not found"}), 404

    product = Product.query.filter_by(id=product_id, store_id=store.id).first()
    if not product:
        return jsonify({"message": "Product not found"}), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({"message": "Product deleted successfully"}), 200
