from core.imports import Blueprint, request, jsonify, jwt_required, get_jwt_identity
from models.vendorModels import Category, Products
from models.userModel import Vendors
from core.extensions import db

vendor_bp = Blueprint('vendor', __name__)

def seed_categories():
    categories = ["Electronics", "Fashion", "Books"]
    created = []
    for name in categories:
        if not Category.query.filter_by(name=name).first():
            category = Category(name=name)
            db.session.add(category)
            created.append(name)
    db.session.commit()
    if created:
        print(f"✅ Categories created: {', '.join(created)}")
    else:
        print("ℹ️ Categories already exist.")

def seed_products():
    vendor = Vendors.query.filter_by(email="demo@vendor.com").first()
    if not vendor:
        print("❌ No demo vendor found. Run seed_demo_vendor() first.")
        return
    
    sample_products = [
        {
            "product_name": "Smartphone X10",
            "product_price": 120000,
            "description": "Latest model smartphone with AI camera.",
            "category": "Electronics",
            "images": ["https://via.placeholder.com/150"],
            "status": "active",
            "visibility": True
        },
        {
            "product_name": "Men's Sneakers",
            "product_price": 25000,
            "description": "Comfortable and stylish sneakers.",
            "category": "Fashion",
            "images": ["https://via.placeholder.com/150"],
            "status": "active",
            "visibility": True
        },
        {
            "product_name": "Python Programming",
            "product_price": 8000,
            "description": "A beginner-friendly guide to Python programming.",
            "category": "Books",
            "images": ["https://via.placeholder.com/150"],
            "status": "inactive",
            "visibility": False
        }
    ]

    for prod in sample_products:
        exists = Products.query.filter_by(product_name=prod["product_name"]).first()
        if not exists:
            category = Category.query.filter_by(name=prod["category"]).first()
            if not category:
                print(f"⚠️ Category {prod['category']} not found. Run seed_categories() first.")
                continue
            new_product = Products(
                product_name=prod["product_name"],
                product_price=prod["product_price"],
                description=prod["description"],
                product_images=prod["images"],
                category_id=category.id,
                vendor_id=vendor.id,
                status=prod["status"],
                visibility=prod["visibility"]
            )
            db.session.add(new_product)
            print(f"✅ Product added: {prod['product_name']}")
        else:
            print(f"ℹ️ Product already exists: {prod['product_name']}")
    db.session.commit()


@vendor_bp.route('/api/vendor/my-products', methods=['GET'])
@jwt_required()
def get_my_products():
    """
    Get all products for the logged-in vendor
    ---
    tags:
      - Vendor
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: "JWT token as: Bearer <your_token>"
        required: true
        type: string
    responses:
      200:
        description: List of vendor's products
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  product_name:
                    type: string
                    example: "Smartphone X10"
                  product_price:
                    type: number
                    example: 120000
                  description:
                    type: string
                    example: "Latest model smartphone with AI camera."
                  category:
                    type: string
                    example: "Electronics"
                  images:
                    type: array
                    items:
                      type: string
                    example: ["https://via.placeholder.com/150"]
                  status:
                    type: string
                    example: "active"
                  visibility:
                    type: boolean
                    example: true
                  vendor:
                    type: object
                    properties:
                      id:
                        type: integer
                        example: 5
                      business_name:
                        type: string
                        example: "Tech World"
                      email:
                        type: string
                        example: "vendor@example.com"
            count:
              type: integer
              example: 3
      401:
        description: Unauthorized (missing or invalid token)
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Unauthorized"
    """
    current_vendor_id = get_jwt_identity()

    products = Products.query.filter_by(vendor_id=current_vendor_id).order_by(Products.id.desc()).all()

    product_list = []
    for product in products:
        product_list.append({
            "id": product.id,
            "product_name": product.product_name,
            "product_price": product.product_price,
            "description": product.description,
            "category": product.category.name if product.category else None,
            "images": product.product_images,
            "status": product.status,
            "visibility": product.visibility,
            "vendor": {
                "id": product.vendor.id,
                "business_name": product.vendor.business_name,
                "email": product.vendor.email
            }
        })

    return jsonify({
        "products": product_list,
        "count": len(product_list)
    }), 200


