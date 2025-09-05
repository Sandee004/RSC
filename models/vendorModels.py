from core.extensions import db
from sqlalchemy.dialects.sqlite import JSON
from core.imports import datetime

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Products(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(150), nullable=False)
    product_price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    condition = db.Column(db.String(100), nullable=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    sold_date = db.Column(db.DateTime)

    status = db.Column(db.String(50), default="active")   # 'active', 'inactive'
    visibility = db.Column(db.Boolean, default=True)      # True = visible, False = hidden

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref='products')

    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    vendor = db.relationship('Vendors', backref='products')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProductImages(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)  # who uploaded
    image_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Products', backref='images')
    vendor = db.relationship('Vendors')


class Storefront(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(150), nullable=False)
    business_banner = db.Column(JSON, nullable=True)
    description = db.Column(db.Text, default="")
    established_at = db.Column(db.DateTime, default=datetime.utcnow)
    ratings = db.Column(db.Float, default=0.0)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), unique=True, nullable=False)

    vendor = db.relationship('Vendors', backref=db.backref('storefront', uselist=False))
