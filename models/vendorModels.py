from core.extensions import db
from sqlalchemy.dialects.sqlite import JSON
from core.imports import datetime

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    #vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    banner = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(500), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    custom_domain = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    """
    country = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    bus_stop = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    """
    products = db.relationship('Product', backref='store', lazy=True)
    orders = db.relationship('Order', backref='store', lazy=True)
    reviews = db.relationship('Review', backref='store', lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    storefront_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    product_images = db.Column(JSON, nullable=True)
    stock = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    #store = db.relationship("Store", backref=db.backref("products", lazy=True))
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    reviews = db.relationship('Review', backref='product', lazy=True)