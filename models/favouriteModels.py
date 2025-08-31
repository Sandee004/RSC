from core.extensions import db
from sqlalchemy.dialects.sqlite import JSON
from core.imports import datetime

class Favourites(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('buyers.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    buyer = db.relationship('Buyers', backref='favourites')
    product = db.relationship('Products', backref='favourited_by')
