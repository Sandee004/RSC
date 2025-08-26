from core.imports import Blueprint, jsonify, get_jwt_identity, jwt_required, request
from core.extensions import db
from models.userModel import Buyers
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from models.vendorModels import Products
from models.orderModels import Order, OrderItem
from models.cartModels import Cart, CartItem

cart_bp = Blueprint("cart", __name__)
buyer_orders = Blueprint("buyer_orders", __name__)

@cart_bp.route('/api/cart', methods=['GET'])
@jwt_required()
def get_cart():
    """
    Get the current buyer's shopping cart
    ---
    tags:
      - Cart
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
    responses:
      200:
        description: Cart retrieved successfully
        schema:
          type: object
          properties:
            cart_items:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  title:
                    type: string
                    example: "Wireless Headphones"
                  price:
                    type: number
                    example: 7500
                  quantity:
                    type: integer
                    example: 2
                  available_stock:
                    type: integer
                    example: 20
                  category:
                    type: string
                    example: "Electronics"
                  product_images:
                    type: array
                    items:
                      type: string
                  status:
                    type: string
                    example: "active"
                  visibility:
                    type: boolean
                    example: true
      403:
        description: Unauthorized access (only buyers allowed)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Unauthorized"
      404:
        description: Buyer not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Buyer not found"
    """
    identity = get_jwt_identity()
    buyer_id = identity.get("id")
    role = identity.get("role")

    if role != "buyer":
        return jsonify({"message": "Unauthorized"}), 403

    buyer = Buyers.query.get(buyer_id)
    if not buyer:
        return jsonify({"message": "Buyer not found"}), 404

    # Get or create cart for buyer
    cart = Cart.query.filter_by(buyer_id=buyer_id).first()
    if not cart:
        return jsonify({"cart_items": []}), 200

    cart_items = []
    for item in cart.cart_items:
        product = item.product
        if product:
            cart_items.append({
                "id": product.id,
                "title": product.product_name,
                "price": product.product_price,
                "quantity": item.quantity,
                "available_stock": getattr(product, "quantity_in_stock", None),  
                "category": product.category.name if product.category else None,
                "product_images": product.product_images,
                "status": product.status,
                "visibility": product.visibility
            })

    return jsonify({"cart_items": cart_items}), 200


@cart_bp.route('/api/cart/add', methods=['POST'])
@jwt_required()
def add_to_cart():
    """
    Add a product to the buyer's cart
    ---
    tags:
      - Cart
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
            - product_id
            - quantity
          properties:
            product_id:
              type: integer
              example: 10
            quantity:
              type: integer
              example: 2
    responses:
      201:
        description: Product added to cart successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Product added to cart"
      404:
        description: Buyer or product not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Product not found"
      400:
        description: Bad request
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Invalid product ID"
    """
    data = request.get_json()
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    identity = get_jwt_identity()
    buyer_id = identity.get("id")

    buyer = Buyers.query.get(buyer_id)
    if not buyer:
        return jsonify({"message": "Buyer not found"}), 404

    product = Products.query.get(product_id)
    if not product:
        return jsonify({"message": "Product not found"}), 404

    # Get or create cart
    cart = Cart.query.filter_by(buyer_id=buyer_id).first()
    if not cart:
        cart = Cart(buyer_id=buyer_id)
        db.session.add(cart)
        db.session.commit()

    # Check if item exists already
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()

    return jsonify({"message": "Product added to cart"}), 201


