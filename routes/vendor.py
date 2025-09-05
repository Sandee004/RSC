
#text/x-generic vendor.py ( Python script, UTF-8 Unicode text executable, with CRLF line terminators )
from core.imports import Blueprint, request, jsonify, jwt_required, get_jwt_identity, requests, base64, BytesIO, re
from models.vendorModels import Category, Products, Storefront, ProductImages
from models.userModel import Vendors
from models.orderModels import Order
from core.extensions import db
import os
import uuid
from werkzeug.utils import secure_filename
from sqlalchemy import func
from sqlalchemy.orm import joinedload
import traceback


vendor_bp = Blueprint('vendor', __name__)

UPLOAD_FOLDER = '/home/realvlcj/api.bizengo.com/images/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Checks if a filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

def upload_base64_image(img_b64, vendor_id, idx):
    # Detect prefix (optional, if sent with data:image/...;base64)
    match = re.match(r"data:image/(png|jpeg|jpg);base64,(.*)", img_b64, re.DOTALL)
    if match:
        img_format = match.group(1).lower()   # png / jpeg / jpg
        img_data = match.group(2)
    else:
        # fallback: assume jpeg if no prefix
        img_format = "jpeg"
        img_data = img_b64

    # Decode base64
    img_bytes = base64.b64decode(img_data)

    # Pick correct mimetype
    mime_type = f"image/{img_format if img_format != 'jpg' else 'jpeg'}"

    files = {
        "file": (f"product_{vendor_id}_{idx}.{img_format}", BytesIO(img_bytes), mime_type)
    }

    # Upload to external API (adjust headers/auth if needed)
    response = requests.post("https://api.bizengo.com/images", files=files)

    if response.status_code == 200:
        return response.json().get("url")
    else:
        raise Exception(f"Image upload failed: {response.text}")
    
    
@vendor_bp.route('/api/vendor/my-products', methods=['GET'])
@jwt_required()
def get_my_products():
    current_vendor_id = get_jwt_identity()

    products = Products.query.options(
        joinedload(Products.images),
        joinedload(Products.category)
    ).filter(
        Products.vendor_id == current_vendor_id,
        Products.status == 'active'
    ).order_by(Products.id.desc()).all()

    product_list = []
    for product in products:
        active_images = [img.image_url for img in product.images if not img.is_deleted]

        product_list.append({
            "product_id": product.id,
            "product_name": product.product_name,
            "product_price": product.product_price,
            "quantity": product.quantity,
            "description": product.description,
            "category": product.category.name if product.category else None,
            "images": active_images,
            "status": product.status,
            "visibility": product.visibility
        })

    return jsonify({
        "products": product_list,
        "count": len(product_list)
    }), 200
    

@vendor_bp.route('/api/vendor/add-product', methods=['POST'])
@jwt_required()
def add_product():
    vendor_id_str = get_jwt_identity()
    vendor = Vendors.query.get(vendor_id_str)
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    data = request.get_json()
    product_name = data.get('product_name')
    description = data.get('description')
    category_name = data.get('category')
    condition = data.get('condition')
    quantity = data.get('quantity')
    product_price = data.get('product_price')
    image_urls = data.get('images', [])

    if not all([product_name, product_price, quantity, category_name, description]):
        return jsonify({"error": "Missing required fields"}), 400
    
    if not image_urls or not isinstance(image_urls, list):
         return jsonify({"error": "The 'images' field must be a non-empty list of URLs"}), 400

    clean_product_name = product_name.strip()

    existing_product = Products.query.filter_by(
        vendor_id=vendor.id,
        product_name=clean_product_name
    ).first()

    if existing_product:
        return jsonify({
            "error": "Conflict: A product with this name already exists.",
            "product_id": existing_product.id
        }), 409

    try:
        category = Category.query.filter(func.lower(Category.name) == category_name.lower()).first()
        if not category:
            category = Category(name=category_name)
            db.session.add(category)

        new_product = Products(
            product_name=clean_product_name,
            product_price=int(product_price),
            quantity=int(quantity),
            description=description,
            category=category,
            condition=condition,
            vendor_id=vendor.id
        )
        db.session.add(new_product)
        
        db.session.flush()

        for url in image_urls:
            product_image = ProductImages(
                product_id=new_product.id,
                vendor_id=vendor.id,
                image_url=url
            )
            db.session.add(product_image)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": "Failed to add product to the database.", "details": str(e)}), 500

    return jsonify({
        "message": "Product added successfully",
        "product_id": new_product.id
    }), 201


