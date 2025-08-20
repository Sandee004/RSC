from core.extensions import db
from sqlalchemy.dialects.sqlite import JSON
from core.imports import datetime


class Buyers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(200), nullable=False)
    referral_code = db.Column(db.String(200), nullable=False)
    referred_by = db.Column(db.String(200), nullable=True)

    state = db.Column(db.String(200))
    country = db.Column(db.String(200))


class Vendors(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(100), nullable=False)
    business_type = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(200), nullable=False)

    state = db.Column(db.String(200))
    country = db.Column(db.String(200))

    referral_code = db.Column(db.String(200), nullable=False)
    referred_by = db.Column(db.String(200), nullable=True)
    kyc_status = db.Column(db.String(50), default="unverified")  # 'unverified', 'pending', 'verified'
    