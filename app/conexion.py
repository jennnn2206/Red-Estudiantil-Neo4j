"""Conexión con Neo4j AuraDB usando el driver oficial (paquete ``neo4j``).

Esta es la única capa que conoce el driver. Traduce sus excepciones a las
propias de la aplicación, para que el resto del código no dependa de él.
"""
from __future__ import annotations

from typing import Any, Optional

from neo4j import Driver, GraphDatabase, RoutingControl
from neo4j.exceptions import (
    AuthError,
    ConstraintError,
    DriverError,
    Neo4jError,
    ServiceUnavailable,
    SessionExpired,
)

from .config import ConfiguracionNeo4j
from .errores import ErrorDeBaseDeDatos, ErrorDeConexion, ErrorDuplicado


class ConexionNeo4j:
    """Abre, usa y cierra la conexión remota con la base de datos."""

    def __init__(self, configuracion: ConfiguracionNeo4j) -> None:
        self._configuracion = configuracion
        self._driver: Optional[Driver] = None

    def abrir(self) -> None:
        """Crea el driver y verifica que la instancia en la nube responda."""
        if self._driver is not None:
            return
        driver = None
        try:
            driver = GraphDatabase.driver(
                self._configuracion.uri,
                auth=(self._configuracion.usuario, self._configuracion.clave),
            )
            driver.verify_connectivity()
        except AuthError as error:
            if driver is not None:
                driver.close()
            raise ErrorDeConexion(
                "La instancia rechazó el usuario o la contraseña. Revisa NEO4J_USERNAME "
                "y NEO4J_PASSWORD en tu archivo .env."
            ) from error
        except (DriverError, Neo4jError, OSError) as error:
            if driver is not None:
                driver.close()
            raise ErrorDeConexion(
                "No se pudo conectar con la instancia en la nube. Verifica tu internet y que "
                "la instancia esté en estado 'Running' en console.neo4j.io (las gratuitas se "
                f"pausan por inactividad). Detalle: {error}"
            ) from error
        self._driver = driver

    def cerrar(self) -> None:
        """Libera la conexión (se puede llamar varias veces)."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def __enter__(self) -> "ConexionNeo4j":
        self.abrir()
        return self

    def __exit__(self, *_: Any) -> None:
        self.cerrar()

    def informacion_servidor(self) -> dict:
        """Dirección, versión y protocolo del servidor (para verificar la conexión)."""
        if self._driver is None:
            raise ErrorDeConexion("La conexión no está abierta.")
        info = self._driver.get_server_info()
        return {
            "direccion": str(info.address),
            "agente": info.agent,
            "protocolo": str(info.protocol_version),
        }

    def leer(self, consulta: str, parametros: Optional[dict] = None) -> list[dict]:
        """Ejecuta una consulta de solo lectura y devuelve filas como diccionarios."""
        return self._ejecutar(consulta, parametros, RoutingControl.READ)

    def escribir(self, consulta: str, parametros: Optional[dict] = None) -> list[dict]:
        """Ejecuta una consulta que modifica datos (transacción confirmada al terminar)."""
        return self._ejecutar(consulta, parametros, RoutingControl.WRITE)

    def _ejecutar(self, consulta: str, parametros: Optional[dict], ruta: Any) -> list[dict]:
        """Envía la consulta con parámetros (nunca se concatenan datos al texto)."""
        if self._driver is None:
            raise ErrorDeConexion("La conexión no está abierta.")
        try:
            resultado = self._driver.execute_query(
                consulta,
                parameters_=parametros or {},
                routing_=ruta,
                database_=self._configuracion.base_de_datos,
            )
        except ConstraintError as error:
            raise ErrorDuplicado("Ya existe un registro con ese valor único.") from error
        except (ServiceUnavailable, SessionExpired) as error:
            raise ErrorDeConexion(
                "Se perdió la conexión con la instancia en la nube. Intenta de nuevo."
            ) from error
        except Neo4jError as error:
            raise ErrorDeBaseDeDatos(f"Neo4j rechazó la consulta ({error.code}): {error.message}") from error
        return [registro.data() for registro in resultado.records]
