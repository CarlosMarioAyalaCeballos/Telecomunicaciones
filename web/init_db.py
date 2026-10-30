"""Crea las tablas y carga los datos iniciales antes de arrancar gunicorn."""
from app import create_app
from app.seed import inicializar

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        inicializar()
