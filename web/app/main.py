from datetime import date, timedelta

from flask import Blueprint, Response, abort, render_template
from flask_login import login_required
from sqlalchemy import func

from . import db
from .models import ESTADOS_EQUIPO, Categoria, Equipo, Mantenimiento

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    hoy = date.today()
    limite = hoy + timedelta(days=30)

    total = db.session.scalar(db.select(func.count(Equipo.id)))
    valor_total = db.session.scalar(db.select(func.coalesce(func.sum(Equipo.valor_compra), 0)))

    por_grupo = dict(db.session.execute(
        db.select(Categoria.grupo, func.count(Equipo.id))
        .join(Equipo, Equipo.categoria_id == Categoria.id)
        .group_by(Categoria.grupo)).all())

    por_estado = dict(db.session.execute(
        db.select(Equipo.estado, func.count(Equipo.id)).group_by(Equipo.estado)).all())
    estados = [(e, por_estado.get(e, 0)) for e in ESTADOS_EQUIPO]

    por_categoria = db.session.execute(
        db.select(Categoria.nombre, func.count(Equipo.id))
        .join(Equipo, Equipo.categoria_id == Categoria.id)
        .group_by(Categoria.nombre)
        .order_by(func.count(Equipo.id).desc())).all()

    # Próximo mantenimiento programado por equipo (el último registrado manda)
    ultimo = (db.select(Mantenimiento.equipo_id, func.max(Mantenimiento.id).label("mid"))
              .group_by(Mantenimiento.equipo_id).subquery())
    proximos = db.session.scalars(
        db.select(Mantenimiento)
        .join(ultimo, Mantenimiento.id == ultimo.c.mid)
        .where(Mantenimiento.proxima_fecha.is_not(None), Mantenimiento.proxima_fecha <= limite)
        .order_by(Mantenimiento.proxima_fecha)).all()

    garantias = db.session.scalars(
        db.select(Equipo)
        .where(Equipo.garantia_hasta.between(hoy, hoy + timedelta(days=90)))
        .order_by(Equipo.garantia_hasta)).all()

    recientes = db.session.scalars(
        db.select(Equipo).order_by(Equipo.actualizado_en.desc()).limit(6)).all()

    return render_template("dashboard.html", total=total, valor_total=valor_total, por_grupo=por_grupo,
                           estados=estados, por_categoria=por_categoria,
                           proximos=proximos, garantias=garantias, recientes=recientes, hoy=hoy)


@bp.route("/uploads/<path:filename>")
@login_required
def uploads(filename):
    equipo = Equipo.query.filter_by(foto=filename).first()
    if equipo is None or not equipo.foto_datos:
        abort(404)
    # El nombre cambia con cada foto nueva, así que el navegador puede guardarla en caché
    return Response(equipo.foto_datos, mimetype=equipo.foto_mime or "image/jpeg",
                    headers={"Cache-Control": "private, max-age=604800"})