@vendor_bp.route('/api/vendor/upload-file', methods=['POST'])
@jwt_required()
def upload_file():
    vendor_id_str = get_jwt_identity()
    
    uploaded_files = request.files.getlist('files')

    if not uploaded_files or all(f.filename == '' for f in uploaded_files):
        return jsonify({"error": "No files selected for upload"}), 400
    
    if len(uploaded_files) > 10:
        return jsonify({"error": "Maximum of 10 files allowed per upload."}), 400

    uploaded_urls = []
    errors = []

    for file in uploaded_files:
        if file.filename == '':
            continue

        if file and allowed_file(file.filename):
            try:
                original_ext = file.filename.rsplit('.', 1)[1].lower()
                unique_id = uuid.uuid4().hex
                filename = secure_filename(f"{vendor_id_str}_{unique_id}.{original_ext}")
                
                save_path = os.path.join(UPLOAD_FOLDER, filename)

                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                file.save(save_path)

                file_url = f"https://api.bizengo.com/images/products/{filename}"
                uploaded_urls.append(file_url)

            except Exception as e:
                errors.append(f"Could not save file '{secure_filename(file.filename)}': {str(e)}")
                traceback.print_exc()
        else:
            errors.append(f"File type not allowed for '{secure_filename(file.filename)}'")

    if not uploaded_urls and errors:
        return jsonify({"error": "All file uploads failed.", "details": errors}), 500
    
    response = {
        "message": f"Successfully uploaded {len(uploaded_urls)} of {len(uploaded_files)} files.",
        "urls": uploaded_urls
    }
    if errors:
        response["errors"] = errors
        
    return jsonify(response), 200