@vendor_bp.route('/api/vendor/add-product', methods=['POST'])
@jwt_required()
def add_product():
    """
    Add a new product for the logged-in vendor
    ---
    tags:
      - Vendor
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - name: Authorization
        in: header
        description: "JWT token as: Bearer <your_token>"
        required: true
        type: string
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - product_name
            - product_price
            - description
            - category
          properties:
            product_name:
              type: string
              example: "Smartphone X10"
            product_price:
              type: number
              example: 120000
            description:
              type: string
              example: "Latest model smartphone with AI camera."
            category:
              type: string
              example: "Electronics"
            status:
              type: string
              example: "active"
            visibility:
              type: boolean
              example: true
            images:
              type: array
              items:
                type: string
              example: ["base64string1", "base64string2"]
    responses:
      201:
        description: Product added successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Product added successfully"
            product:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                product_name:
                  type: string
                  example: "Smartphone X10"
                product_price:
                  type: number
                  example: 120000
                description:
                  type: string
                  example: "Latest model smartphone with AI camera."
                category:
                  type: string
                  example: "Electronics"
                images:
                  type: array
                  items:
                    type: string
                status:
                  type: string
                  example: "active"
                visibility:
                  type: boolean
                  example: true
                vendor:
                  type: object
                  properties:
                    id:
                      type: integer
                      example: 5
                    business_name:
                      type: string
                      example: "Tech World"
                    email:
                      type: string
                      example: "vendor@example.com"
      400:
        description: Missing required fields
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Missing required fields"
      500:
        description: Image upload failed
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Image upload failed"
    """
    current_vendor_id = get_jwt_identity()  # vendor ID from JWT
    data = request.get_json()

    # Retain your fields
    product_name = data.get('product_name')
    description = data.get('description')
    category_name = data.get('category')
    status = data.get('status', 'active')         # default = active
    visibility = data.get('visibility', True)     # default = True
    base64_images = data.get('images', [])
    product_price = data.get('product_price')

    # Validate required fields
    if not all([product_name, product_price, category_name, description]):
        return jsonify({"error": "Missing required fields"}), 400

    # Upload images to Cloudinary (optional)
    uploaded_image_urls = []
    """
    for base64_str in base64_images:
        try:
            upload_response = cloudinary.uploader.upload(
                f"data:image/jpeg;base64,{base64_str}"
            )
            uploaded_image_urls.append(upload_response.get("secure_url"))
        except Exception as e:
            print("Upload error:", e)
            return jsonify({"error": "Image upload failed"}), 500
    """

    # Ensure category exists
    category = Category.query.filter_by(name=category_name).first()
    if not category:
        category = Category(name=category_name)
        db.session.add(category)
        db.session.commit()

    # Create product tied to vendor
    new_product = Products(
        product_name=product_name,
        product_price=float(product_price),
        description=description,
        product_images=uploaded_image_urls,
        category_id=category.id,
        vendor_id=current_vendor_id,   # 🔑 vendor link
        status=status,
        visibility=visibility
    )

    db.session.add(new_product)
    db.session.commit()

    return jsonify({
        "message": "Product added successfully",
        "product": {
            "id": new_product.id,
            "product_name": new_product.product_name,
            "product_price": new_product.product_price,
            "description": new_product.description,
            "category": category.name,
            "images": new_product.product_images,
            "status": new_product.status,
            "visibility": new_product.visibility,
            "vendor": {
                "id": new_product.vendor.id,
                "business_name": new_product.vendor.business_name,
                "email": new_product.vendor.email
            }
        }
    }), 201


@vendor_bp.route('/api/vendor/edit-product/<int:product_id>', methods=['PUT'])
@jwt_required()
def edit_product(product_id):
    """
    Edit a product for the logged-in vendor (partial update supported)
    ---
    tags:
      - Vendor
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - name: Authorization
        in: header
        description: "JWT token as: Bearer <your_token>"
        required: true
        type: string
      - name: product_id
        in: path
        description: ID of the product to update
        required: true
        type: integer
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            product_name:
              type: string
              example: "Smartphone X20"
            product_price:
              type: number
              example: 110000
            description:
              type: string
              example: "Updated description for the smartphone."
            category:
              type: string
              example: "Electronics"
            status:
              type: string
              example: "active"
            visibility:
              type: boolean
              example: true
            images:
              type: array
              items:
                type: string
              example: ["https://via.placeholder.com/150"]
    responses:
      200:
        description: Product updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Product updated successfully"
            product:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                product_name:
                  type: string
                  example: "Smartphone X20"
                product_price:
                  type: number
                  example: 110000
                description:
                  type: string
                  example: "Updated description for the smartphone."
                category:
                  type: string
                  example: "Electronics"
                images:
                  type: array
                  items:
                    type: string
                status:
                  type: string
                  example: "active"
                visibility:
                  type: boolean
                  example: true
                vendor:
                  type: object
                  properties:
                    id:
                      type: integer
                      example: 5
                    business_name:
                      type: string
                      example: "Tech World"
                    email:
                      type: string
                      example: "vendor@example.com"
      400:
        description: Invalid request (e.g., bad price format)
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Invalid price format"
      404:
        description: Product not found or not authorized
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Product not found or not authorized"
    """
    current_vendor_id = get_jwt_identity()
    data = request.get_json()

    # Fetch product and ensure vendor owns it
    product = Products.query.filter_by(id=product_id, vendor_id=current_vendor_id).first()
    if not product:
        return jsonify({"error": "Product not found or not authorized"}), 404

    # Update fields if provided
    if "product_name" in data:
        product.product_name = data["product_name"]

    if "product_price" in data:
        try:
            product.product_price = float(data["product_price"])
        except ValueError:
            return jsonify({"error": "Invalid price format"}), 400

    if "description" in data:
        product.description = data["description"]

    if "status" in data:
        product.status = data["status"]

    if "visibility" in data:
        product.visibility = bool(data["visibility"])

    if "images" in data:
        product.product_images = data["images"]

    if "category" in data:
        category = Category.query.filter_by(name=data["category"]).first()
        if not category:
            category = Category(name=data["category"])
            db.session.add(category)
            db.session.commit()
        product.category_id = category.id

    db.session.commit()

    return jsonify({
        "message": "Product updated successfully",
        "product": {
            "id": product.id,
            "product_name": product.product_name,
            "product_price": product.product_price,
            "description": product.description,
            "category": product.category.name,
            "images": product.product_images,
            "status": product.status,
            "visibility": product.visibility,
            "vendor": {
                "id": product.vendor.id,
                "business_name": product.vendor.business_name,
                "email": product.vendor.email
            }
        }
    }), 200
