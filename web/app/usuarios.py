from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from . import db
from .models import ROLES, Usuario
from .utils import admin_required, texto

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.route("/")
@admin_required
def lista():
    usuarios = Usuario.query.order_by(Usuario.username).all()
    return render_template("usuarios/lista.html", usuarios=usuarios)


@bp.route("/nuevo", methods=["GET", "POST"])
@bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@admin_required
def formulario(usuario_id=None):
    usuario = db.get_or_404(Usuario, usuario_id) if usuario_id else None
    if request.method == "POST":
        username = texto(request.form.get("username"))
        nombre = texto(request.form.get("nombre"))
        email = texto(request.form.get("email"))
        rol = request.form.get("rol")
        activo = bool(request.form.get("activo"))
        password = request.form.get("password", "")

        errores = []
        if not username or not nombre:
            errores.append("Usuario y nombre son obligatorios.")
        if rol not in ROLES:
            errores.append("Rol inválido.")
        if usuario is None and len(password) < 6:
            errores.append("La contraseña debe tener al menos 6 caracteres.")
        if usuario is not None and password and len(password) < 6:
            errores.append("La nueva contraseña debe tener al menos 6 caracteres.")
        if username and Usuario.query.filter(Usuario.username == username,
                                             Usuario.id != (usuario.id if usuario else 0)).first():
            errores.append(f"El usuario «{username}» ya existe.")
        if email and Usuario.query.filter(Usuario.email == email,
                                          Usuario.id != (usuario.id if usuario else 0)).first():
            errores.append(f"El correo «{email}» ya está registrado.")
        if usuario is not None and usuario.id == current_user.id and (rol != "ADMIN" or not activo):
            errores.append("No puede quitarse el rol ADMIN ni desactivar su propio usuario.")

        if errores:
            for msg in errores:
                flash(msg, "danger")
        else:
            if usuario is None:
                usuario = Usuario()
                db.session.add(usuario)
            usuario.username, usuario.nombre, usuario.email = username, nombre, email
            usuario.rol, usuario.activo = rol, activo
            if password:
                usuario.set_password(password)
            db.session.commit()
            flash(f"Usuario {username} guardado.", "success")
            return redirect(url_for("usuarios.lista"))
    return render_template("usuarios/form.html", usuario=usuario, roles=ROLES, form=request.form)


@bp.route("/<int:usuario_id>/eliminar", methods=["POST"])
@admin_required
def eliminar(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    if usuario.id == current_user.id:
        flash("No puede eliminar su propio usuario.", "danger")
    else:
        db.session.delete(usuario)
        db.session.commit()
        flash(f"Usuario {usuario.username} eliminado.", "success")
    return redirect(url_for("usuarios.lista"))
