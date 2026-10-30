import os
from decimal import Decimal

from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///activos.db"),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads")),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        EMPRESA_NOMBRE=os.getenv("EMPRESA_NOMBRE", "Empresa de Telecomunicaciones"),
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicie sesión para continuar."
    login_manager.login_message_category = "warning"

    from .models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .equipos import bp as equipos_bp
    from .catalogos import bp as catalogos_bp
    from .usuarios import bp as usuarios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(equipos_bp)
    app.register_blueprint(catalogos_bp)
    app.register_blueprint(usuarios_bp)

    @app.template_filter("fecha")
    def fecha(valor, formato="%d/%m/%Y"):
        return valor.strftime(formato) if valor else "—"

    @app.template_filter("moneda")
    def moneda(valor):
        if valor is None:
            return "—"
        return "$ " + f"{Decimal(valor):,.0f}".replace(",", ".")

    @app.template_filter("vacio")
    def vacio(valor):
        return valor if valor not in (None, "") else "—"

    @app.context_processor
    def globales():
        return {
            "EMPRESA": app.config["EMPRESA_NOMBRE"],
            "COLOR_ESTADO": {"Operativo": "success", "En mantenimiento": "warning text-dark",
                             "En bodega": "secondary", "Dañado": "danger", "Dado de baja": "dark"},
            "COLOR_CRITICIDAD": {"Alta": "danger", "Media": "warning text-dark", "Baja": "secondary"},
        }

    @app.errorhandler(403)
    def prohibido(e):
        return render_template("errores/error.html", codigo=403,
                               mensaje="No tiene permisos para realizar esta acción."), 403

    @app.errorhandler(404)
    def no_encontrado(e):
        return render_template("errores/error.html", codigo=404,
                               mensaje="El recurso solicitado no existe."), 404

    @app.errorhandler(413)
    def muy_grande(e):
        return render_template("errores/error.html", codigo=413,
                               mensaje="El archivo supera el tamaño máximo de 5 MB."), 413

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return render_template("errores/error.html", codigo=400,
                               mensaje="La sesión del formulario expiró. Recargue la página e intente de nuevo."), 400

    return app
