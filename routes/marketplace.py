from core.imports import Blueprint, jsonify
from models.vendorModels import Products

marketplace_bp = Blueprint('marketplace', __name__)

@marketplace_bp.route('/api/marketplace/popular-products', methods=['GET'])
def popular_products():
    """
    Get all popular products (active and visible)
    ---
    tags:
      - Marketplace
    responses:
      200:
        description: List of popular products
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
              example: 10
    """
    # Fetch only active & visible products
    products = Products.query.filter_by(status="active", visibility=True).order_by(Products.id.desc()).all()

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
