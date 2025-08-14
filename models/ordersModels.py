from core.extensions import db
from core.imports import datetime
from sqlalchemy.dialects.sqlite import JSON

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_address = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, shipped, delivered, cancelled
    tracking_info = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Add this line
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)

    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    image = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
