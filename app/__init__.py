import os

from dotenv import load_dotenv
from flask import Flask

from app.extensions import csrf, db, login_manager, migrate
from config import Config


def create_app(config_class=Config):
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.billing import billing_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.inventory import inventory_bp
    from app.routes.mpesa import mpesa_bp
    from app.routes.reports import reports_bp
    from app.routes.sales import sales_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(mpesa_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(reports_bp)

    from app.services.mpesa import daraja_client

    daraja_client._app = app

    @app.context_processor
    def inject_globals():
        from flask_login import current_user

        return {"current_user": current_user}

    return app
