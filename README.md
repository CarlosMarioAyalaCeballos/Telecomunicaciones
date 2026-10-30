# Sistema de Activos Fijos de Telecomunicaciones

Aplicación web para el inventario y la **hoja de vida** de equipos de telecomunicaciones
(routers, switches, OLT, radios, antenas, UPS…), con exportación a **PDF**, base de datos
relacional **PostgreSQL**, login y dos roles (**ADMIN** y **USER**). Todo corre en **Docker**.

## Arranque rápido

```bash
cp .env.example .env        # (opcional) ajuste claves y nombre de la empresa
docker compose up -d --build
```

Abra **http://localhost:8000**

| Usuario   | Contraseña   | Rol   |
|-----------|--------------|-------|
| `admin`   | `admin123`   | ADMIN |
| `usuario` | `usuario123` | USER  |

> Cambie las contraseñas después del primer ingreso (menú del usuario → *Cambiar contraseña*).
> El usuario `usuario` y los equipos de ejemplo solo se crean si `SEED_DEMO=true`.

Comandos útiles:

```bash
docker compose logs -f web          # ver logs
docker compose down                 # detener
docker compose down -v              # detener y BORRAR la base de datos y fotos
docker compose exec db pg_dump -U activos activos_telecom > respaldo.sql   # respaldo
```

## Funcionalidades

- **Login** con sesiones seguras, contraseñas cifradas (hash) y protección CSRF.
- **Roles**
  - **ADMIN**: crear, editar y eliminar equipos, mantenimientos, catálogos y usuarios.
  - **USER**: consultar inventario y hojas de vida, descargar PDF/CSV y registrar mantenimientos.
- **Dos grupos de activos** con menú propio:
  - **Telecomunicaciones**: routers, switches, OLT, radios, antenas, UPS…
  - **Cómputo y móviles**: portátiles, computadores de escritorio, tablets, celulares, monitores,
    impresoras. Campos adicionales: procesador, RAM, almacenamiento, sistema operativo, licencia,
    software instalado, pantalla, IMEI, línea y operador, área y accesorios. Su PDF incluye firmas de
    *Entregó / Recibió*, por lo que sirve como acta de entrega al usuario.
  - El grupo se define en cada categoría (*Catálogos → Categorías*), así que puede crear nuevas.
- **Inventario detallado** con búsqueda (código, serie, marca, modelo, IP, hostname, responsable),
  filtros por categoría, ubicación, estado y criticidad, paginación y exportación a CSV (Excel).
- **Hoja de vida del equipo**: identificación, información técnica (IP, MAC, hostname, firmware,
  consumo), ubicación/rack/responsable, adquisición (proveedor, factura, OC, garantía),
  **depreciación en línea recta** y valor en libros, foto, historial de mantenimientos y bitácora
  automática de eventos (creación, traslados, cambios de estado, actualizaciones).
- **PDF de la hoja de vida** listo para imprimir y firmar (ver o descargar).
- **Catálogos**: categorías, ubicaciones/sitios (con coordenadas) y proveedores.
- **Panel** con totales, equipos por estado y categoría, mantenimientos próximos/vencidos y
  garantías por vencer.

## Modelo de datos (PostgreSQL)

```
usuarios ─┐
          ├──< equipos >── categorias
          │      │  └───── ubicaciones
          │      │  └───── proveedores
          │      ├──< mantenimientos
          └──────┴──< historial
```

| Tabla            | Descripción                                                      |
|------------------|------------------------------------------------------------------|
| `usuarios`       | Usuarios, rol (ADMIN/USER) y estado                               |
| `categorias`     | Tipos de equipo y su grupo (Telecomunicaciones / Cómputo)         |
| `ubicaciones`    | Sitios: nodos, torres, data center, bodegas                       |
| `proveedores`    | Proveedores / distribuidores                                      |
| `equipos`        | Activo fijo con todos sus datos técnicos, ubicación y financieros |
| `mantenimientos` | Preventivos, correctivos, firmware… con costo y próxima fecha     |
| `historial`      | Bitácora automática de eventos de cada equipo                     |

**Migraciones:** al arrancar, `init_db.py` agrega automáticamente a la base de datos existente las
columnas nuevas que se definan en `models.py`, sin borrar datos.

## Estructura

```
docker-compose.yml        Servicios: db (PostgreSQL 16) y web (Flask + Gunicorn)
web/
  Dockerfile
  init_db.py              Crea tablas, usuario admin y datos de ejemplo
  app/
    models.py             Modelo relacional (SQLAlchemy)
    auth.py               Login, logout, cambio de contraseña
    equipos.py            Inventario, CRUD, hoja de vida, mantenimientos, CSV
    pdf.py                Generación del PDF (ReportLab)
    catalogos.py          CRUD de categorías, ubicaciones y proveedores
    usuarios.py           Gestión de usuarios (solo ADMIN)
    templates/            Vistas (Bootstrap 5)
```

## Variables de entorno (`.env`)

| Variable          | Por defecto                              |
|-------------------|------------------------------------------|
| `POSTGRES_DB`     | `activos_telecom`                        |
| `POSTGRES_USER`   | `activos`                                |
| `POSTGRES_PASSWORD` | `activos_pass`                         |
| `SECRET_KEY`      | `cambie-esta-clave-secreta` (**cámbiela**) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin123` (solo al crear la BD) |
| `EMPRESA_NOMBRE`  | Nombre que aparece en el PDF             |
| `SEED_DEMO`       | `true` carga datos de ejemplo            |
