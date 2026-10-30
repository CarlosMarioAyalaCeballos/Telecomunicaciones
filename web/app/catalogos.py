"""CRUD genérico para las tablas maestras: categorías, ubicaciones y proveedores."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from . import db
from .models import GRUPOS, TIPOS_UBICACION, Categoria, Proveedor, Ubicacion
from .utils import admin_required, texto

bp = Blueprint("catalogos", __name__, url_prefix="/catalogos")

# Cada campo: (nombre, etiqueta, tipo, obligatorio, opciones)
CATALOGOS = {
    "categorias": {
        "modelo": Categoria, "titulo": "Categorías", "singular": "categoría", "icono": "bi-tags",
        "campos": [
            ("nombre", "Nombre", "text", True, None),
            ("grupo", "Grupo", "select", True, GRUPOS),
            ("descripcion", "Descripción", "text", False, None),
        ],
    },
    "ubicaciones": {
        "modelo": Ubicacion, "titulo": "Ubicaciones / Sitios", "singular": "ubicación", "icono": "bi-geo-alt",
        "campos": [
            ("nombre", "Nombre del sitio", "text", True, None),
            ("tipo", "Tipo", "select", False, TIPOS_UBICACION),
            ("direccion", "Dirección", "text", False, None),
            ("ciudad", "Ciudad", "text", False, None),
            ("departamento", "Departamento", "text", False, None),
            ("latitud", "Latitud", "number", False, None),
            ("longitud", "Longitud", "number", False, None),
            ("descripcion", "Descripción", "text", False, None),
        ],
    },
    "proveedores": {
        "modelo": Proveedor, "titulo": "Proveedores", "singular": "proveedor", "icono": "bi-truck",
        "campos": [
            ("nombre", "Razón social", "text", True, None),
            ("nit", "NIT", "text", False, None),
            ("contacto", "Contacto", "text", False, None),
            ("telefono", "Teléfono", "text", False, None),
            ("email", "Correo", "email", False, None),
            ("direccion", "Dirección", "text", False, None),
        ],
    },
}


def _config(tipo):
    if tipo not in CATALOGOS:
        abort(404)
    return CATALOGOS[tipo]


def _aplicar(obj, cfg):
    errores = []
    for nombre, etiqueta, tipo, obligatorio, opciones in cfg["campos"]:
        crudo = request.form.get(nombre)
        if tipo == "number":
            valor = (crudo or "").strip().replace(",", ".") or None
            if valor is not None:
                try:
                    valor = float(valor)
                except ValueError:
                    errores.append(f"{etiqueta}: número inválido.")
                    continue
        else:
            valor = texto(crudo)
        if obligatorio and not valor:
            errores.append(f"{etiqueta} es obligatorio.")
        if opciones and valor and valor not in opciones:
            errores.append(f"{etiqueta}: opción inválida.")
        setattr(obj, nombre, valor)
    return errores


@bp.route("/<tipo>")
@admin_required
def lista(tipo):
    cfg = _config(tipo)
    modelo = cfg["modelo"]
    orden = [modelo.grupo.desc(), modelo.nombre] if modelo is Categoria else [modelo.nombre]
    registros = modelo.query.order_by(*orden).all()
    return render_template("catalogos/lista.html", tipo=tipo, cfg=cfg, registros=registros)


@bp.route("/<tipo>/nuevo", methods=["GET", "POST"])
@bp.route("/<tipo>/<int:obj_id>/editar", methods=["GET", "POST"])
@admin_required
def formulario(tipo, obj_id=None):
    cfg = _config(tipo)
    obj = db.get_or_404(cfg["modelo"], obj_id) if obj_id else cfg["modelo"]()
    if request.method == "POST":
        errores = _aplicar(obj, cfg)
        if not errores:
            try:
                db.session.add(obj)
                db.session.commit()
                flash(f"«{obj.nombre}» guardado correctamente.", "success")
                return redirect(url_for("catalogos.lista", tipo=tipo))
            except IntegrityError:
                db.session.rollback()
                errores.append(f"Ya existe un registro con el nombre «{obj.nombre}».")
        db.session.rollback()
        for msg in errores:
            flash(msg, "danger")
    return render_template("catalogos/form.html", tipo=tipo, cfg=cfg, obj=obj)


@bp.route("/<tipo>/<int:obj_id>/eliminar", methods=["POST"])
@admin_required
def eliminar(tipo, obj_id):
    cfg = _config(tipo)
    obj = db.get_or_404(cfg["modelo"], obj_id)
    if obj.equipos:
        flash(f"No se puede eliminar «{obj.nombre}»: tiene {len(obj.equipos)} equipo(s) asociado(s).", "danger")
    else:
        db.session.delete(obj)
        db.session.commit()
        flash(f"«{obj.nombre}» eliminado.", "success")
    return redirect(url_for("catalogos.lista", tipo=tipo))
