from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import Usuario

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        usuario = Usuario.query.filter_by(username=username).first()

        if usuario is None or not usuario.check_password(password):
            flash("Usuario o contraseña incorrectos.", "danger")
        elif not usuario.activo:
            flash("El usuario está inactivo. Contacte al administrador.", "danger")
        else:
            login_user(usuario, remember=bool(request.form.get("recordar")))
            destino = request.args.get("next")
            # Solo redirecciones internas
            if not destino or urlparse(destino).netloc:
                destino = url_for("main.dashboard")
            return redirect(destino)

    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        actual = request.form.get("actual", "")
        nueva = request.form.get("nueva", "")
        confirmar = request.form.get("confirmar", "")
        if not current_user.check_password(actual):
            flash("La contraseña actual no es correcta.", "danger")
        elif len(nueva) < 6:
            flash("La nueva contraseña debe tener al menos 6 caracteres.", "danger")
        elif nueva != confirmar:
            flash("Las contraseñas no coinciden.", "danger")
        else:
            current_user.set_password(nueva)
            db.session.commit()
            flash("Contraseña actualizada.", "success")
            return redirect(url_for("auth.perfil"))
    return render_template("auth/perfil.html")
