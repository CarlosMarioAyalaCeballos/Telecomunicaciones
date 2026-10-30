"""Creación de tablas, usuario administrador y datos de ejemplo."""
import os
import time
from datetime import date, timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy.exc import OperationalError

from . import db
from .models import Categoria, Equipo, Historial, Mantenimiento, Proveedor, Ubicacion, Usuario


def _esperar_bd(intentos=30):
    for i in range(intentos):
        try:
            db.session.execute(db.text("SELECT 1"))
            return
        except OperationalError:
            print(f"Esperando la base de datos ({i + 1}/{intentos})...")
            time.sleep(2)
    raise RuntimeError("No fue posible conectar con la base de datos")


def _migrar():
    """Agrega a las tablas existentes las columnas nuevas del modelo (sin borrar datos)."""
    inspector = db.inspect(db.engine)
    for tabla in db.metadata.sorted_tables:
        existentes = {c["name"] for c in inspector.get_columns(tabla.name)}
        for col in tabla.columns:
            if col.name in existentes:
                continue
            ddl = f'ALTER TABLE {tabla.name} ADD COLUMN {col.name} {col.type.compile(dialect=db.engine.dialect)}'
            if col.server_default is not None:
                ddl += f" DEFAULT '{col.server_default.arg}'"
            if not col.nullable:
                ddl += " NOT NULL"
            db.session.execute(db.text(ddl))
            print(f"Migración: columna {tabla.name}.{col.name} agregada.")
    db.session.commit()


CATEGORIAS_COMPUTO = [
    ("Portátil", "Computadores portátiles / laptops"),
    ("Computador de escritorio", "Torres, mini PC y All-in-One"),
    ("Tablet", "Tabletas Android, iPad y similares"),
    ("Celular / Smartphone", "Teléfonos móviles corporativos"),
    ("Monitor", "Pantallas y monitores"),
    ("Impresora / Escáner", "Impresoras, multifuncionales y escáneres"),
]


def _categorias_computo():
    """Crea las categorías de cómputo la primera vez (si aún no existe ninguna de ese grupo)."""
    if Categoria.query.filter_by(grupo="Cómputo").count() == 0:
        for nombre, descripcion in CATEGORIAS_COMPUTO:
            if not Categoria.query.filter_by(nombre=nombre).first():
                db.session.add(Categoria(nombre=nombre, descripcion=descripcion, grupo="Cómputo"))
        db.session.commit()
        print("Categorías de cómputo creadas.")


def _fotos_a_bd():
    """Mueve a la BD las fotos que versiones anteriores guardaban en la carpeta uploads."""
    carpeta = current_app.config["UPLOAD_FOLDER"]
    movidas = 0
    for equipo in Equipo.query.filter(Equipo.foto.is_not(None), Equipo.foto_datos.is_(None)):
        ruta = os.path.join(carpeta, equipo.foto)
        if os.path.exists(ruta):
            with open(ruta, "rb") as f:
                equipo.foto_datos = f.read()
            equipo.foto_mime = "image/png" if equipo.foto.lower().endswith(".png") else "image/jpeg"
            movidas += 1
        else:
            equipo.foto = None  # el archivo ya no existe
    db.session.commit()
    if movidas:
        print(f"Migración: {movidas} foto(s) movidas a la base de datos.")


def inicializar():
    _esperar_bd()
    db.create_all()
    _migrar()
    _fotos_a_bd()

    if Usuario.query.count() == 0:
        admin = Usuario(username=os.getenv("ADMIN_USERNAME", "admin"), nombre="Administrador del sistema",
                        email="admin@telecom.local", rol="ADMIN")
        admin.set_password(os.getenv("ADMIN_PASSWORD", "admin123"))
        db.session.add(admin)
        if os.getenv("SEED_DEMO", "true").lower() == "true":
            usuario = Usuario(username="usuario", nombre="Técnico de consulta",
                              email="usuario@telecom.local", rol="USER")
            usuario.set_password("usuario123")
            db.session.add(usuario)
        db.session.commit()
        print("Usuarios iniciales creados.")

    demo = os.getenv("SEED_DEMO", "true").lower() == "true"
    if demo and Categoria.query.count() == 0:
        _datos_demo()
        print("Datos de ejemplo cargados.")

    _categorias_computo()
    hay_computo = Equipo.query.join(Categoria).filter(Categoria.grupo == "Cómputo").count()
    if demo and not hay_computo:
        _datos_demo_computo()
        print("Datos de ejemplo de cómputo cargados.")


