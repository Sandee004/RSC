from flask import current_app
from core.imports import Blueprint, jsonify, get_jwt_identity, jwt_required, request
from core.extensions import db
from models.orderModels import OrderItem, Order
from models.vendorModels import Products

order_bp = Blueprint("orders", __name__)

@order_bp.route('/api/vendor/orders', methods=['GET'])
@jwt_required()
def get_vendor_orders():
    identity = get_jwt_identity()
    vendor_id = identity.get("id")
    role = identity.get("role")

    if role != "vendor":
        return jsonify({"message": "Unauthorized"}), 403

    # find order items where product belongs to this vendor
    order_items = (
        OrderItem.query
        .join(Products, OrderItem.product_id == Products.id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Products.vendor_id == vendor_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    # group items by order
    orders_map = {}
    for item in order_items:
        order = item.order
        if order.id not in orders_map:
            orders_map[order.id] = {
                "order_id": order.id,
                "buyer_id": order.user_id,
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


@order_bp.route('/api/vendor/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_vendor_order(order_id):
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

    return jsonify({
        "order_id": order.id,
        "buyer_id": order.user_id,
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


@order_bp.route('/api/vendor/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_vendor_order_item_status(order_id):
    identity = get_jwt_identity()
    vendor_id = identity.get("id")
    role = identity.get("role")

    if role != "vendor":
        return jsonify({"message": "Unauthorized"}), 403

    new_status = request.json.get("status")
    if new_status not in ["pending", "shipped", "delivered", "cancelled"]:
        return jsonify({"message": "Invalid status"}), 400

    # only update items in this order that belong to the vendor
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


import hashlib
import hmac

@order_bp.route('/api/paystack/webhook', methods=['POST'])
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
