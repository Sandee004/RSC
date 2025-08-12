from core.imports import Blueprint, jsonify, request
from models.vendorModels import Product, Store
from sqlalchemy import or_
from routes.vendor import get_location_from_ip

marketplace_bp = Blueprint('marketplace', __name__)

from math import radians, cos, sin, asin, sqrt

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers.
    """
    R = 6371

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Differences
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return R * c


@marketplace_bp.route('/api/marketplace/popular', methods=['GET'])
def get_popular_products():
    """
    Get Popular (Newest First) Products
    ---
    tags:
      - Marketplace
    summary: Retrieve products sorted by newest first
    description: >
      Returns all products in the marketplace sorted by creation date (newest first).
      This means products created this week appear at the top, but older products are still included.
    responses:
      200:
        description: List of products sorted by newest first
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                example: 1
              name:
                type: string
                example: Premium Coffee Beans
              price:
                type: number
                example: 19.99
              store_name:
                type: string
                example: My Awesome Store
              created_at:
                type: string
                example: 2025-08-11T12:34:56
    """
    products = (
        Product.query
        .join(Product.store)
        .order_by(Product.created_at.desc())
        .all()
    )

    results = []
    for product in products:
        results.append({
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "store_name": product.store.store_name,
            "created_at": product.created_at.isoformat()
        })

    return jsonify(results), 200


@marketplace_bp.route('/api/marketfront/search', methods=['GET'])
def search_marketfront():
    """
    Search Products and Stores
    ---
    tags:
      - Marketplace
    summary: Search for products or stores
    description: >
      This endpoint searches across both product names/descriptions and store names/descriptions.
      Returns matching products and stores in separate lists.
    parameters:
      - name: q
        in: query
        required: true
        type: string
        description: The search term
        example: coffee
    responses:
      200:
        description: Search results for products and stores
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  id: {type: integer, example: 1}
                  name: {type: string, example: Premium Coffee Beans}
                  price: {type: number, example: 19.99}
                  store_name: {type: string, example: My Awesome Store}
            stores:
              type: array
              items:
                type: object
                properties:
                  id: {type: integer, example: 2}
                  store_name: {type: string, example: My Awesome Store}
                  store_description: {type: string, example: We sell premium coffee beans.}
    """
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({"message": "Search term 'q' is required"}), 400

    # Search products
    product_results = (
        Product.query
        .join(Product.store)
        .filter(
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%")
            )
        )
        .order_by(Product.created_at.desc())
        .all()
    )

    products = []
    for product in product_results:
        products.append({
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "store_name": product.store.store_name
        })

    # Search stores
    store_results = (
        Store.query
        .filter(
            or_(
                Store.store_name.ilike(f"%{query}%"),
                Store.store_description.ilike(f"%{query}%")
            )
        )
        .order_by(Store.store_name.asc())
        .all()
    )

    stores = []
    for store in store_results:
        stores.append({
            "id": store.id,
            "store_name": store.store_name,
            "store_description": store.store_description
        })

    return jsonify({
        "products": products,
        "stores": stores
    }), 200


@marketplace_bp.route('/api/marketplace/nearby', methods=['GET'])
def get_products_nearby():
    """
    Get Nearby Products
    ---
    tags:
      - Marketplace
    summary: Retrieve products from stores near the user's location
    description: >
      This endpoint detects the user's approximate location automatically using their IP address
      and returns products from stores within a specified radius in kilometers.
      The search radius defaults to 10 km if not provided.
    parameters:
      - name: radius
        in: query
        required: false
        type: number
        default: 10
        example: 5
        description: Search radius in kilometers
    responses:
      200:
        description: List of nearby products sorted by proximity
        schema:
          type: array
          items:
            type: object
            properties:
              product_id:
                type: integer
                example: 1
              name:
                type: string
                example: Premium Coffee Beans
              price:
                type: number
                example: 19.99
              store_name:
                type: string
                example: My Awesome Store
              distance_km:
                type: number
                example: 2.35
      400:
        description: Location could not be determined
    """
    ip = request.remote_addr
    latitude, longitude = get_location_from_ip(ip)

    if not latitude or not longitude:
        return jsonify({"message": "Could not determine location"}), 400

    radius = float(request.args.get('radius', 10))

    stores = Store.query.filter(Store.latitude.isnot(None), Store.longitude.isnot(None)).all()

    nearby_products = []
    for store in stores:
        distance = haversine(latitude, longitude, store.latitude, store.longitude)
        if distance <= radius:
            for product in store.products:
                nearby_products.append({
                    "product_id": product.id,
                    "name": product.name,
                    "price": float(product.price),
                    "store_name": store.store_name,
                    "distance_km": round(distance, 2)
                })

    nearby_products.sort(key=lambda x: x["distance_km"])
    return jsonify(nearby_products), 200


@marketplace_bp.route('/api/marketplace/filters', methods=['GET'])
def filter_products():
    """
    Filter Products
    ---
    tags:
      - Marketplace
    summary: Retrieve products based on filters
    description: >
      This endpoint returns products matching the given filters.
      Filters are optional and can be combined.
    parameters:
      - name: min_price
        in: query
        required: false
        type: number
        example: 10.00
        description: Minimum price
      - name: max_price
        in: query
        required: false
        type: number
        example: 100.00
        description: Maximum price
      - name: store
        in: query
        required: false
        type: string
        example: My Awesome Store
        description: Filter products by store name
    responses:
      200:
        description: List of filtered products
        schema:
          type: array
          items:
            type: object
            properties:
              product_id:
                type: integer
                example: 1
              name:
                type: string
                example: Wireless Headphones
              price:
                type: number
                example: 59.99
              store_name:
                type: string
                example: My Awesome Store
    """
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    store_name = request.args.get('store')

    query = Product.query.join(Product.store)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if store_name:
        query = query.filter(Store.store_name.ilike(f"%{store_name}%"))

    products = query.order_by(Product.created_at.desc()).all()

    results = [
        {
            "product_id": product.id,
            "name": product.name,
            "price": float(product.price),
            "store_name": product.store.store_name
        }
        for product in products
    ]

    return jsonify(results), 200
