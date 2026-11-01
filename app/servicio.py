"""Reglas de negocio: valida los datos y coordina al repositorio."""
from __future__ import annotations

from typing import Optional

from . import validaciones as val
from .errores import ErrorDeValidacion, ErrorDuplicado, ErrorNoEncontrado
from .repositorio import RepositorioRed

LIMITE_POR_DEFECTO = 5


class ServicioRed:
    """Casos de uso de la red de estudiantes."""

    def __init__(self, repositorio: RepositorioRed) -> None:
        self._repo = repositorio

    # --- utilidades internas ------------------------------------------
    def _exigir_estudiante(self, correo: Optional[str]) -> dict:
        """Valida el correo y comprueba en la base que el estudiante exista."""
        correo_ok = val.validar_correo(correo)
        estudiante = self._repo.obtener_estudiante(correo_ok)
        if estudiante is None:
            raise ErrorNoEncontrado(f"No existe ningún estudiante con el correo '{correo_ok}'.")
        return estudiante

    def _exigir_materia(self, codigo: Optional[str]) -> dict:
        codigo_ok = val.validar_codigo_materia(codigo)
        materia = self._repo.obtener_materia(codigo_ok)
        if materia is None:
            raise ErrorNoEncontrado(f"No existe ninguna materia con el código '{codigo_ok}'.")
        return materia

    @staticmethod
    def _limite(valor: object) -> int:
        return val.validar_entero(valor, "límite", 1, 50)

    # --- estudiantes (CRUD) -------------------------------------------
    def crear_estudiante(self, correo: str, nombre: str, carrera: str, semestre: object) -> dict:
        correo_ok = val.validar_correo(correo)
        nombre_ok = val.validar_texto(nombre, "nombre")
        carrera_ok = val.validar_texto(carrera, "carrera")
        semestre_ok = val.validar_entero(semestre, "semestre", 1, 12)
        if self._repo.obtener_estudiante(correo_ok) is not None:
            raise ErrorDuplicado(f"Ya existe un estudiante con el correo '{correo_ok}'.")
        return self._repo.crear_estudiante(correo_ok, nombre_ok, carrera_ok, semestre_ok)

    def obtener_estudiante(self, correo: str) -> dict:
        return self._exigir_estudiante(correo)

    def listar_estudiantes(self) -> list[dict]:
        return self._repo.listar_estudiantes()

    def buscar_estudiantes(self, texto: str) -> list[dict]:
        return self._repo.buscar_estudiantes(val.validar_texto(texto, "texto a buscar"))

    def actualizar_estudiante(
        self,
        correo: str,
        nombre: Optional[str] = None,
        carrera: Optional[str] = None,
        semestre: Optional[object] = None,
    ) -> dict:
        """Modifica solo los campos recibidos (None = dejar igual). El correo no cambia."""
        actual = self._exigir_estudiante(correo)
        cambios: dict = {}
        if nombre is not None:
            cambios["nombre"] = val.validar_texto(nombre, "nombre")
        if carrera is not None:
            cambios["carrera"] = val.validar_texto(carrera, "carrera")
        if semestre is not None:
            cambios["semestre"] = val.validar_entero(semestre, "semestre", 1, 12)
        cambios = {k: v for k, v in cambios.items() if actual.get(k) != v}
        if not cambios:
            raise ErrorDeValidacion("No hay cambios que guardar.")
        actualizado = self._repo.actualizar_estudiante(actual["correo"], cambios)
        if actualizado is None:  # alguien lo borró entre las dos consultas
            raise ErrorNoEncontrado("El estudiante dejó de existir.")
        return actualizado

    def eliminar_estudiante(self, correo: str) -> dict:
        """Borra al estudiante y todas sus relaciones (DETACH DELETE)."""
        actual = self._exigir_estudiante(correo)
        resultado = self._repo.eliminar_estudiante(actual["correo"])
        if resultado is None:
            raise ErrorNoEncontrado("El estudiante dejó de existir.")
        return resultado

    # --- materias ------------------------------------------------------
    def crear_materia(self, codigo: str, nombre: str) -> dict:
        codigo_ok = val.validar_codigo_materia(codigo)
        nombre_ok = val.validar_texto(nombre, "nombre")
        if self._repo.obtener_materia(codigo_ok) is not None:
            raise ErrorDuplicado(f"Ya existe la materia '{codigo_ok}'.")
        return self._repo.crear_materia(codigo_ok, nombre_ok)

    def listar_materias(self) -> list[dict]:
        return self._repo.listar_materias()

    # --- relaciones ----------------------------------------------------
    def agregar_amistad(self, correo_a: str, correo_b: str) -> tuple[str, str]:
        a = self._exigir_estudiante(correo_a)
        b = self._exigir_estudiante(correo_b)
        if a["correo"] == b["correo"]:
            raise ErrorDeValidacion("Un estudiante no puede ser amigo de sí mismo.")
        if self._repo.existe_amistad(a["correo"], b["correo"]):
            raise ErrorDuplicado(f"{a['nombre']} y {b['nombre']} ya son amigos.")
        self._repo.agregar_amistad(a["correo"], b["correo"])
        return a["nombre"], b["nombre"]

    def eliminar_amistad(self, correo_a: str, correo_b: str) -> tuple[str, str]:
        a = self._exigir_estudiante(correo_a)
        b = self._exigir_estudiante(correo_b)
        if not self._repo.eliminar_amistad(a["correo"], b["correo"]):
            raise ErrorNoEncontrado(f"{a['nombre']} y {b['nombre']} no son amigos.")
        return a["nombre"], b["nombre"]

    def listar_amigos(self, correo: str) -> list[dict]:
        return self._repo.listar_amigos(self._exigir_estudiante(correo)["correo"])

    def inscribir_materia(self, correo: str, codigo: str, periodo: str) -> None:
        estudiante = self._exigir_estudiante(correo)
        materia = self._exigir_materia(codigo)
        self._repo.inscribir_materia(
            estudiante["correo"], materia["codigo"], val.validar_periodo(periodo)
        )

    def dar_de_baja_materia(self, correo: str, codigo: str) -> None:
        estudiante = self._exigir_estudiante(correo)
        materia = self._exigir_materia(codigo)
        if not self._repo.dar_de_baja_materia(estudiante["correo"], materia["codigo"]):
            raise ErrorNoEncontrado(f"{estudiante['nombre']} no cursa {materia['nombre']}.")

    def materias_de(self, correo: str) -> list[dict]:
        return self._repo.materias_de(self._exigir_estudiante(correo)["correo"])

    def agregar_habilidad(self, correo: str, habilidad: str, nivel: object) -> None:
        estudiante = self._exigir_estudiante(correo)
        self._repo.agregar_habilidad(
            estudiante["correo"],
            val.validar_habilidad(habilidad),
            val.validar_entero(nivel, "nivel", 1, 5),
        )

    def quitar_habilidad(self, correo: str, habilidad: str) -> None:
        estudiante = self._exigir_estudiante(correo)
        nombre = val.validar_habilidad(habilidad)
        if not self._repo.quitar_habilidad(estudiante["correo"], nombre):
            raise ErrorNoEncontrado(f"{estudiante['nombre']} no tiene la habilidad '{nombre}'.")

    def habilidades_de(self, correo: str) -> list[dict]:
        return self._repo.habilidades_de(self._exigir_estudiante(correo)["correo"])

    # --- consultas de grafo -------------------------------------------
    def sugerir_amigos(self, correo: str, limite: object = LIMITE_POR_DEFECTO) -> list[dict]:
        estudiante = self._exigir_estudiante(correo)
        return self._repo.sugerir_amigos(estudiante["correo"], self._limite(limite))

    def camino_mas_corto(self, origen: str, destino: str) -> dict:
        a = self._exigir_estudiante(origen)
        b = self._exigir_estudiante(destino)
        if a["correo"] == b["correo"]:
            raise ErrorDeValidacion("Elige dos estudiantes distintos.")
        camino = self._repo.camino_mas_corto(a["correo"], b["correo"])
        if camino is None:
            raise ErrorNoEncontrado(
                f"No hay conexión entre {a['nombre']} y {b['nombre']} en hasta 6 grados de amistad."
            )
        return camino

    def amigos_en_comun(self, correo_a: str, correo_b: str) -> list[dict]:
        a = self._exigir_estudiante(correo_a)
        b = self._exigir_estudiante(correo_b)
        if a["correo"] == b["correo"]:
            raise ErrorDeValidacion("Elige dos estudiantes distintos.")
        return self._repo.amigos_en_comun(a["correo"], b["correo"])

    def vecindad(self, correo: str, grados: object) -> list[dict]:
        grados_ok = val.validar_entero(grados, "grados", 1, 4)
        estudiante = self._exigir_estudiante(correo)
        return self._repo.vecindad(estudiante["correo"], grados_ok)

    def companeros_de_materia(self, correo: str) -> list[dict]:
        return self._repo.companeros_de_materia(self._exigir_estudiante(correo)["correo"])

    def sugerir_equipo(self, correo: str, codigo: str, limite: object = LIMITE_POR_DEFECTO) -> list[dict]:
        estudiante = self._exigir_estudiante(correo)
        materia = self._exigir_materia(codigo)
        return self._repo.sugerir_equipo(
            estudiante["correo"], materia["codigo"], self._limite(limite)
        )

    def mas_conectados(self, limite: object = LIMITE_POR_DEFECTO) -> list[dict]:
        return self._repo.mas_conectados(self._limite(limite))

    def habilidades_populares(self, limite: object = LIMITE_POR_DEFECTO) -> list[dict]:
        return self._repo.habilidades_populares(self._limite(limite))
