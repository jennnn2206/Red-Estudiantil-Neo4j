"""Punto de entrada: lee la configuración, abre la conexión y lanza el menú.

Uso:
    python3 main.py
"""
from __future__ import annotations

import sys

from app.config import cargar_configuracion
from app.conexion import ConexionNeo4j
from app.errores import ErrorDeAplicacion
from app.menu import ejecutar_aplicacion
from app.repositorio import RepositorioRed
from app.servicio import ServicioRed


def main() -> int:
    """Devuelve 0 si todo salió bien y 1 si no se pudo iniciar."""
    try:
        configuracion = cargar_configuracion()
        with ConexionNeo4j(configuracion) as conexion:
            repositorio = RepositorioRed(conexion)
            repositorio.crear_esquema()  # idempotente
            ejecutar_aplicacion(ServicioRed(repositorio))
    except ErrorDeAplicacion as error:
        print(f"[ERROR] {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
