"""Repositorio: ejecuta las consultas del catálogo y devuelve datos simples.

No valida reglas de negocio; solo traduce llamadas de Python a Cypher.
"""
from __future__ import annotations

from typing import Any, Optional

from . import consultas as c
from .conexion import ConexionNeo4j


class RepositorioRed:
    """Acceso a los datos del grafo de estudiantes."""

    def __init__(self, conexion: ConexionNeo4j) -> None:
        self._bd = conexion

    # --- esquema -------------------------------------------------------
    def crear_esquema(self) -> None:
        """Crea las restricciones de unicidad si no existen."""
        for sentencia in c.ESQUEMA:
            self._bd.escribir(sentencia)

    # --- estudiantes ---------------------------------------------------
    def crear_estudiante(self, correo: str, nombre: str, carrera: str, semestre: int) -> dict:
        filas = self._bd.escribir(
            c.CREAR_ESTUDIANTE,
            {"correo": correo, "nombre": nombre, "carrera": carrera, "semestre": semestre},
        )
        return filas[0]["estudiante"]

    def obtener_estudiante(self, correo: str) -> Optional[dict]:
        filas = self._bd.leer(c.OBTENER_ESTUDIANTE, {"correo": correo})
        return filas[0]["estudiante"] if filas else None

    def listar_estudiantes(self) -> list[dict]:
        return [f["estudiante"] for f in self._bd.leer(c.LISTAR_ESTUDIANTES)]

    def buscar_estudiantes(self, texto: str) -> list[dict]:
        return [f["estudiante"] for f in self._bd.leer(c.BUSCAR_ESTUDIANTES, {"texto": texto})]

    def actualizar_estudiante(self, correo: str, cambios: dict) -> Optional[dict]:
        filas = self._bd.escribir(c.ACTUALIZAR_ESTUDIANTE, {"correo": correo, "cambios": cambios})
        return filas[0]["estudiante"] if filas else None

    def eliminar_estudiante(self, correo: str) -> Optional[dict]:
        filas = self._bd.escribir(c.ELIMINAR_ESTUDIANTE, {"correo": correo})
        return filas[0] if filas else None

    # --- materias ------------------------------------------------------
    def crear_materia(self, codigo: str, nombre: str) -> dict:
        filas = self._bd.escribir(c.CREAR_MATERIA, {"codigo": codigo, "nombre": nombre})
        return filas[0]["materia"]

    def obtener_materia(self, codigo: str) -> Optional[dict]:
        filas = self._bd.leer(c.OBTENER_MATERIA, {"codigo": codigo})
        return filas[0]["materia"] if filas else None

    def listar_materias(self) -> list[dict]:
        return [f["materia"] for f in self._bd.leer(c.LISTAR_MATERIAS)]

    # --- relaciones ----------------------------------------------------
    def existe_amistad(self, correo_a: str, correo_b: str) -> bool:
        filas = self._bd.leer(c.EXISTE_AMISTAD, {"correo_a": correo_a, "correo_b": correo_b})
        return bool(filas) and filas[0]["total"] > 0

    def agregar_amistad(self, correo_a: str, correo_b: str) -> None:
        self._bd.escribir(c.AGREGAR_AMISTAD, {"correo_a": correo_a, "correo_b": correo_b})

    def eliminar_amistad(self, correo_a: str, correo_b: str) -> bool:
        filas = self._bd.escribir(c.ELIMINAR_AMISTAD, {"correo_a": correo_a, "correo_b": correo_b})
        return bool(filas)

    def listar_amigos(self, correo: str) -> list[dict]:
        return self._bd.leer(c.LISTAR_AMIGOS, {"correo": correo})

    def inscribir_materia(self, correo: str, codigo: str, periodo: str) -> None:
        self._bd.escribir(
            c.INSCRIBIR_MATERIA, {"correo": correo, "codigo": codigo, "periodo": periodo}
        )

    def dar_de_baja_materia(self, correo: str, codigo: str) -> bool:
        return bool(self._bd.escribir(c.BAJA_MATERIA, {"correo": correo, "codigo": codigo}))

    def materias_de(self, correo: str) -> list[dict]:
        return self._bd.leer(c.MATERIAS_DE_ESTUDIANTE, {"correo": correo})

    def agregar_habilidad(self, correo: str, habilidad: str, nivel: int) -> None:
        self._bd.escribir(
            c.AGREGAR_HABILIDAD, {"correo": correo, "habilidad": habilidad, "nivel": nivel}
        )

    def quitar_habilidad(self, correo: str, habilidad: str) -> bool:
        return bool(self._bd.escribir(c.QUITAR_HABILIDAD, {"correo": correo, "habilidad": habilidad}))

    def habilidades_de(self, correo: str) -> list[dict]:
        return self._bd.leer(c.HABILIDADES_DE_ESTUDIANTE, {"correo": correo})

    # --- consultas de grafo -------------------------------------------
    def sugerir_amigos(self, correo: str, limite: int) -> list[dict]:
        return self._bd.leer(c.SUGERIR_AMIGOS, {"correo": correo, "limite": limite})

    def camino_mas_corto(self, origen: str, destino: str) -> Optional[dict]:
        filas = self._bd.leer(c.CAMINO_MAS_CORTO, {"origen": origen, "destino": destino})
        return filas[0] if filas else None

    def amigos_en_comun(self, correo_a: str, correo_b: str) -> list[dict]:
        return self._bd.leer(c.AMIGOS_EN_COMUN, {"correo_a": correo_a, "correo_b": correo_b})

    def vecindad(self, correo: str, grados: int) -> list[dict]:
        consulta = c.VECINDAD.replace("__GRADOS__", str(int(grados)))
        return self._bd.leer(consulta, {"correo": correo})

    def companeros_de_materia(self, correo: str) -> list[dict]:
        return self._bd.leer(c.COMPANEROS_DE_MATERIA, {"correo": correo})

    def sugerir_equipo(self, correo: str, codigo: str, limite: int) -> list[dict]:
        return self._bd.leer(
            c.SUGERIR_EQUIPO, {"correo": correo, "codigo": codigo, "limite": limite}
        )

    def mas_conectados(self, limite: int) -> list[dict]:
        return self._bd.leer(c.MAS_CONECTADOS, {"limite": limite})

    def habilidades_populares(self, limite: int) -> list[dict]:
        return self._bd.leer(c.HABILIDADES_POPULARES, {"limite": limite})

    # --- carga inicial -------------------------------------------------
    def sembrar(self, datos: dict[str, list[dict[str, Any]]]) -> None:
        """Inserta materias, estudiantes, amistades, inscripciones y habilidades."""
        self._bd.escribir(c.SEMILLA_MATERIAS, {"materias": datos["materias"]})
        self._bd.escribir(c.SEMILLA_ESTUDIANTES, {"estudiantes": datos["estudiantes"]})
        self._bd.escribir(c.SEMILLA_AMISTADES, {"amistades": datos["amistades"]})
        self._bd.escribir(c.SEMILLA_INSCRIPCIONES, {"inscripciones": datos["inscripciones"]})
        self._bd.escribir(c.SEMILLA_HABILIDADES, {"habilidades": datos["habilidades"]})

    def reiniciar_datos(self) -> None:
        """Borra los estudiantes, materias y habilidades de esta aplicación."""
        self._bd.escribir(c.REINICIAR_DATOS)

    def contar_datos(self) -> dict:
        return self._bd.leer(c.CONTAR_DATOS)[0]
