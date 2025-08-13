from core.extensions import db
from sqlalchemy.dialects.sqlite import JSON
from core.imports import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(200), nullable=False)
    kyc_status = db.Column(db.String(50), default="unverified")  # 'unverified', 'pending', 'verified'
    referral_code = db.Column(db.String(200), nullable=False)
    referred_by = db.Column(db.String(200), nullable=True)
    credits = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='customer', lazy=True)
    reviews = db.relationship('Review', backref='customer', lazy=True)
