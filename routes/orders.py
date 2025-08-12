from core.imports import Blueprint, jwt_required, get_jwt_identity, jsonify, request
from core.extensions import db
from models.ordersModels import Order, Review, OrderItem
from models.vendorModels import Product, Store

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/api/orders', methods=['POST'])
@jwt_required()
def create_new_order():
    """
    Create a New Order
    ---
    tags:
      - Orders
    summary: Place a new order
    description: >
      Allows an authenticated customer to create a new order for products from a single store.
      Multiple products from the same store can be included in one order.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - store_id
            - items
          properties:
            store_id:
              type: integer
              example: 1
              description: ID of the store
            items:
              type: array
              description: List of products with quantities
              items:
                type: object
                properties:
                  product_id:
                    type: integer
                    example: 5
                  quantity:
                    type: integer
                    example: 2
    responses:
      201:
        description: Order created successfully
      400:
        description: Invalid input
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    store_id = data.get('store_id')
    items = data.get('items')

    if not store_id or not items:
        return jsonify({"message": "store_id and items are required"}), 400

    total_amount = 0
    for item in items:
        product = Product.query.filter_by(id=item['product_id'], store_id=store_id).first()
        if not product:
            return jsonify({"message": f"Product {item['product_id']} not found in store {store_id}"}), 400
        total_amount += float(product.price) * item['quantity']

    order = Order(
        customer_id=user_id,
        store_id=store_id,
        total_amount=total_amount
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({"message": "Order created successfully", "order_id": order.id}), 201


@orders_bp.route('/api/orders/<id>', methods=['GET'])
@jwt_required()
def get_order_details(id):
    """
    Get Order Details
    ---
    tags:
      - Orders
    summary: Retrieve a specific order by ID
    description: Returns the details of an order belonging to the authenticated user.
    parameters:
      - name: id
        in: path
        required: true
        type: integer
        example: 1
        description: Order ID
    responses:
      200:
        description: Order details
      404:
        description: Order not found
    """
    user_id = get_jwt_identity()
    order = Order.query.filter_by(id=id, customer_id=user_id).first()
    if not order:
        return jsonify({"message": "Order not found"}), 404

    return jsonify({
        "order_id": order.id,
        "store_name": order.store.store_name,
        "total_amount": float(order.total_amount),
        "status": order.status,
        "created_at": order.created_at.isoformat()
    }), 200


@orders_bp.route('/api/orders/<id>/status', methods=['PATCH'])
@jwt_required()
def update_order_status(id):
    """
    Update Order Status
    ---
    tags:
      - Orders
    summary: Change the status of an order
    description: >
      Allows the store owner (vendor) to update the order status.
      Valid statuses: pending, shipped, delivered, cancelled.
    parameters:
      - name: id
        in: path
        required: true
        type: integer
        example: 1
        description: Order ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              example: shipped
    responses:
      200:
        description: Status updated successfully
      400:
        description: Invalid status
      404:
        description: Order not found
    """
    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['pending', 'shipped', 'delivered', 'cancelled']:
        return jsonify({"message": "Invalid status"}), 400

    vendor_id = get_jwt_identity()
    order = Order.query.join(Store).filter(Order.id == id, Store.vendor_id == vendor_id).first()
    if not order:
        return jsonify({"message": "Order not found"}), 404

    order.status = new_status
    db.session.commit()

    return jsonify({"message": f"Order status updated to {new_status}"}), 200


@orders_bp.route('/api/orders/review', methods=['POST'])
@jwt_required()
def add_product_or_store_review():
    """
    Leave a Product or Store Review
    ---
    tags:
      - Orders
    summary: Post a review for a product or store
    description: >
      Allows a customer to leave a review for either a product they purchased or a store they bought from.
      The customer must have purchased the product or ordered from the store before leaving a review.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - rating
          properties:
            product_id:
              type: integer
              example: 5
              description: ID of the product being reviewed
            store_id:
              type: integer
              example: 2
              description: ID of the store being reviewed
            rating:
              type: integer
              example: 4
              description: Rating (1–5)
            comment:
              type: string
              example: "Great product, arrived quickly!"
              description: Optional review comment
    responses:
      201:
        description: Review created successfully
      400:
        description: Invalid input or not authorized
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    product_id = data.get('product_id')
    store_id = data.get('store_id')
    rating = data.get('rating')
    comment = data.get('comment', '')

    if not rating or (not product_id and not store_id):
        return jsonify({"message": "Either product_id or store_id is required, and rating must be given"}), 400

    # Validate purchase before allowing review
    if product_id:
        purchased = db.session.query(Order).join(OrderItem).filter(
            Order.customer_id == user_id,
            OrderItem.product_id == product_id
        ).first()
        if not purchased:
            return jsonify({"message": "You can only review products you have purchased"}), 403

    if store_id:
        purchased_from_store = Order.query.filter_by(customer_id=user_id, store_id=store_id).first()
        if not purchased_from_store:
            return jsonify({"message": "You can only review stores you have purchased from"}), 403

    review = Review(
        customer_id=user_id,
        product_id=product_id,
        store_id=store_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({"message": "Review submitted successfully"}), 201
