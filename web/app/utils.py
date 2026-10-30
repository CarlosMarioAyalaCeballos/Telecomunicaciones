from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(vista):
    """Restringe la vista al rol ADMIN."""
    @wraps(vista)
    @login_required
    def envoltura(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return vista(*args, **kwargs)
    return envoltura


def texto(valor):
    valor = (valor or "").strip()
    return valor or None


def a_fecha(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Fecha inválida: {valor}")


def a_decimal(valor):
    valor = (valor or "").strip().replace(",", ".")
    if not valor:
        return None
    try:
        numero = Decimal(valor)
    except InvalidOperation:
        raise ValueError(f"Número inválido: {valor}")
    if numero < 0:
        raise ValueError("Los valores no pueden ser negativos")
    return numero


def a_entero(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        numero = int(valor)
    except ValueError:
        raise ValueError(f"Número entero inválido: {valor}")
    if numero < 0:
        raise ValueError("Los valores no pueden ser negativos")
    return numero
