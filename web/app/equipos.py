import csv
import io
import os
import uuid

from flask import (Blueprint, Response, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import or_

from . import db
from .models import (CRITICIDADES, ESTADOS_EQUIPO, GRUPOS, TIPOS_MANTENIMIENTO, Categoria,
                     Equipo, Historial, Mantenimiento, Proveedor, Ubicacion)
from .pdf import generar_hoja_vida
from .utils import a_decimal, a_entero, a_fecha, admin_required, comprimir_imagen, texto

bp = Blueprint("equipos", __name__, url_prefix="/equipos")

EXTENSIONES_FOTO = {"png", "jpg", "jpeg"}

# campo -> (etiqueta para el historial, conversor)
CAMPOS = {
    "codigo_activo": ("Código de activo", texto),
    "nombre": ("Nombre", texto),
    "categoria_id": ("Categoría", a_entero),
    "marca": ("Marca", texto),
    "modelo": ("Modelo", texto),
    "numero_serie": ("N.º de serie", texto),
    "part_number": ("Part number", texto),
    "direccion_mac": ("Dirección MAC", texto),
    "direccion_ip": ("Dirección IP", texto),
    "hostname": ("Hostname", texto),
    "firmware": ("Firmware / SO", texto),
    "consumo_energia_w": ("Consumo (W)", a_entero),
    "especificaciones": ("Especificaciones", texto),
    "procesador": ("Procesador", texto),
    "memoria_ram": ("Memoria RAM", texto),
    "almacenamiento": ("Almacenamiento", texto),
    "sistema_operativo": ("Sistema operativo", texto),
    "licencia_so": ("Licencia SO", texto),
    "software_instalado": ("Software instalado", texto),
    "pantalla": ("Pantalla", texto),
    "imei": ("IMEI", texto),
    "numero_linea": ("N.º de línea", texto),
    "operador_movil": ("Operador móvil", texto),
    "area": ("Área / dependencia", texto),
    "accesorios": ("Accesorios", texto),
    "ubicacion_id": ("Ubicación", a_entero),
    "rack_posicion": ("Rack / posición", texto),
    "responsable": ("Responsable", texto),
    "estado": ("Estado", texto),
    "criticidad": ("Criticidad", texto),
    "fecha_instalacion": ("Fecha de instalación", a_fecha),
    "proveedor_id": ("Proveedor", a_entero),
    "fecha_adquisicion": ("Fecha de adquisición", a_fecha),
    "numero_factura": ("N.º factura", texto),
    "orden_compra": ("Orden de compra", texto),
    "valor_compra": ("Valor de compra", a_decimal),
    "valor_residual": ("Valor residual", a_decimal),
    "vida_util_anios": ("Vida útil (años)", a_entero),
    "garantia_hasta": ("Garantía hasta", a_fecha),
    "observaciones": ("Observaciones", texto),
}
CAMPOS_RELACION = {"categoria_id": Categoria, "ubicacion_id": Ubicacion, "proveedor_id": Proveedor}


def _catalogos():
    return {
        "categorias": Categoria.query.order_by(Categoria.grupo.desc(), Categoria.nombre).all(),
        "grupos": GRUPOS,
        "ubicaciones": Ubicacion.query.order_by(Ubicacion.nombre).all(),
        "proveedores": Proveedor.query.order_by(Proveedor.nombre).all(),
        "estados": ESTADOS_EQUIPO,
        "criticidades": CRITICIDADES,
    }


def _leer_formulario():
    """Convierte el formulario a un dict validado. Lanza ValueError con los errores."""
    datos, errores = {}, []
    for campo, (etiqueta, conversor) in CAMPOS.items():
        try:
            datos[campo] = conversor(request.form.get(campo))
        except ValueError as e:
            errores.append(f"{etiqueta}: {e}")

    for campo in ("codigo_activo", "nombre", "numero_serie", "categoria_id"):
        if not datos.get(campo):
            errores.append(f"{CAMPOS[campo][0]} es obligatorio.")
    if datos.get("estado") not in ESTADOS_EQUIPO:
        errores.append("Estado inválido.")
    if datos.get("criticidad") not in CRITICIDADES:
        errores.append("Criticidad inválida.")
    for campo, modelo in CAMPOS_RELACION.items():
        if datos.get(campo) and db.session.get(modelo, datos[campo]) is None:
            errores.append(f"{CAMPOS[campo][0]} no existe.")
    if datos.get("valor_compra") is not None and datos.get("valor_residual") is not None \
            and datos["valor_residual"] > datos["valor_compra"]:
        errores.append("El valor residual no puede ser mayor que el valor de compra.")
    if errores:
        raise ValueError(errores)
    return datos


def _validar_unicos(datos, equipo_id=None):
    errores = []
    for campo in ("codigo_activo", "numero_serie"):
        q = Equipo.query.filter(getattr(Equipo, campo) == datos[campo])
        if equipo_id:
            q = q.filter(Equipo.id != equipo_id)
        if q.first():
            errores.append(f"Ya existe un equipo con {CAMPOS[campo][0].lower()} «{datos[campo]}».")
    if errores:
        raise ValueError(errores)


def _guardar_foto(equipo):
    archivo = request.files.get("foto")
    if not archivo or not archivo.filename:
        return
    ext = archivo.filename.rsplit(".", 1)[-1].lower() if "." in archivo.filename else ""
    if ext not in EXTENSIONES_FOTO:
        raise ValueError(["La foto debe ser PNG o JPG."])
    try:
        datos, mime = comprimir_imagen(archivo.stream)
    except ValueError as e:
        raise ValueError([str(e)])
    _borrar_foto(equipo)
    # El nombre cambia en cada carga para que el navegador no muestre la foto anterior en caché
    extension = "png" if mime == "image/png" else "jpg"
    equipo.foto = f"equipo_{equipo.id}_{uuid.uuid4().hex[:8]}.{extension}"
    equipo.foto_datos, equipo.foto_mime = datos, mime


def _borrar_foto(equipo):
    if equipo.foto:
        # Fotos de versiones anteriores que aún estuvieran en disco
        ruta = os.path.join(current_app.config["UPLOAD_FOLDER"], equipo.foto)
        if os.path.exists(ruta):
            os.remove(ruta)
    equipo.foto = equipo.foto_datos = equipo.foto_mime = None


def _registrar(equipo, accion, detalle):
    db.session.add(Historial(equipo=equipo, accion=accion, detalle=detalle, usuario_id=current_user.id))


def _describir(campo, valor):
    if valor is None or valor == "":
        return "—"
    if campo in CAMPOS_RELACION:
        obj = db.session.get(CAMPOS_RELACION[campo], valor)
        return obj.nombre if obj else str(valor)
    return str(valor)


def _filtrar():
    q = Equipo.query
    grupo = request.args.get("grupo")
    if grupo in GRUPOS:
        q = q.join(Categoria).filter(Categoria.grupo == grupo)
    buscar = request.args.get("q", "").strip()
    if buscar:
        patron = f"%{buscar}%"
        q = q.filter(or_(Equipo.codigo_activo.ilike(patron), Equipo.nombre.ilike(patron),
                         Equipo.numero_serie.ilike(patron), Equipo.marca.ilike(patron),
                         Equipo.modelo.ilike(patron), Equipo.direccion_ip.ilike(patron),
                         Equipo.hostname.ilike(patron), Equipo.responsable.ilike(patron),
                         Equipo.imei.ilike(patron), Equipo.numero_linea.ilike(patron),
                         Equipo.area.ilike(patron)))
    for campo in ("categoria_id", "ubicacion_id", "proveedor_id"):
        valor = request.args.get(campo, type=int)
        if valor:
            q = q.filter(getattr(Equipo, campo) == valor)
    for campo in ("estado", "criticidad"):
        valor = request.args.get(campo)
        if valor:
            q = q.filter(getattr(Equipo, campo) == valor)
    return q.order_by(Equipo.codigo_activo)


# ---------------------------------------------------------------- Inventario
@bp.route("/")
@login_required
def lista():
    pagina = db.paginate(_filtrar(), page=request.args.get("page", 1, type=int),
                         per_page=15, error_out=False)
    filtros = {k: v for k, v in request.args.items() if k != "page" and v}
    grupo = request.args.get("grupo") if request.args.get("grupo") in GRUPOS else None
    return render_template("equipos/lista.html", pagina=pagina, filtros=filtros, grupo=grupo, **_catalogos())


@bp.route("/exportar.csv")
@login_required
def exportar():
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(["Código", "Nombre", "Grupo", "Categoría", "Marca", "Modelo", "Serie", "MAC", "IP",
                       "Hostname", "Firmware", "Procesador", "RAM", "Almacenamiento", "Sistema operativo",
                       "Licencia SO", "Pantalla", "IMEI", "Línea", "Operador", "Ubicación", "Rack",
                       "Responsable", "Área", "Accesorios", "Estado", "Criticidad", "Proveedor",
                       "F. adquisición", "Factura", "Valor compra", "Vida útil", "Valor en libros",
                       "Garantía hasta"])
    for e in _filtrar().all():
        escritor.writerow([
            e.codigo_activo, e.nombre, e.categoria.grupo, e.categoria.nombre, e.marca, e.modelo,
            e.numero_serie, e.direccion_mac, e.direccion_ip, e.hostname, e.firmware,
            e.procesador, e.memoria_ram, e.almacenamiento, e.sistema_operativo, e.licencia_so,
            e.pantalla, e.imei, e.numero_linea, e.operador_movil,
            e.ubicacion.nombre if e.ubicacion else "", e.rack_posicion, e.responsable, e.area,
            e.accesorios, e.estado, e.criticidad, e.proveedor.nombre if e.proveedor else "",
            e.fecha_adquisicion, e.numero_factura, e.valor_compra, e.vida_util_anios,
            e.valor_en_libros, e.garantia_hasta])
    nombre = {"Cómputo": "inventario_computo.csv", "Telecomunicaciones": "inventario_telecom.csv"}.get(
        request.args.get("grupo"), "inventario_equipos.csv")
    # BOM para que Excel abra correctamente las tildes
    return Response("﻿" + salida.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={nombre}"})


# ---------------------------------------------------------------- CRUD
@bp.route("/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo():
    if request.method == "POST":
        try:
            datos = _leer_formulario()
            _validar_unicos(datos)
            equipo = Equipo(**datos, creado_por_id=current_user.id)
            db.session.add(equipo)
            db.session.flush()
            _guardar_foto(equipo)
            _registrar(equipo, "Creación", f"Equipo registrado en el inventario con estado «{equipo.estado}».")
            db.session.commit()
            flash(f"Equipo {equipo.codigo_activo} creado.", "success")
            return redirect(url_for("equipos.detalle", equipo_id=equipo.id))
        except ValueError as e:
            db.session.rollback()
            for msg in e.args[0]:
                flash(msg, "danger")
    return render_template("equipos/form.html", equipo=None, form=request.form,
                           grupo_inicial=request.args.get("grupo"), **_catalogos())


@bp.route("/<int:equipo_id>")
@login_required
def detalle(equipo_id):
    equipo = db.get_or_404(Equipo, equipo_id)
    return render_template("equipos/detalle.html", equipo=equipo, tipos_mant=TIPOS_MANTENIMIENTO)


@bp.route("/<int:equipo_id>/editar", methods=["GET", "POST"])
@admin_required
def editar(equipo_id):
    equipo = db.get_or_404(Equipo, equipo_id)
    if request.method == "POST":
        try:
            datos = _leer_formulario()
            _validar_unicos(datos, equipo.id)
            cambios = []
            for campo, valor in datos.items():
                anterior = getattr(equipo, campo)
                if anterior != valor:
                    if campo in ("especificaciones", "observaciones", "software_instalado"):
                        cambios.append(f"{CAMPOS[campo][0]} modificado")
                    else:
                        cambios.append(f"{CAMPOS[campo][0]}: {_describir(campo, anterior)} → {_describir(campo, valor)}")
                    setattr(equipo, campo, valor)
            if request.form.get("quitar_foto"):
                _borrar_foto(equipo)
                cambios.append("Foto eliminada")
            foto_anterior = equipo.foto
            _guardar_foto(equipo)
            if equipo.foto != foto_anterior:
                cambios.append("Foto actualizada")

            if cambios:
                accion = "Actualización"
                if any(c.startswith("Ubicación") for c in cambios):
                    accion = "Traslado"
                elif any(c.startswith("Estado") for c in cambios):
                    accion = "Cambio de estado"
                _registrar(equipo, accion, "; ".join(cambios))
                db.session.commit()
                flash("Equipo actualizado.", "success")
            else:
                flash("No se detectaron cambios.", "info")
            return redirect(url_for("equipos.detalle", equipo_id=equipo.id))
        except ValueError as e:
            db.session.rollback()
            for msg in e.args[0]:
                flash(msg, "danger")
        return render_template("equipos/form.html", equipo=equipo, form=request.form, **_catalogos())
    return render_template("equipos/form.html", equipo=equipo, form={}, **_catalogos())


@bp.route("/<int:equipo_id>/eliminar", methods=["POST"])
@admin_required
def eliminar(equipo_id):
    equipo = db.get_or_404(Equipo, equipo_id)
    codigo = equipo.codigo_activo
    _borrar_foto(equipo)
    db.session.delete(equipo)
    db.session.commit()
    flash(f"Equipo {codigo} eliminado.", "success")
    return redirect(url_for("equipos.lista"))


# ---------------------------------------------------------------- Hoja de vida PDF
@bp.route("/<int:equipo_id>/pdf")
@login_required
def pdf(equipo_id):
    equipo = db.get_or_404(Equipo, equipo_id)
    contenido = generar_hoja_vida(equipo, current_app.config["EMPRESA_NOMBRE"], current_user.nombre)
    nombre = f"hoja_de_vida_{equipo.codigo_activo}.pdf"
    disposicion = "inline" if request.args.get("ver") else "attachment"
    return Response(contenido, mimetype="application/pdf",
                    headers={"Content-Disposition": f'{disposicion}; filename="{nombre}"'})


# ---------------------------------------------------------------- Mantenimientos
@bp.route("/<int:equipo_id>/mantenimientos", methods=["POST"])
@login_required
def agregar_mantenimiento(equipo_id):
    equipo = db.get_or_404(Equipo, equipo_id)
    try:
        tipo = request.form.get("tipo")
        descripcion = texto(request.form.get("descripcion"))
        fecha = a_fecha(request.form.get("fecha"))
        if tipo not in TIPOS_MANTENIMIENTO:
            raise ValueError("Tipo de mantenimiento inválido.")
        if not descripcion or not fecha:
            raise ValueError("La fecha y la descripción son obligatorias.")
        mant = Mantenimiento(
            equipo=equipo, fecha=fecha, tipo=tipo, descripcion=descripcion,
            tecnico=texto(request.form.get("tecnico")),
            costo=a_decimal(request.form.get("costo")),
            proxima_fecha=a_fecha(request.form.get("proxima_fecha")),
            registrado_por_id=current_user.id)
        db.session.add(mant)
        nuevo_estado = request.form.get("nuevo_estado")
        detalle = f"Mantenimiento {tipo.lower()} del {fecha:%d/%m/%Y}: {descripcion}"
        if nuevo_estado in ESTADOS_EQUIPO and nuevo_estado != equipo.estado:
            detalle += f" — Estado: {equipo.estado} → {nuevo_estado}"
            equipo.estado = nuevo_estado
        _registrar(equipo, "Mantenimiento", detalle)
        db.session.commit()
        flash("Mantenimiento registrado.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "danger")
    return redirect(url_for("equipos.detalle", equipo_id=equipo.id, _anchor="mantenimientos"))


@bp.route("/mantenimientos/<int:mant_id>/eliminar", methods=["POST"])
@admin_required
def eliminar_mantenimiento(mant_id):
    mant = db.get_or_404(Mantenimiento, mant_id)
    equipo = mant.equipo
    _registrar(equipo, "Actualización",
               f"Se eliminó el registro de mantenimiento {mant.tipo.lower()} del {mant.fecha:%d/%m/%Y}.")
    db.session.delete(mant)
    db.session.commit()
    flash("Registro de mantenimiento eliminado.", "success")
    return redirect(url_for("equipos.detalle", equipo_id=equipo.id, _anchor="mantenimientos"))
