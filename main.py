from core.imports import jsonify, text, inspect, Flask
from core.config import Config
from core.extensions import db, jwt, swagger, cors, bcrypt, migrate
from routes.auth import auth_bp, seed_demo_vendor, seed_demo_buyer
from routes.admin import admin_bp
from routes.vendor import seed_categories, seed_products, vendor_bp
from routes.marketplace import marketplace_bp
from routes.cart import cart_bp
from routes.buyerOrders import buyer_orders
from routes.vendorOrders import vendor_orders, seed_demo_orders

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    swagger.init_app(app)
    cors.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(vendor_bp)
    app.register_blueprint(marketplace_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(buyer_orders)
    app.register_blueprint(vendor_orders)

    return app

app = create_app()

@app.route('/ping')
def ping():
    return "Ping received", 200

@app.route("/view_db")
def view_db():
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        db_data = {}

        for table in tables:
            result = db.session.execute(text(f"SELECT * FROM `{table}`"))
            rows = [dict(row._mapping) for row in result]
            db_data[table] = rows

        return jsonify(db_data)
    except Exception as e:
        return jsonify({"error": str(e)})
    

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        seed_demo_vendor()
        seed_demo_buyer()
        seed_categories()
        seed_products()
        seed_demo_orders()

    app.run(debug=True)
