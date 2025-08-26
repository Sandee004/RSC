from core.imports import Blueprint, current_app, jsonify, get_jwt_identity, jwt_required, request, hashlib, hmac
from core.extensions import db
from models.orderModels import OrderItem, Order
from models.vendorModels import Products
from models.userModel import Buyers, Vendors

vendor_orders = Blueprint("vendor_orders", __name__)

def seed_demo_orders():
    buyer = Buyers.query.filter_by(email="demo@buyer.com").first()
    vendor = Vendors.query.filter_by(email="demo@vendor.com").first()

    if not buyer or not vendor:
        print("❌ Demo buyer/vendor not found. Run seed_demo_buyer() and seed_demo_vendor() first.")
        return

    # Grab vendor's active products
    products = Products.query.filter_by(vendor_id=vendor.id, status="active").all()
    if not products:
        print("❌ No active products found for demo vendor. Run seed_products() first.")
        return

    demo_orders = [
        {"reference": "DEMO_ORDER_001", "status": "pending"},
        {"reference": "DEMO_ORDER_002", "status": "shipped"},
        {"reference": "DEMO_ORDER_003", "status": "shipped"},
        {"reference": "DEMO_ORDER_004", "status": "delivered"},
    ]

    created_orders = []
    for demo in demo_orders:
        exists = Order.query.filter_by(reference=demo["reference"]).first()
        if exists:
            print(f"ℹ️ {demo['reference']} already exists.")
            continue

        # Create order for demo buyer
        new_order = Order(
            buyer_id=buyer.id,
            total_amount=0,
            status=demo["status"],
            reference=demo["reference"],
        )
        db.session.add(new_order)
        db.session.flush()  # so new_order.id is available

        total_amount = 0
        order_items = []

        # Add 1–2 products from vendor to each order
        for product in products[:2]:
            quantity = 1
            line_total = product.product_price * quantity
            total_amount += line_total

            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                product_name=product.product_name,
                quantity=quantity,
                price=product.product_price,
                status="pending"  # default
            )
            db.session.add(order_item)
            order_items.append(order_item)

        # Update total after adding items
        new_order.total_amount = total_amount
        created_orders.append(new_order)

    db.session.commit()
    print(f"✅ Created {len(created_orders)} demo orders for buyer={buyer.email}, vendor={vendor.business_name}")
    return created_orders