def _datos_demo():
    admin = Usuario.query.filter_by(rol="ADMIN").first()
    cats = {n: Categoria(nombre=n, descripcion=d) for n, d in [
        ("Router", "Equipos de enrutamiento IP/MPLS"),
        ("Switch", "Conmutadores Ethernet de acceso, distribución y core"),
        ("OLT", "Terminales de línea óptica GPON/XGS-PON"),
        ("Radio enlace", "Radios microondas punto a punto / multipunto"),
        ("Antena", "Antenas sectoriales, parabólicas y omnidireccionales"),
        ("Firewall", "Seguridad perimetral"),
        ("Energía / UPS", "UPS, rectificadores y bancos de baterías"),
        ("Servidor", "Servidores físicos"),
    ]}
    ubis = {
        "DC": Ubicacion(nombre="Data Center Principal", tipo="Data Center", direccion="Cra 7 # 71-21",
                        ciudad="Bogotá", departamento="Cundinamarca", latitud=4.6533, longitud=-74.0566),
        "NODO": Ubicacion(nombre="Nodo Chapinero", tipo="Nodo", direccion="Cl 57 # 13-40",
                          ciudad="Bogotá", departamento="Cundinamarca"),
        "TORRE": Ubicacion(nombre="Torre Cerro Monserrate", tipo="Torre / Estación base",
                           ciudad="Bogotá", departamento="Cundinamarca", latitud=4.6058, longitud=-74.0556),
        "BODEGA": Ubicacion(nombre="Bodega Central", tipo="Bodega", direccion="Zona Industrial Montevideo",
                            ciudad="Bogotá", departamento="Cundinamarca"),
    }
    provs = {
        "CISCO": Proveedor(nombre="Distribuidora Redes Andinas S.A.S.", nit="900.123.456-7",
                           contacto="Laura Gómez", telefono="601 555 0101", email="ventas@redesandinas.co"),
        "HW": Proveedor(nombre="Soluciones Ópticas de Colombia", nit="901.234.567-8",
                        contacto="Andrés Ruiz", telefono="601 555 0202", email="comercial@sopticas.co"),
        "PWR": Proveedor(nombre="Energía Crítica Ltda.", nit="830.345.678-9",
                         contacto="Marta Díaz", telefono="604 555 0303"),
    }
    db.session.add_all([*cats.values(), *ubis.values(), *provs.values()])
    db.session.flush()

    hoy = date.today()
    equipos = [
        dict(codigo_activo="ACT-RTR-0001", nombre="Router de borde principal", categoria=cats["Router"],
             marca="Cisco", modelo="ASR 1002-HX", numero_serie="FXS2231Q0AB", part_number="ASR1002-HX",
             direccion_ip="10.0.0.1", direccion_mac="00:1A:2B:3C:4D:01", hostname="bog-edge-01",
             firmware="IOS-XE 17.9.4", consumo_energia_w=470, ubicacion=ubis["DC"], rack_posicion="Rack A1 / U20-U21",
             responsable="Ing. Carlos Pérez", estado="Operativo", criticidad="Alta", proveedor=provs["CISCO"],
             fecha_adquisicion=hoy - timedelta(days=900), fecha_instalacion=hoy - timedelta(days=880),
             numero_factura="FE-10234", orden_compra="OC-2023-045", valor_compra=Decimal("185000000"),
             valor_residual=Decimal("15000000"), vida_util_anios=10, garantia_hasta=hoy + timedelta(days=60),
             especificaciones="4x 10GE SFP+, 8x 1GE, 2 fuentes redundantes AC, 100 Gbps throughput"),
        dict(codigo_activo="ACT-SW-0001", nombre="Switch core", categoria=cats["Switch"],
             marca="Huawei", modelo="CE6881-48S6CQ", numero_serie="2102351QNL10K5000012",
             direccion_ip="10.0.0.2", hostname="bog-core-sw01", firmware="V200R022C00",
             consumo_energia_w=350, ubicacion=ubis["DC"], rack_posicion="Rack A2 / U30",
             responsable="Ing. Carlos Pérez", estado="Operativo", criticidad="Alta", proveedor=provs["HW"],
             fecha_adquisicion=hoy - timedelta(days=600), valor_compra=Decimal("62000000"),
             vida_util_anios=8, garantia_hasta=hoy + timedelta(days=500)),
        dict(codigo_activo="ACT-OLT-0001", nombre="OLT GPON Chapinero", categoria=cats["OLT"],
             marca="Huawei", modelo="MA5800-X7", numero_serie="21023518VN10J8000045",
             direccion_ip="10.10.1.5", firmware="V100R021", ubicacion=ubis["NODO"],
             rack_posicion="Rack N1 / U10-U16", responsable="Téc. Ana Martínez", estado="En mantenimiento",
             criticidad="Alta", proveedor=provs["HW"], fecha_adquisicion=hoy - timedelta(days=1200),
             valor_compra=Decimal("98000000"), valor_residual=Decimal("5000000"), vida_util_anios=10,
             especificaciones="2 tarjetas GPHF 16 puertos, 2 MCUD, capacidad 7 slots de servicio"),
        dict(codigo_activo="ACT-RAD-0001", nombre="Radio enlace Monserrate - DC", categoria=cats["Radio enlace"],
             marca="Ubiquiti", modelo="airFiber AF-5XHD", numero_serie="UBQAF5XHD000981",
             direccion_ip="10.20.0.11", direccion_mac="F0:9F:C2:AA:10:11", firmware="v4.1.0",
             ubicacion=ubis["TORRE"], responsable="Téc. Jorge León", estado="Operativo", criticidad="Media",
             proveedor=provs["CISCO"], fecha_adquisicion=hoy - timedelta(days=400),
             valor_compra=Decimal("4800000"), vida_util_anios=5),
        dict(codigo_activo="ACT-UPS-0001", nombre="UPS Data Center 20 kVA", categoria=cats["Energía / UPS"],
             marca="APC", modelo="Symmetra PX 20kW", numero_serie="PX20K-AS1932000123",
             ubicacion=ubis["DC"], responsable="Ing. Carlos Pérez", estado="Operativo", criticidad="Alta",
             proveedor=provs["PWR"], fecha_adquisicion=hoy - timedelta(days=2000),
             valor_compra=Decimal("75000000"), vida_util_anios=10, consumo_energia_w=1200),
        dict(codigo_activo="ACT-SW-0002", nombre="Switch de acceso (repuesto)", categoria=cats["Switch"],
             marca="Cisco", modelo="Catalyst 9200L-24P", numero_serie="JAE24410ABC",
             ubicacion=ubis["BODEGA"], estado="En bodega", criticidad="Baja", proveedor=provs["CISCO"],
             fecha_adquisicion=hoy - timedelta(days=200), valor_compra=Decimal("9500000"), vida_util_anios=5),
    ]
    for datos in equipos:
        e = Equipo(**datos, creado_por=admin)
        db.session.add(e)
        db.session.add(Historial(equipo=e, accion="Creación", usuario=admin,
                                 detalle=f"Equipo registrado en el inventario con estado «{e.estado}»."))
    db.session.flush()

    rtr = Equipo.query.filter_by(codigo_activo="ACT-RTR-0001").first()
    olt = Equipo.query.filter_by(codigo_activo="ACT-OLT-0001").first()
    db.session.add_all([
        Mantenimiento(equipo=rtr, fecha=hoy - timedelta(days=180), tipo="Preventivo", tecnico="Ing. Carlos Pérez",
                      descripcion="Limpieza de filtros, verificación de fuentes y revisión de logs.",
                      costo=Decimal("350000"), proxima_fecha=hoy + timedelta(days=10), registrado_por=admin),
        Mantenimiento(equipo=rtr, fecha=hoy - timedelta(days=90), tipo="Actualización de firmware",
                      tecnico="Ing. Carlos Pérez", descripcion="Actualización IOS-XE 17.6 → 17.9.4.",
                      registrado_por=admin),
        Mantenimiento(equipo=olt, fecha=hoy - timedelta(days=2), tipo="Correctivo", tecnico="Téc. Ana Martínez",
                      descripcion="Falla en tarjeta GPHF slot 3. Se solicita RMA al proveedor.",
                      costo=Decimal("1200000"), proxima_fecha=hoy + timedelta(days=5), registrado_por=admin),
    ])
    db.session.commit()