@cart_bp.route('/api/cart/update/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_cart_item(item_id):
    """
    Update quantity of a cart item
    ---
    tags:
      - Cart
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
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID of the cart item to update
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - quantity
          properties:
            quantity:
              type: integer
              example: 3
    responses:
      200:
        description: Cart item updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cart item updated successfully"
      404:
        description: Cart item not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cart item not found"
    """
    identity = get_jwt_identity()
    buyer_id = identity.get("id")

    cart_item = CartItem.query.join(Cart).filter(
        CartItem.id == item_id,
        Cart.buyer_id == buyer_id
    ).first()

    if not cart_item:
        return jsonify({"message": "Cart item not found"}), 404

    data = request.get_json()
    quantity = data.get("quantity")
    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({"message": "Invalid quantity"}), 400

    cart_item.quantity = quantity
    db.session.commit()

    return jsonify({"message": "Cart item updated successfully"}), 200


@cart_bp.route('/api/cart/delete/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_cart_item(item_id):
    """
    Delete a product from the buyer's cart
    ---
    tags:
      - Cart
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: "JWT token as: Bearer <your_token>"
        required: true
        type: string
      - name: item_id
        in: path
        type: integer
        required: true
        description: ID of the cart item to delete
    responses:
      200:
        description: Cart item deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cart item deleted successfully"
      404:
        description: Cart item not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cart item not found"
    """
    identity = get_jwt_identity()
    buyer_id = identity.get("id")

    cart_item = CartItem.query.join(Cart).filter(
        CartItem.id == item_id,
        Cart.buyer_id == buyer_id
    ).first()

    if not cart_item:
        return jsonify({"message": "Cart item not found"}), 404

    db.session.delete(cart_item)
    db.session.commit()

    return jsonify({"message": "Cart item deleted successfully"}), 200


@cart_bp.route('/api/cart/clear', methods=['DELETE'])
@jwt_required()
def clear_cart():
    """
    Clear all items from the buyer's cart (e.g., after payment)
    ---
    tags:
      - Cart
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
        description: Cart cleared successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cart cleared successfully"
      404:
        description: Cart not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cart not found"
    """
    identity = get_jwt_identity()
    buyer_id = identity.get("id")

    cart = Cart.query.filter_by(buyer_id=buyer_id).first()
    if not cart:
        return jsonify({"message": "Cart not found"}), 404

    # Delete all items
    CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()

    return jsonify({"message": "Cart cleared successfully"}), 200


@buyer_orders.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    identity = get_jwt_identity()
    user_id = identity.get("id")
  
    user = Buyers.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    order_reference = data.get("reference")
    items = data.get("items", [])

    cart = Cart.query.filter_by(user_id=user_id).first()
    if not items and cart:
        items = [{'product_id': ci.product_id, 'quantity': ci.quantity} for ci in cart.cart_items]

    if not items:
        return jsonify({"message": "No items in order"}), 400

    total_amount = 0
    order_items = []

    try:
        # Create order
        new_order = Order(user_id=user_id, total_amount=0, status="pending", reference=order_reference)
        db.session.add(new_order)
        db.session.flush()

        for item in items:
            product_id = item.get("product_id")
            quantity = max(int(item.get("quantity", 1)), 1)

            product = Products.query.get(product_id)
            if not product:
                return jsonify({"message": f"Product with id {product_id} not found"}), 404

            if hasattr(product, "quantity_in_stock") and quantity > product.quantity_in_stock:
                return jsonify({"message": f"Only {product.quantity_in_stock} of '{product.product_name}' available"}), 400

            # Deduct stock if tracking inventory
            if hasattr(product, "quantity_in_stock"):
                product.quantity_in_stock -= quantity

            line_total = product.product_price * quantity
            total_amount += line_total

            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                product_name=product.product_name,
                quantity=quantity,
                price=product.product_price
            )
            db.session.add(order_item)
            order_items.append({
                "product_name": product.product_name,
                "quantity": quantity,
                "price": product.product_price
            })

        new_order.total_amount = total_amount

        # Clear cart
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete()

        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"message": "Error creating order"}), 500

    return jsonify({
        "message": "Order created successfully",
        "order_id": new_order.id,
        "total_amount": total_amount,
        "order_items": order_items
    }), 201


@buyer_orders.route('/api/orders', methods=['GET'])
@jwt_required()
def get_user_orders():
    user_id = get_jwt_identity()
    user = Buyers.query.get(user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404

    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    orders_data = []

    for order in orders:
        order_items = []
        for item in order.order_items:
            order_items.append({
                "product_name": item.product_name,
                "quantity": item.quantity,
                "price": item.price
            })
        
        orders_data.append({
            "id": str(order.id),
            "title": f"Order #{order.id}",
            "price": order.total_amount,
            "status": order.status,
            "date": order.created_at.strftime("%Y-%m-%d %H:%M"),
            "items": order_items
        })
    
    return jsonify({"orders": orders_data}), 200


@buyer_orders.route('/api/orders/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    user_id = get_jwt_identity()

    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order:
        return jsonify({"message": "Order not found"}), 404

    new_status = request.json.get('status')
    if new_status not in ['pending', 'completed', 'cancelled']:
        return jsonify({"message": "Invalid status"}), 400

    order.status = new_status
    db.session.commit()

    return jsonify({"message": "Order status updated successfully"}), 200


@buyer_orders.route('/api/orders/<int:order_id>', methods=['DELETE'])
@jwt_required()
def cancel_order(order_id):
    user_id = get_jwt_identity()

    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order:
        return jsonify({"message": "Order not found"}), 404

    if order.status == 'shipped':
        return jsonify({"message": "Cannot cancel shipped order"}), 400

    order.status = 'cancelled'
    db.session.commit()

    return jsonify({"message": "Order cancelled successfully"}), 200


import hashlib
import hmac

@buyer_orders.route('/api/paystack/webhook', methods=['POST'])
def paystack_webhook():
    """
    Handle Paystack webhook response after payment
    """
    paystack_secret = current_app.config.get("PAYSTACK_SECRET_KEY")

    # Validate signature
    signature = request.headers.get("x-paystack-signature")
    payload = request.get_data()
    expected_signature = hmac.new(
        paystack_secret.encode("utf-8"),
        payload,
        hashlib.sha512
    ).hexdigest()

    if signature != expected_signature:
        return jsonify({"message": "Invalid signature"}), 400

    event = request.json
    if event and event.get("event") == "charge.success":
        data = event.get("data", {})
        reference = data.get("reference")
        amount = data.get("amount") / 100  # Paystack sends kobo

        # ✅ Find the order with this reference
        order = Order.query.filter_by(reference=reference).first()
        if not order:
            return jsonify({"message": "Order not found"}), 404

        # ✅ Mark order as paid
        order.status = "paid"
        order.total_amount = amount
        db.session.commit()

        return jsonify({"message": "Order payment verified"}), 200

    return jsonify({"message": "Unhandled event"}), 200
