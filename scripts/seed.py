"""Carga los datos iniciales en la base de datos en la nube.

Uso (desde la carpeta del proyecto):
    python3 -m scripts.seed              # agrega o actualiza los datos de ejemplo
    python3 -m scripts.seed --reiniciar  # borra antes los nodos de esta app
"""
from __future__ import annotations

import sys

from app.config import cargar_configuracion
from app.conexion import ConexionNeo4j
from app.entrada import confirmar
from app.errores import ErrorDeAplicacion
from app.repositorio import RepositorioRed
from scripts.datos_iniciales import obtener_datos


def main(argumentos: list[str]) -> int:
    reiniciar = "--reiniciar" in argumentos
    try:
        with ConexionNeo4j(cargar_configuracion()) as conexion:
            repositorio = RepositorioRed(conexion)
            repositorio.crear_esquema()
            if reiniciar:
                if not confirmar("Se borrarán TODOS los Estudiantes, Materias y Habilidades. ¿Continuar?"):
                    print("Cancelado.")
                    return 0
                repositorio.reiniciar_datos()
                print("[OK] Datos anteriores borrados.")
            repositorio.sembrar(obtener_datos())
            print("[OK] Datos iniciales cargados. Resumen en la nube:")
            for nombre, total in repositorio.contar_datos().items():
                print(f"  {nombre:<14}{total}")
    except ErrorDeAplicacion as error:
        print(f"[ERROR] {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
