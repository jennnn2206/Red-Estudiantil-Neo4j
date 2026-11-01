"""Lectura segura del teclado: ninguna función falla por teclear mal."""
from __future__ import annotations

from typing import Optional, Sequence


class EntradaCancelada(Exception):
    """El usuario cerró la entrada (Ctrl+D) o la interrumpió (Ctrl+C)."""


def pedir_texto(mensaje: str) -> str:
    """Pide una línea de texto tal cual (sin quitar espacios)."""
    try:
        return input(mensaje)
    except (EOFError, KeyboardInterrupt, UnicodeError) as causa:
        print()
        raise EntradaCancelada() from causa


def pedir_opcion(mensaje: str, validas: Sequence[str]) -> str:
    """Repite la pregunta hasta que se escriba una opción válida."""
    while True:
        respuesta = pedir_texto(mensaje).strip()
        if respuesta in validas:
            return respuesta
        print(f"[ERROR] Opción '{respuesta}' no válida. Opciones: {', '.join(validas)}.")


def pedir_opcional(mensaje: str) -> Optional[str]:
    """ENTER vacío devuelve None (= dejar el valor actual)."""
    respuesta = pedir_texto(mensaje)
    return None if respuesta == "" else respuesta


def confirmar(mensaje: str) -> bool:
    """Pregunta sí/no hasta recibir una respuesta clara."""
    while True:
        respuesta = pedir_texto(f"{mensaje} (s/n): ").strip().lower()
        if respuesta in ("s", "si", "sí"):
            return True
        if respuesta in ("n", "no"):
            return False
        print("[ERROR] Responde 's' para sí o 'n' para no.")