@vendor_orders.route('/api/vendor/orders', methods=['GET'])
@jwt_required()
def get_vendor_orders():
    """
    Get all orders that include the logged-in vendor's products
    ---
    tags:
      - Vendor Orders
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
        description: List of orders containing this vendor's products
        schema:
          type: object
          properties:
            orders:
              type: array
              items:
                type: object
                properties:
                  order_id:
                    type: integer
                    example: 12
                  buyer_id:
                    type: integer
                    example: 7
                  buyer_name:
                    type: string
                    example: "Jane Doe"
                  buyer_email:
                    type: string
                    example: "jane@example.com"
                  status:
                    type: string
                    example: "pending"
                  created_at:
                    type: string
                    example: "2025-08-26 14:30"
                  items:
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
                          example: 45000
      403:
        description: Unauthorized (only vendors can access this endpoint)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Unauthorized"
    """
    identity = get_jwt_identity()
    vendor_id = identity.get("id")
    role = identity.get("role")

    if role != "vendor":
        return jsonify({"message": "Unauthorized"}), 403

    order_items = (
        OrderItem.query
        .join(Products, OrderItem.product_id == Products.id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Products.vendor_id == vendor_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    orders_map = {}
    for item in order_items:
        order = item.order
        buyer = Buyers.query.get(order.buyer_id)
        if order.id not in orders_map:
            orders_map[order.id] = {
                "order_id": order.id,
                "buyer_id": order.buyer_id,
                "buyer_name": buyer.name if buyer else None,
                "buyer_email": buyer.email if buyer else None,
                "status": order.status,
                "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
                "items": []
            }
        orders_map[order.id]["items"].append({
            "product_name": item.product_name,
            "quantity": item.quantity,
            "price": item.price
        })

    return jsonify({"orders": list(orders_map.values())}), 200


@vendor_orders.route('/api/vendor/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_vendor_order(order_id):
    """
    Get details of a specific order for the logged-in vendor
    ---
    tags:
      - Vendor Orders
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: "JWT token as: Bearer <your_token>"
        required: true
        type: string
      - name: order_id
        in: path
        description: ID of the order to fetch
        required: true
        type: integer
    responses:
      200:
        description: Order details including vendor's items
        schema:
          type: object
          properties:
            order_id:
              type: integer
              example: 12
            buyer_id:
              type: integer
              example: 7
            buyer_name:
              type: string
              example: "Jane Doe"
            buyer_email:
              type: string
              example: "jane@example.com"
            created_at:
              type: string
              example: "2025-08-26 14:30"
            items:
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
                    example: 45000
                  status:
                    type: string
                    example: "pending"
      403:
        description: Unauthorized (only vendors can access this endpoint)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Unauthorized"
      404:
        description: Order not found or no products for this vendor
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Order not found or no products for this vendor"
    """
    identity = get_jwt_identity()
    vendor_id = identity.get("id")
    role = identity.get("role")

    if role != "vendor":
        return jsonify({"message": "Unauthorized"}), 403

    order_items = (
        OrderItem.query
        .join(Products, OrderItem.product_id == Products.id)
        .filter(OrderItem.order_id == order_id, Products.vendor_id == vendor_id)
        .all()
    )

    if not order_items:
        return jsonify({"message": "Order not found or no products for this vendor"}), 404

    order = order_items[0].order
    buyer = Buyers.query.get(order.buyer_id)

    return jsonify({
        "order_id": order.id,
        "buyer_id": order.buyer_id,
        "buyer_name": buyer.name if buyer else None,
        "buyer_email": buyer.email if buyer else None,
        "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "price": item.price,
                "status": item.status
            }
            for item in order_items
        ]
    }), 200


@vendor_orders.route('/api/vendor/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_vendor_order_item_status(order_id):
    """
    Update the status of a vendor's items in a specific order
    ---
    tags:
      - Vendor Orders
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
      - name: order_id
        in: path
        description: ID of the order to update
        required: true
        type: integer
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [pending, shipped, delivered]
              example: "shipped"
    responses:
      200:
        description: Order items status updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Vendor's order items updated to shipped"
      400:
        description: Invalid request (e.g., invalid status)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Invalid status"
      403:
        description: Unauthorized (only vendors can update their items)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Unauthorized"
      404:
        description: No order items found for this vendor
        schema:
          type: object
          properties:
            message:
              type: string
              example: "No order items found for this vendor"
    """
    identity = get_jwt_identity()
    vendor_id = identity.get("id")
    role = identity.get("role")

    if role != "vendor":
        return jsonify({"message": "Unauthorized"}), 403

    new_status = request.json.get("status")
    if new_status not in ["pending", "shipped", "delivered"]:
        return jsonify({"message": "Invalid status"}), 400

    order_items = (
        OrderItem.query
        .join(Products, OrderItem.product_id == Products.id)
        .filter(OrderItem.order_id == order_id, Products.vendor_id == vendor_id)
        .all()
    )

    if not order_items:
        return jsonify({"message": "No order items found for this vendor"}), 404

    for item in order_items:
        item.status = new_status

    db.session.commit()

    return jsonify({"message": f"Vendor's order items updated to {new_status}"}), 200


@vendor_orders.route('/api/paystack/webhook', methods=['POST'])
def paystack_webhook():
    """
    Handle Paystack webhook response after payment
    ---
    tags:
      - Payments
    consumes:
      - application/json
    parameters:
      - name: x-paystack-signature
        in: header
        description: "Paystack signature for verifying webhook authenticity"
        required: true
        type: string
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            event:
              type: string
              example: "charge.success"
            data:
              type: object
              properties:
                reference:
                  type: string
                  example: "ORDER_12345"
                amount:
                  type: integer
                  example: 250000   # Amount in kobo (₦2,500)
    responses:
      200:
        description: Webhook processed successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Order payment verified"
      400:
        description: Invalid Paystack signature
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Invalid signature"
      404:
        description: Order not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Order not found"
    """
    paystack_secret = current_app.config.get("PAYSTACK_SECRET_KEY")

    # ✅ Validate signature
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