@vendor_bp.route('/api/vendor/edit-product/<int:product_id>', methods=['PUT'])
@jwt_required()
def edit_product(product_id):
    current_vendor_id = get_jwt_identity()
    data = request.get_json()

    product = Products.query.filter(
        Products.id == product_id,
        Products.vendor_id == int(current_vendor_id)
    ).first()

    if not product:
        return jsonify({"error": "Product not found or you are not authorized to edit it"}), 404

    try:
        if 'product_name' in data:
            product.product_name = str(data['product_name'])
        if 'product_price' in data:
            product.product_price = int(data['product_price'])
        if 'quantity' in data:
            product.quantity = int(data['quantity'])
        if 'description' in data:
            product.description = str(data['description'])
        if 'condition' in data:
            product.condition = str(data['condition'])
        if 'status' in data:
            product.status = str(data['status'])
        if 'visibility' in data:
            product.visibility = bool(data['visibility'])
        
        if 'category' in data:
            category_name = data['category']
            category = Category.query.filter(func.lower(Category.name) == category_name.lower()).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
            product.category = category

        if 'new_images' in data and isinstance(data['new_images'], list):
            new_image_urls = data['new_images']
            
            for url in new_image_urls:
                if isinstance(url, str) and url:
                    new_product_image = ProductImages(
                        product_id=product.id,
                        vendor_id=int(current_vendor_id),
                        image_url=url
                    )
                    db.session.add(new_product_image)

        db.session.commit()

    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({"error": "Invalid data format provided.", "details": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": "An internal error occurred while updating the product."}), 500

    return jsonify({"message": "Product updated successfully", "product_id": product.id}), 200


@vendor_bp.route('/api/vendor/delete-image/<int:image_id>', methods=['DELETE'])
@jwt_required()
def delete_image(image_id):
    current_vendor_id = get_jwt_identity()

    image_to_delete = ProductImages.query.filter_by(
        id=image_id, 
        vendor_id=current_vendor_id
    ).first()

    if not image_to_delete:
        return jsonify({"error": "Image not found or you do not have permission to delete it."}), 404

    image_to_delete.is_deleted = True
    db.session.commit()

    return jsonify({"message": f"Image {image_id} has been marked as deleted."}), 200


@vendor_bp.route('/api/vendor/delete-product/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """
    Soft-deletes a product by ID for the logged-in vendor
    by setting its status to 'deleted'.
    """
    current_vendor_id = get_jwt_identity()
    
    product = Products.query.filter_by(id=product_id).first()

    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product.vendor_id != int(current_vendor_id):
        return jsonify({"error": "Unauthorized: You do not own this product."}), 403

    product.status = "deleted" 
    product.visibility = False
    
    db.session.commit()
    
    return jsonify({"message": f"Product '{product.product_name}' has been deleted."}), 200


@vendor_bp.route('/api/vendor/storefront', methods=['GET'])
@jwt_required()
def get_storefront_details():
    """
    Get storefront details for the logged-in vendor
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
        description: Storefront details retrieved successfully
        schema:
          type: object
          properties:
            storefront:
              type: object
              properties:
                id:
                  type: integer
                  example: 3
                business_name:
                  type: string
                  example: "Tech World"
                description:
                  type: string
                  example: "Your one-stop shop for electronics."
                state:
                  type: string
                  example: "Lagos"
                phone:
                  type: string
                  example: "08012345678"
                country:
                  type: string
                  example: "Nigeria"
                email:
                  type: string
                  example: "vendor@example.com"
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
                  images:
                    type: array
                    items:
                      type: string
                    example: ["https://cdn.com/img1.jpg", "https://cdn.com/img2.jpg"]
                  status:
                    type: string
                    example: "active"
                  visibility:
                    type: boolean
                    example: true
                  category:
                    type: string
                    example: "Electronics"
      404:
        description: Storefront not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Storefront not found"
    """
    current_vendor_id = get_jwt_identity()

    storefront = Storefront.query.filter_by(vendor_id=current_vendor_id).first()

    if not storefront:
        return jsonify({"error": "Storefront not found"}), 404

    vendor = storefront.vendor

    products = [
        {
            "id": product.id,
            "product_name": product.product_name,
            "product_price": product.product_price,
            "description": product.description,
            "images": product.product_images,
            "status": product.status,
            "visibility": product.visibility,
            "category": product.category.name if product.category else None
        }
        for product in vendor.products
    ]

    return jsonify({
        "storefront": {
            "id": storefront.id,
            "business_name": storefront.business_name,
            "description": storefront.description,
            "state": vendor.state,
            "phone": vendor.phone,
            "country": vendor.country,
            "email": vendor.email
        },
        "products": products
    }), 200


@vendor_bp.route('/api/vendor/storefront', methods=['PUT'])
@jwt_required()
def update_storefront():
    """
    Update storefront details for the logged-in vendor
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
          properties:
            business_name:
              type: string
              example: "Tech World Updated"
            business_banner:
              type: array
              items:
                type: string
              example: ["https://cdn.com/banner1.jpg", "https://cdn.com/banner2.jpg"]
            description:
              type: string
              example: "We sell the latest gadgets and electronics."
    responses:
      200:
        description: Storefront updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Storefront updated successfully"
            storefront:
              type: object
              properties:
                id:
                  type: integer
                  example: 3
                business_name:
                  type: string
                  example: "Tech World Updated"
                business_banner:
                  type: array
                  items:
                    type: string
                  example: ["https://cdn.com/banner1.jpg"]
                description:
                  type: string
                  example: "We sell the latest gadgets and electronics."
                established_at:
                  type: string
                  example: "2025-01-10T12:00:00"
                ratings:
                  type: number
                  example: 4.5
      400:
        description: Invalid request (e.g., bad field types)
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Invalid request data"
      404:
        description: Storefront not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Storefront not found"
    """
    current_vendor_id = get_jwt_identity()
  
    storefront = Storefront.query.filter_by(vendor_id=current_vendor_id).first()
    if not storefront:
        return jsonify({"error": "Storefront not found"}), 404

    data = request.get_json()

    # Update fields only if provided
    if "business_name" in data:
        storefront.business_name = data["business_name"]
    if "business_banner" in data:
        storefront.business_banner = data["business_banner"]  # expects a list (JSON column)
    if "description" in data:
        storefront.description = data["description"]

    db.session.commit()

    return jsonify({
        "message": "Storefront updated successfully",
        "storefront": {
            "id": storefront.id,
            "business_name": storefront.business_name,
            "business_banner": storefront.business_banner,
            "description": storefront.description,
            "established_at": storefront.established_at,
            "ratings": storefront.ratings
        }
    }), 200


