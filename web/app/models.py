from datetime import date, datetime
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

ROLES = ("ADMIN", "USER")
GRUPOS = ("Telecomunicaciones", "Cómputo")
ESTADOS_EQUIPO = ("Operativo", "En mantenimiento", "En bodega", "Dañado", "Dado de baja")
CRITICIDADES = ("Alta", "Media", "Baja")
TIPOS_MANTENIMIENTO = ("Preventivo", "Correctivo", "Predictivo", "Actualización de firmware", "Calibración")
TIPOS_UBICACION = ("Nodo", "Torre / Estación base", "Data Center", "Oficina", "Bodega", "Cliente")


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(10), nullable=False, default="USER")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.rol == "ADMIN"

    @property
    def is_active(self):
        return self.activo


class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    grupo = db.Column(db.String(20), nullable=False, default="Telecomunicaciones",
                      server_default="Telecomunicaciones")
    descripcion = db.Column(db.String(255))

    equipos = db.relationship("Equipo", back_populates="categoria")


class Ubicacion(db.Model):
    __tablename__ = "ubicaciones"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    tipo = db.Column(db.String(40))
    direccion = db.Column(db.String(200))
    ciudad = db.Column(db.String(80))
    departamento = db.Column(db.String(80))
    latitud = db.Column(db.Numeric(9, 6))
    longitud = db.Column(db.Numeric(9, 6))
    descripcion = db.Column(db.String(255))

    equipos = db.relationship("Equipo", back_populates="ubicacion")


class Proveedor(db.Model):
    __tablename__ = "proveedores"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    nit = db.Column(db.String(30))
    contacto = db.Column(db.String(120))
    telefono = db.Column(db.String(40))
    email = db.Column(db.String(120))
    direccion = db.Column(db.String(200))

    equipos = db.relationship("Equipo", back_populates="proveedor")


class Equipo(db.Model):
    __tablename__ = "equipos"

    id = db.Column(db.Integer, primary_key=True)
    # Identificación
    codigo_activo = db.Column(db.String(40), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(150), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    marca = db.Column(db.String(80))
    modelo = db.Column(db.String(80))
    numero_serie = db.Column(db.String(80), unique=True, nullable=False, index=True)
    part_number = db.Column(db.String(80))
    # Información técnica
    direccion_mac = db.Column(db.String(30))
    direccion_ip = db.Column(db.String(45))
    hostname = db.Column(db.String(100))
    firmware = db.Column(db.String(80))
    consumo_energia_w = db.Column(db.Integer)
    especificaciones = db.Column(db.Text)
    # Cómputo y dispositivos móviles
    procesador = db.Column(db.String(120))
    memoria_ram = db.Column(db.String(40))
    almacenamiento = db.Column(db.String(80))
    sistema_operativo = db.Column(db.String(80))
    licencia_so = db.Column(db.String(120))
    software_instalado = db.Column(db.Text)
    pantalla = db.Column(db.String(40))
    imei = db.Column(db.String(40))
    numero_linea = db.Column(db.String(30))
    operador_movil = db.Column(db.String(40))
    area = db.Column(db.String(120))
    accesorios = db.Column(db.String(255))
    # Ubicación y estado
    ubicacion_id = db.Column(db.Integer, db.ForeignKey("ubicaciones.id"))
    rack_posicion = db.Column(db.String(60))
    responsable = db.Column(db.String(120))
    estado = db.Column(db.String(30), nullable=False, default="Operativo")
    criticidad = db.Column(db.String(10), nullable=False, default="Media")
    fecha_instalacion = db.Column(db.Date)
    # Adquisición y financiera
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"))
    fecha_adquisicion = db.Column(db.Date)
    numero_factura = db.Column(db.String(60))
    orden_compra = db.Column(db.String(60))
    valor_compra = db.Column(db.Numeric(14, 2))
    valor_residual = db.Column(db.Numeric(14, 2))
    vida_util_anios = db.Column(db.Integer)
    garantia_hasta = db.Column(db.Date)
    # Otros
    observaciones = db.Column(db.Text)
    foto = db.Column(db.String(200))
    # La imagen se guarda en la BD para no perderla en hostings sin disco persistente (Render).
    # deferred: solo se carga cuando se pide, no en cada consulta del inventario.
    foto_datos = db.deferred(db.Column(db.LargeBinary))
    foto_mime = db.Column(db.String(30))
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.now)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    creado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))

    categoria = db.relationship("Categoria", back_populates="equipos")
    ubicacion = db.relationship("Ubicacion", back_populates="equipos")
    proveedor = db.relationship("Proveedor", back_populates="equipos")
    creado_por = db.relationship("Usuario")
    mantenimientos = db.relationship(
        "Mantenimiento", back_populates="equipo", cascade="all, delete-orphan",
        order_by="desc(Mantenimiento.fecha)")
    historial = db.relationship(
        "Historial", back_populates="equipo", cascade="all, delete-orphan",
        order_by="desc(Historial.fecha)")

    @property
    def es_computo(self):
        return self.categoria is not None and self.categoria.grupo == "Cómputo"

    # --- Cálculos financieros (depreciación en línea recta) ---
    @property
    def depreciacion_anual(self):
        if not (self.valor_compra and self.vida_util_anios):
            return None
        base = Decimal(self.valor_compra) - Decimal(self.valor_residual or 0)
        return (base / self.vida_util_anios).quantize(Decimal("0.01"))

    @property
    def anios_uso(self):
        if not self.fecha_adquisicion:
            return None
        return round((date.today() - self.fecha_adquisicion).days / 365.25, 2)

    @property
    def depreciacion_acumulada(self):
        anual, anios = self.depreciacion_anual, self.anios_uso
        if anual is None or anios is None:
            return None
        anios = min(max(anios, 0), self.vida_util_anios)
        return (anual * Decimal(str(anios))).quantize(Decimal("0.01"))

    @property
    def valor_en_libros(self):
        acumulada = self.depreciacion_acumulada
        if acumulada is None:
            return None
        return Decimal(self.valor_compra) - acumulada

    @property
    def en_garantia(self):
        return bool(self.garantia_hasta and self.garantia_hasta >= date.today())

    @property
    def costo_mantenimientos(self):
        return sum((m.costo or Decimal(0) for m in self.mantenimientos), Decimal(0))


class Mantenimiento(db.Model):
    __tablename__ = "mantenimientos"

    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey("equipos.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    tipo = db.Column(db.String(40), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    tecnico = db.Column(db.String(120))
    costo = db.Column(db.Numeric(14, 2))
    proxima_fecha = db.Column(db.Date)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.now)

    equipo = db.relationship("Equipo", back_populates="mantenimientos")
    registrado_por = db.relationship("Usuario")


class Historial(db.Model):
    """Bitácora de eventos del equipo: creación, cambios, traslados, mantenimientos."""
    __tablename__ = "historial"

    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey("equipos.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.now)
    accion = db.Column(db.String(40), nullable=False)
    detalle = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))

    equipo = db.relationship("Equipo", back_populates="historial")
    usuario = db.relationship("Usuario")
