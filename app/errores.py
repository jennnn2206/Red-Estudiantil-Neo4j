"""Errores propios de la aplicación.

La interfaz solo captura ``ErrorDeAplicacion`` para mostrar un mensaje claro
sin cerrar el programa.
"""


class ErrorDeAplicacion(Exception):
    """Clase base de todos los errores controlados."""


class ErrorDeConfiguracion(ErrorDeAplicacion):
    """Faltan o son inválidas las variables de entorno de conexión."""


class ErrorDeConexion(ErrorDeAplicacion):
    """No se pudo conectar con la base de datos en la nube."""


class ErrorDeBaseDeDatos(ErrorDeAplicacion):
    """Neo4j rechazó la consulta (sintaxis, permisos, etc.)."""


class ErrorDeValidacion(ErrorDeAplicacion):
    """Un dato de entrada es inválido (vacío, formato, rango)."""


class ErrorDuplicado(ErrorDeAplicacion):
    """El registro ya existe (viola una restricción de unicidad)."""


class ErrorNoEncontrado(ErrorDeAplicacion):
    """El registro buscado no existe."""