def _datos_demo_computo():
    admin = Usuario.query.filter_by(rol="ADMIN").first()
    cat = {c.nombre: c for c in Categoria.query.filter_by(grupo="Cómputo")}
    oficina = Ubicacion.query.filter_by(tipo="Oficina").first()
    if oficina is None:
        oficina = Ubicacion(nombre="Oficina Principal", tipo="Oficina", direccion="Cl 93 # 11-26",
                            ciudad="Bogotá", departamento="Cundinamarca")
        db.session.add(oficina)
    hoy = date.today()
    equipos = [
        dict(codigo_activo="ACT-PC-0001", nombre="Portátil ingeniería", categoria=cat.get("Portátil"),
             marca="Lenovo", modelo="ThinkPad T14 Gen 4", numero_serie="PF4XK2LM", estado="Operativo",
             criticidad="Media", procesador="Intel Core i7-1365U", memoria_ram="16 GB DDR5",
             almacenamiento="512 GB SSD NVMe", sistema_operativo="Windows 11 Pro",
             licencia_so="OEM Windows 11 Pro", pantalla='14"', direccion_mac="8C:16:45:AA:01:02",
             hostname="LT-ING-001", software_instalado="Microsoft 365, Winbox, PuTTY, Wireshark",
             responsable="Ing. Carlos Pérez", area="Ingeniería de red", accesorios="Cargador USB-C 65W, maletín",
             ubicacion=oficina, fecha_adquisicion=hoy - timedelta(days=500), valor_compra=Decimal("6200000"),
             vida_util_anios=3, garantia_hasta=hoy + timedelta(days=230)),
        dict(codigo_activo="ACT-PC-0002", nombre="Computador NOC", categoria=cat.get("Computador de escritorio"),
             marca="Dell", modelo="OptiPlex 7010", numero_serie="7XQ9KL3", estado="Operativo", criticidad="Alta",
             procesador="Intel Core i5-13500", memoria_ram="32 GB", almacenamiento="1 TB SSD",
             sistema_operativo="Ubuntu 22.04 LTS", hostname="PC-NOC-01", direccion_ip="10.50.0.21",
             responsable="Centro de gestión (NOC)", area="Operaciones", accesorios="2 monitores 24\", teclado, mouse",
             ubicacion=oficina, fecha_adquisicion=hoy - timedelta(days=300), valor_compra=Decimal("4100000"),
             vida_util_anios=5),
        dict(codigo_activo="ACT-TAB-0001", nombre="Tablet de campo", categoria=cat.get("Tablet"),
             marca="Samsung", modelo="Galaxy Tab Active4 Pro", numero_serie="R52T80ABCDE", estado="Operativo",
             criticidad="Media", memoria_ram="6 GB", almacenamiento="128 GB", sistema_operativo="Android 14",
             pantalla='10.1"', imei="356789104512347", responsable="Téc. Jorge León", area="Mantenimiento en campo",
             accesorios="Funda rugerizada, lápiz S Pen", ubicacion=oficina,
             fecha_adquisicion=hoy - timedelta(days=150), valor_compra=Decimal("3200000"), vida_util_anios=3),
        dict(codigo_activo="ACT-CEL-0001", nombre="Celular corporativo supervisor", categoria=cat.get("Celular / Smartphone"),
             marca="Apple", modelo="iPhone 15", numero_serie="F2LXK9P0Q1", estado="Operativo", criticidad="Baja",
             almacenamiento="128 GB", sistema_operativo="iOS 18", pantalla='6.1"', imei="353912110987654",
             numero_linea="300 555 0147", operador_movil="Claro", responsable="Ana Martínez",
             area="Supervisión técnica", accesorios="Cargador, protector", ubicacion=oficina,
             fecha_adquisicion=hoy - timedelta(days=90), valor_compra=Decimal("4300000"), vida_util_anios=2,
             garantia_hasta=hoy + timedelta(days=275)),
    ]
    for datos in equipos:
        if datos["categoria"] is None or Equipo.query.filter_by(codigo_activo=datos["codigo_activo"]).first():
            continue
        e = Equipo(**datos, creado_por=admin)
        db.session.add(e)
        db.session.add(Historial(equipo=e, accion="Creación", usuario=admin,
                                 detalle=f"Equipo registrado en el inventario con estado «{e.estado}»."))
    db.session.commit()
