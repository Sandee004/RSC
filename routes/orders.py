from core.imports import Blueprint, jwt_required, get_jwt_identity, jsonify, request
from core.extensions import db
from models.ordersModels import Order, Review
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
      Allows an authenticated customer to create one or more orders for products.
      Each product will create a separate order entry since orders store a single product.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - items
            - delivery_address
          properties:
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
            delivery_address:
              type: string
              example: "123 Main Street, Ikeja, Lagos, Nigeria"
    responses:
      201:
        description: Orders created successfully
      400:
        description: Invalid input
    """
    buyer_id = get_jwt_identity()
    data = request.get_json()

    items = data.get('items')
    delivery_address = data.get('delivery_address')

    if not items or not delivery_address:
        return jsonify({"message": "items and delivery_address are required"}), 400

    created_orders = []

    for item in items:
        product = Product.query.filter_by(id=item['product_id']).first()
        if not product:
            return jsonify({"message": f"Product {item['product_id']} not found"}), 400

        quantity = item.get('quantity', 1)
        total_price = float(product.price) * quantity

        order = Order(
            buyer_id=buyer_id,
            product_id=product.id,
            quantity=quantity,
            total_price=total_price,
            delivery_address=delivery_address
        )
        db.session.add(order)
        created_orders.append(order)

    db.session.commit()

    return jsonify({
        "message": "Orders created successfully",
        "order_ids": [o.id for o in created_orders]
    }), 201


@orders_bp.route('/api/orders/<int:id>', methods=['GET'])
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
    buyer_id = get_jwt_identity()
    order = Order.query.filter_by(id=id, buyer_id=buyer_id).first()
    if not order:
        return jsonify({"message": "Order not found"}), 404

    return jsonify({
        "order_id": order.id,
        "product_name": order.items[0].product.name if order.items else None,
        "quantity": order.quantity,
        "total_price": float(order.total_price),
        "status": order.status,
        "delivery_address": order.delivery_address,
        "created_at": order.created_at.isoformat()
    }), 200


@orders_bp.route('/api/orders/<int:id>/status', methods=['PATCH'])
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
    order = (
        Order.query
        .join(Product, Order.product_id == Product.id)
        .join(Store, Product.storefront_id == Store.id)
        .filter(Order.id == id, Store.vendor_id == vendor_id)
        .first()
    )

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
      Allows a customer to leave a review for a product they purchased.
      The customer must have purchased the product before leaving a review.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - rating
          properties:
            order_id:
              type: integer
              example: 10
              description: ID of the order being reviewed
            product_id:
              type: integer
              example: 5
              description: ID of the product being reviewed
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
    buyer_id = get_jwt_identity()
    data = request.get_json()

    order_id = data.get('order_id')
    product_id = data.get('product_id')
    rating = data.get('rating')
    comment = data.get('comment', '')

    if not rating or not order_id or not product_id:
        return jsonify({"message": "order_id, product_id, and rating are required"}), 400

    # Validate purchase before allowing review
    purchased = Order.query.filter_by(
        id=order_id,
        buyer_id=buyer_id,
        product_id=product_id
    ).first()

    if not purchased:
        return jsonify({"message": "You can only review products you have purchased"}), 403

    review = Review(
        order_id=order_id,
        product_id=product_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({"message": "Review submitted successfully"}), 201
