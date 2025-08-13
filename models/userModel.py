from core.extensions import db
from sqlalchemy.dialects.sqlite import JSON


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(200), nullable=False)

    kyc_status = db.Column(db.String(50), default="unverified")  # 'unverified', 'pending', 'verified'
    referral_code = db.Column(db.String(200), nullable=False)
    referral_stat = db.Column(db.Integer, default=0)

    orders = db.relationship('Order', backref='customer', lazy=True)
    reviews = db.relationship('Review', backref='customer', lazy=True)
