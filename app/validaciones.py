"""Validación y normalización de datos de entrada (funciones de una sola tarea)."""
from __future__ import annotations

import re
from typing import Optional

from .errores import ErrorDeValidacion

_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PATRON_CODIGO = re.compile(r"^[A-Z]{2,5}-\d{2,4}$")
_PATRON_PERIODO = re.compile(r"^\d{4}-(Primavera|Verano|Otoño)$", re.IGNORECASE)


def validar_correo(valor: Optional[str]) -> str:
    """Correo en minúsculas y sin espacios; lanza ErrorDeValidacion si no es válido."""
    limpio = (valor or "").strip().lower()
    if not limpio:
        raise ErrorDeValidacion("El correo no puede estar vacío.")
    if len(limpio) > 254 or not _PATRON_CORREO.match(limpio):
        raise ErrorDeValidacion(f"'{limpio}' no es un correo válido (ej. nombre@dominio.com).")
    return limpio


def validar_texto(valor: Optional[str], campo: str, maximo: int = 100) -> str:
    """Texto obligatorio (no vacío ni solo espacios) con largo máximo."""
    limpio = " ".join((valor or "").split())
    if not limpio:
        raise ErrorDeValidacion(f"El campo '{campo}' es obligatorio y no puede estar vacío.")
    if len(limpio) > maximo:
        raise ErrorDeValidacion(f"El campo '{campo}' admite máximo {maximo} caracteres.")
    return limpio


def validar_entero(valor: object, campo: str, minimo: int, maximo: int) -> int:
    """Convierte a entero y exige que esté en [minimo, maximo]; rechaza letras y decimales."""
    if isinstance(valor, bool):
        raise ErrorDeValidacion(f"'{campo}' debe ser un número entero.")
    if isinstance(valor, int):
        numero = valor
    else:
        texto = str(valor if valor is not None else "").strip()
        if not (texto.isascii() and texto.isdigit()):
            raise ErrorDeValidacion(f"'{campo}' debe ser un número entero (recibido: '{texto}').")
        numero = int(texto)
    if not minimo <= numero <= maximo:
        raise ErrorDeValidacion(f"'{campo}' debe estar entre {minimo} y {maximo}.")
    return numero


def validar_codigo_materia(valor: Optional[str]) -> str:
    """Código tipo BDA-401 (letras, guion, números); se guarda en mayúsculas."""
    limpio = (valor or "").strip().upper()
    if not _PATRON_CODIGO.match(limpio):
        raise ErrorDeValidacion(
            f"'{limpio}' no es un código válido: usa letras, guion y números (ej. BDA-401)."
        )
    return limpio


def validar_periodo(valor: Optional[str]) -> str:
    """Periodo escolar como 2026-Otoño."""
    limpio = (valor or "").strip()
    if not _PATRON_PERIODO.match(limpio):
        raise ErrorDeValidacion(
            f"'{limpio}' no es un periodo válido (ej. 2026-Otoño, 2027-Primavera, 2027-Verano)."
        )
    año, temporada = limpio.split("-")
    return f"{año}-{temporada.capitalize()}"


def validar_habilidad(valor: Optional[str]) -> str:
    """Nombre de habilidad en minúsculas, para que «Python» y «python» sean el mismo nodo."""
    return validar_texto(valor, "habilidad", 50).lower()
