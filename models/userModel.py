from core.extensions import db
from sqlalchemy.dialects.sqlite import JSON
from core.imports import datetime


class Admins(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default="admin")  # Always 'admin'


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



class PendingBuyer(db.Model):
    __tablename__ = "pending_buyers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(255))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    referral_code = db.Column(db.String(50))
    otp_code = db.Column(db.String(6), nullable=False)
    otp_expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PendingVendor(db.Model):
    __tablename__ = "pending_vendors"
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(255), nullable=False)
    lastname = db.Column(db.String(255), nullable=False)
    business_name = db.Column(db.String(255), nullable=False)
    business_type = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    referral_code = db.Column(db.String(50))
    otp_code = db.Column(db.String(6), nullable=False)
    otp_expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
