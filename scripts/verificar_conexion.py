"""Comprueba que las credenciales del .env funcionan y que la instancia responde.

Uso:
    python3 -m scripts.verificar_conexion
"""
from __future__ import annotations

import sys

from app.config import cargar_configuracion
from app.conexion import ConexionNeo4j
from app.errores import ErrorDeAplicacion


def main() -> int:
    try:
        configuracion = cargar_configuracion()
        with ConexionNeo4j(configuracion) as conexion:
            info = conexion.informacion_servidor()
            respuesta = conexion.leer("RETURN 'conexión exitosa' AS mensaje")[0]["mensaje"]
    except ErrorDeAplicacion as error:
        print(f"[ERROR] {error}")
        return 1
    print(f"[OK] {respuesta}")
    print(f"  Servidor : {info['direccion']}")
    print(f"  Versión  : {info['agente']}")
    print(f"  Base     : {configuracion.base_de_datos}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
