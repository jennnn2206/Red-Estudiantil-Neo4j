"""Lectura de la configuración de conexión desde variables de entorno.

Las credenciales NUNCA van escritas en el código: se leen del entorno o de un
archivo ``.env`` (que está en .gitignore para no subirlo al repositorio).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv

from .errores import ErrorDeConfiguracion

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
# Esquemas con cifrado TLS, los que usa un servicio administrado como AuraDB.
ESQUEMAS_NUBE = {"neo4j+s", "neo4j+ssc", "bolt+s", "bolt+ssc"}
HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


@dataclass(frozen=True)
class ConfiguracionNeo4j:
    """Datos para conectarse a la instancia de Neo4j."""

    uri: str
    usuario: str
    clave: str = field(repr=False)  # repr=False: la contraseña no sale en impresiones
    base_de_datos: str = "neo4j"


def _validar_uri(uri: str) -> None:
    """Exige una URI de nube con TLS; rechaza localhost (lo pide la tarea)."""
    analizada = urlparse(uri)
    if analizada.scheme not in ESQUEMAS_NUBE:
        raise ErrorDeConfiguracion(
            f"NEO4J_URI debe empezar con neo4j+s:// (AuraDB). Recibido: '{analizada.scheme}://'."
        )
    if not analizada.hostname or analizada.hostname in HOSTS_LOCALES:
        raise ErrorDeConfiguracion(
            "NEO4J_URI apunta a una máquina local. La base de datos debe estar en la nube "
            "(Neo4j AuraDB), por ejemplo neo4j+s://xxxxxxxx.databases.neo4j.io."
        )


def cargar_configuracion(ruta_env: Optional[Path] = None) -> ConfiguracionNeo4j:
    """Lee NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD y NEO4J_DATABASE.

    Las variables ya definidas en el sistema tienen prioridad sobre el .env.
    """
    load_dotenv(ruta_env or RAIZ_PROYECTO / ".env")
    uri = os.getenv("NEO4J_URI", "").strip()
    usuario = os.getenv("NEO4J_USERNAME", "").strip()
    clave = os.getenv("NEO4J_PASSWORD", "").strip()
    base = os.getenv("NEO4J_DATABASE", "").strip() or "neo4j"

    faltantes = [
        nombre
        for nombre, valor in (
            ("NEO4J_URI", uri),
            ("NEO4J_USERNAME", usuario),
            ("NEO4J_PASSWORD", clave),
        )
        if not valor
    ]
    if faltantes:
        raise ErrorDeConfiguracion(
            f"Faltan variables de entorno: {', '.join(faltantes)}. "
            "Copia .env.example como .env y completa los datos de tu instancia de AuraDB."
        )
    _validar_uri(uri)
    return ConfiguracionNeo4j(uri=uri, usuario=usuario, clave=clave, base_de_datos=base)
