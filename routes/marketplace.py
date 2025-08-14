from core.imports import Blueprint, jsonify, request, requests
from models.vendorModels import Product, Store
from models.userModel import User
from sqlalchemy import or_
from routes.vendor import geocode_location
from math import radians, cos, sin, asin, sqrt

marketplace_bp = Blueprint('marketplace', __name__)

def get_location_from_ip(ip):
    """
    Get approximate latitude & longitude from an IP address using ip-api.com.
    Returns (latitude, longitude) or (None, None) if lookup fails.
    """
    try:
        url = f"http://ip-api.com/json/{ip}"
        res = requests.get(url, timeout=5)
        data = res.json()
        if data.get("status") == "success":
            return float(data.get("lat")), float(data.get("lon"))
    except Exception as e:
        print("IP Geolocation error:", e)
    return None, None


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth.
    All args are in decimal degrees.
    Returns distance in kilometers.
    """
    R = 6371

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return R * c


@marketplace_bp.route('/api/marketplace/popular', methods=['GET'])
def get_popular_products():
    """
    Get Popular (Newest First) Products from Verified Vendors
    ---
    tags:
      - Marketplace
    summary: Retrieve products from verified vendors sorted by newest first
    description: >
      Returns all products in the marketplace from vendors whose KYC status is 'accepted',
      sorted by creation date (newest first).
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
        .join(Store.vendor)  # join the user/vendor table
        .filter(User.kyc_status == "accepted")  # only products from accepted vendors
        .order_by(Product.created_at.desc())
        .all()
    )

    results = []
    for product in products:
        results.append({
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "store_name": product.store.name,
            "created_at": product.created_at.isoformat()
        })

    return jsonify(results), 200


from sqlalchemy import or_

@marketplace_bp.route('/api/marketfront/search', methods=['GET'])
def search_marketfront():
    """
    Search Products and Stores
    ---
    tags:
      - Marketplace
    summary: Search for products or stores from verified vendors
    description: >
      This endpoint searches across both product names/descriptions and store names/descriptions.
      Only products and stores from vendors with accepted KYC are returned.
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

    # Products from verified vendors
    product_results = (
        Product.query
        .join(Product.store)
        .join(Store.vendor)
        .filter(
            User.kyc_status == "accepted",
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%")
            )
        )
        .order_by(Product.created_at.desc())
        .all()
    )

    products = [
        {"id": p.id, "name": p.name, "price": float(p.price), "store_name": p.store.name}
        for p in product_results
    ]

    # Stores from verified vendors
    store_results = (
        Store.query
        .join(Store.vendor)
        .filter(
            User.kyc_status == "accepted",
            or_(
                Store.name.ilike(f"%{query}%"),
                Store.description.ilike(f"%{query}%")
            )
        )
        .order_by(Store.name.asc())
        .all()
    )

    stores = [
        {"id": s.id, "store_name": s.name, "store_description": s.description}
        for s in store_results
    ]

    return jsonify({"products": products, "stores": stores}), 200


@marketplace_bp.route('/api/marketplace/nearby', methods=['GET'])
def get_products_nearby():
    """
    Get Nearby Products
    ---
    tags:
      - Marketplace
    summary: Retrieve products from verified vendors near the user's location
    description: >
      Returns products from stores near the user's location.
      Only stores owned by vendors with accepted KYC are included.
    parameters:
      - name: country
        in: query
        required: false
        type: string
      - name: state
        in: query
        required: false
        type: string
      - name: city
        in: query
        required: false
        type: string
      - name: bus_stop
        in: query
        required: false
        type: string
      - name: radius
        in: query
        required: false
        type: number
        default: 10
        description: Search radius in kilometers
    responses:
      200:
        description: List of nearby products sorted by distance
    """
    radius = float(request.args.get("radius", 10))
    country = request.args.get("country")
    state = request.args.get("state")
    city = request.args.get("city")
    bus_stop = request.args.get("bus_stop")

    if all([country, state, city]):
        latitude, longitude = geocode_location(country, state, city, bus_stop)
    else:
        ip = request.remote_addr
        latitude, longitude = get_location_from_ip(ip)

    if not latitude or not longitude:
        return jsonify({"message": "Could not determine location"}), 400

    stores = (
        Store.query
        .join(Store.vendor)
        .filter(
            Store.latitude.isnot(None),
            Store.longitude.isnot(None),
            User.kyc_status == "accepted"
        )
        .all()
    )

    nearby_products = []
    for store in stores:
        distance = haversine(latitude, longitude, store.latitude, store.longitude)
        if distance <= radius:
            for product in store.products:
                nearby_products.append({
                    "product_id": product.id,
                    "name": product.name,
                    "price": float(product.price),
                    "store_name": store.name,
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
    summary: Retrieve products from verified vendors based on filters
    description: >
      Returns products matching optional filters (min/max price, store name).
      Only products from vendors with accepted KYC are included.
    parameters:
      - name: min_price
        in: query
        required: false
        type: number
        example: 10.00
      - name: max_price
        in: query
        required: false
        type: number
        example: 100.00
      - name: store
        in: query
        required: false
        type: string
        example: My Awesome Store
    responses:
      200:
        description: List of filtered products
        schema:
          type: array
          items:
            type: object
            properties:
              product_id: {type: integer, example: 1}
              name: {type: string, example: Wireless Headphones}
              price: {type: number, example: 59.99}
              store_name: {type: string, example: My Awesome Store}
    """
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    store_name = request.args.get('store')

    query = Product.query.join(Product.store).join(Store.vendor).filter(User.kyc_status == "accepted")

    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if store_name:
        query = query.filter(Store.name.ilike(f"%{store_name}%"))

    products = query.order_by(Product.created_at.desc()).all()

    results = [
        {"product_id": p.id, "name": p.name, "price": float(p.price), "store_name": p.store.name}
        for p in products
    ]

    return jsonify(results), 200
