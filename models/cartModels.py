from core.extensions import db

class Cart(db.Model):
    __tablename__ = "cart"
    
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('buyers.id'), nullable=False)
    buyer = db.relationship("Buyers", backref=db.backref("cart", uselist=False))  
    
    cart_items = db.relationship("CartItem", backref="cart", cascade="all, delete-orphan")


class CartItem(db.Model):
    __tablename__ = "cart_item"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product = db.relationship("Products")

    quantity = db.Column(db.Integer, default=1, nullable=False)
