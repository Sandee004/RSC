from core.imports import Blueprint, jwt_required, get_jwt_identity, jsonify, request, SQLAlchemyError
from core.extensions import db
from models.userModel import Buyers
from models.cartModels import Cart, CartItem
from models.vendorModels import Products
from models.orderModels import Order, OrderItem

buyer_orders = Blueprint("buyer_orders", __name__)

@buyer_orders.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    """
    Create a new order for the logged-in buyer
    ---
    tags:
      - Buyer Orders
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
            reference:
              type: string
              example: "PSK123456789"
            items:
              type: array
              description: "Optional if user has items in cart. If provided, overrides cart."
              items:
                type: object
                properties:
                  product_id:
                    type: integer
                    example: 2
                  quantity:
                    type: integer
                    example: 3
    responses:
      201:
        description: Order created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Order created successfully"
            order_id:
              type: integer
              example: 10
            total_amount:
              type: number
              example: 25000
            order_items:
              type: array
              items:
                type: object
                properties:
                  product_name:
                    type: string
                    example: "Wireless Headphones"
                  quantity:
                    type: integer
                    example: 2
                  price:
                    type: number
                    example: 12500
      400:
        description: No items in order or invalid stock
        schema:
          type: object
          properties:
            message:
              type: string
              example: "No items in order"
      404:
        description: User or product not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Product with id 99 not found"
      500:
        description: Server error during order creation
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Error creating order"
    """
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
    """
    Get all orders of the logged-in buyer
    ---
    tags:
      - Buyer Orders
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
        description: List of buyer's orders
        schema:
          type: object
          properties:
            orders:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    example: "12"
                  title:
                    type: string
                    example: "Order #12"
                  price:
                    type: number
                    example: 35000
                  status:
                    type: string
                    example: "paid"
                  date:
                    type: string
                    example: "2025-08-26 14:30"
                  items:
                    type: array
                    items:
                      type: object
                      properties:
                        product_name:
                          type: string
                          example: "Wireless Mouse"
                        quantity:
                          type: integer
                          example: 2
                        price:
                          type: number
                          example: 17500
                        business_name:
                          type: string
                          example: "Tech World"
      404:
        description: Buyer not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "User not found"
    """
    identity = get_jwt_identity()
    user_id = identity.get("id")
    user = Buyers.query.get(user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404

    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    orders_data = []

    for order in orders:
        order_items = []
        for item in order.order_items:
            vendor = item.product.vendor if item.product else None
            order_items.append({
                "product_name": item.product_name,
                "quantity": item.quantity,
                "price": item.price,
                "business_name": vendor.business_name if vendor else None
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
