"""API REST y servidor del frontend web de UniRed.

Uso (desde la carpeta del proyecto):
    uvicorn app.web.api:app --reload
y abrir http://127.0.0.1:8000

Capas: esta API solo traduce HTTP <-> ServicioRed. Las reglas de negocio y las
validaciones reales siguen en ``app/servicio.py`` y ``app/validaciones.py``.

Los endpoints son funciones ``def`` normales (no ``async``) porque el driver de
Neo4j es síncrono; FastAPI las ejecuta en un hilo aparte sin bloquear el servidor.
Los correos llevan ``@`` y puntos, por eso viajan como parámetros de consulta
(``?correo=...``) o en el cuerpo JSON, nunca dentro de la ruta.
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import RAIZ_PROYECTO, cargar_configuracion
from ..conexion import ConexionNeo4j
from ..errores import (
    ErrorDeAplicacion,
    ErrorDeBaseDeDatos,
    ErrorDeConexion,
    ErrorDeConfiguracion,
    ErrorDeValidacion,
    ErrorDuplicado,
    ErrorNoEncontrado,
)
from ..repositorio import RepositorioRed
from ..servicio import LIMITE_POR_DEFECTO, ServicioRed

CARPETA_ESTATICA = RAIZ_PROYECTO / "web" / "static"
registro = logging.getLogger("unired.web")

# Excepción propia -> código HTTP. El orden importa: se usa la primera que coincida.
CODIGOS_HTTP: list[tuple[type[ErrorDeAplicacion], int]] = [
    (ErrorDeValidacion, 422),
    (ErrorNoEncontrado, 404),
    (ErrorDuplicado, 409),
    (ErrorDeConexion, 503),
    (ErrorDeBaseDeDatos, 500),
    (ErrorDeConfiguracion, 500),
]


# ----------------------------------------------------------------------
# Cuerpos JSON de entrada. Los campos numéricos se aceptan como texto o
# número (Any) para que la validación y sus mensajes en español los dé el
# servicio, igual que en la consola.
# ----------------------------------------------------------------------
class EstudianteNuevo(BaseModel):
    correo: Optional[str] = None
    nombre: Optional[str] = None
    carrera: Optional[str] = None
    semestre: Any = None


class EstudianteCambios(BaseModel):
    nombre: Optional[str] = None
    carrera: Optional[str] = None
    semestre: Any = None


class ParEstudiantes(BaseModel):
    correo_a: Optional[str] = None
    correo_b: Optional[str] = None


class MateriaNueva(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None


class Inscripcion(BaseModel):
    correo: Optional[str] = None
    codigo: Optional[str] = None
    periodo: Optional[str] = None


class HabilidadDeEstudiante(BaseModel):
    correo: Optional[str] = None
    habilidad: Optional[str] = None
    nivel: Any = None


# ----------------------------------------------------------------------
# Fábrica de la aplicación
# ----------------------------------------------------------------------
class GestorConexion:
    """Dueño de la única conexión (driver) del servidor.

    Se abre al arrancar. Si en ese momento la instancia en la nube no responde
    (por ejemplo, AuraDB Free pausada), el servidor arranca de todos modos: la
    API responde 503 con el motivo y vuelve a intentar conectarse en una
    petición posterior (como máximo una vez cada ``ESPERA_REINTENTO`` segundos),
    así no hace falta reiniciar uvicorn cuando la instancia vuelve a estar activa.
    """

    ESPERA_REINTENTO = 10.0

    def __init__(self) -> None:
        self._conexion: Optional[ConexionNeo4j] = None
        self._servicio: Optional[ServicioRed] = None
        self._ultimo_error: Optional[ErrorDeAplicacion] = None
        self._ultimo_intento = 0.0
        self._candado = threading.Lock()

    def conectar(self) -> ServicioRed:
        """Abre la conexión, crea el esquema y devuelve el servicio compartido."""
        with self._candado:
            if self._servicio is not None:
                return self._servicio
            self._ultimo_intento = time.monotonic()
            conexion = ConexionNeo4j(cargar_configuracion())
            try:
                conexion.abrir()
                repositorio = RepositorioRed(conexion)
                repositorio.crear_esquema()  # idempotente
            except ErrorDeAplicacion as error:
                conexion.cerrar()
                self._ultimo_error = error
                raise
            self._conexion, self._servicio, self._ultimo_error = conexion, ServicioRed(repositorio), None
            registro.info("Conectado a Neo4j AuraDB; esquema verificado.")
            return self._servicio

    def obtener_servicio(self) -> ServicioRed:
        """Servicio listo para usar; reintenta la conexión si hace falta."""
        if self._servicio is not None:
            return self._servicio
        reciente = time.monotonic() - self._ultimo_intento < self.ESPERA_REINTENTO
        if reciente and self._ultimo_error is not None:
            raise self._ultimo_error
        return self.conectar()

    def cerrar(self) -> None:
        with self._candado:
            if self._conexion is not None:
                self._conexion.cerrar()
                registro.info("Conexión con Neo4j cerrada.")
            self._conexion = self._servicio = None


def crear_app(servicio: Optional[ServicioRed] = None) -> FastAPI:
    """Construye la aplicación FastAPI.

    Sin argumentos abre una única conexión a AuraDB al arrancar y la cierra al
    apagar (lifespan). Las pruebas pasan un ``servicio`` simulado y entonces no
    se toca la base de datos.
    """

    @asynccontextmanager
    async def ciclo_de_vida(aplicacion: FastAPI):
        if servicio is not None:
            aplicacion.state.servicio = servicio
            yield
            return
        gestor = GestorConexion()
        aplicacion.state.gestor = gestor
        try:
            gestor.conectar()
        except ErrorDeAplicacion as error:
            registro.error("No se pudo abrir la conexión al arrancar: %s", error)
            registro.error("El servidor sigue activo; la API responderá 503 hasta que la base responda.")
        try:
            yield
        finally:
            gestor.cerrar()

    aplicacion = FastAPI(
        title="UniRed API",
        description="Red de estudiantes sobre Neo4j AuraDB.",
        version="1.0",
        lifespan=ciclo_de_vida,
    )
    _registrar_manejadores_de_error(aplicacion)
    aplicacion.include_router(_crear_rutas())

    @aplicacion.get("/", include_in_schema=False)
    def inicio() -> FileResponse:
        return FileResponse(CARPETA_ESTATICA / "index.html")

    aplicacion.mount("/static", StaticFiles(directory=CARPETA_ESTATICA), name="static")
    return aplicacion


def _registrar_manejadores_de_error(aplicacion: FastAPI) -> None:
    """Todas las respuestas de error son JSON: {"error": tipo, "mensaje": texto}."""

    @aplicacion.exception_handler(ErrorDeAplicacion)
    def error_de_aplicacion(_: Request, error: ErrorDeAplicacion) -> JSONResponse:
        codigo = next((c for tipo, c in CODIGOS_HTTP if isinstance(error, tipo)), 500)
        return JSONResponse(
            status_code=codigo,
            content={"error": type(error).__name__, "mensaje": str(error)},
        )

    @aplicacion.exception_handler(RequestValidationError)
    def error_de_peticion(_: Request, error: RequestValidationError) -> JSONResponse:
        # Errores de forma de la petición (falta un parámetro, JSON mal formado).
        partes = []
        for detalle in error.errors():
            campo = ".".join(str(x) for x in detalle.get("loc", []) if x not in ("query", "body"))
            if detalle.get("type") == "missing":
                partes.append(f"falta el dato '{campo}'")
            else:
                partes.append(f"el dato '{campo}' no es válido")
        mensaje = "Petición inválida: " + "; ".join(partes) + "." if partes else "Petición inválida."
        return JSONResponse(
            status_code=422, content={"error": "ErrorDeValidacion", "mensaje": mensaje}
        )

    @aplicacion.exception_handler(Exception)
    def error_inesperado(_: Request, error: Exception) -> JSONResponse:
        registro.error("Error inesperado en la API", exc_info=error)
        return JSONResponse(
            status_code=500,
            content={
                "error": "ErrorInesperado",
                "mensaje": f"Ocurrió un problema inesperado en el servidor ({type(error).__name__}).",
            },
        )


def obtener_servicio(request: Request) -> ServicioRed:
    """Dependencia: el servicio compartido creado en el arranque."""
    servicio = getattr(request.app.state, "servicio", None)
    if servicio is not None:
        return servicio
    gestor: Optional[GestorConexion] = getattr(request.app.state, "gestor", None)
    if gestor is None:
        raise ErrorDeConexion("El servidor no tiene conexión con la base de datos.")
    return gestor.obtener_servicio()


def _ok(mensaje: str, **datos: Any) -> dict:
    """Respuesta estándar de las operaciones que modifican datos."""
    return {"mensaje": mensaje, **datos}


# ----------------------------------------------------------------------
# Rutas /api
# ----------------------------------------------------------------------
def _crear_rutas() -> APIRouter:
    """Define todos los endpoints bajo /api."""
    r = APIRouter(prefix="/api")
    S = Depends(obtener_servicio)
    LIMITE = Query(str(LIMITE_POR_DEFECTO), description="Máximo de resultados (1 a 50)")

    # --- estado ---------------------------------------------------------
    @r.get("/salud", tags=["estado"])
    def salud(s: ServicioRed = S) -> dict:
        """Comprueba que la API está arriba y responde la base de datos."""
        return {"estado": "ok", "estudiantes": len(s.listar_estudiantes())}

    # --- estudiantes ----------------------------------------------------
    @r.get("/estudiantes", tags=["estudiantes"])
    def listar_estudiantes(q: Optional[str] = None, s: ServicioRed = S) -> list[dict]:
        """Lista todos los estudiantes, o filtra por nombre si se envía ``q``."""
        if q is not None and q.strip():
            return s.buscar_estudiantes(q)
        return s.listar_estudiantes()

    @r.post("/estudiantes", status_code=201, tags=["estudiantes"])
    def crear_estudiante(datos: EstudianteNuevo, s: ServicioRed = S) -> dict:
        e = s.crear_estudiante(datos.correo, datos.nombre, datos.carrera, datos.semestre)
        return _ok(f"Estudiante creado: {e['nombre']} ({e['correo']}).", estudiante=e)

    @r.get("/estudiantes/detalle", tags=["estudiantes"])
    def obtener_estudiante(correo: str, s: ServicioRed = S) -> dict:
        return s.obtener_estudiante(correo)

    @r.get("/estudiantes/perfil", tags=["estudiantes"])
    def perfil(correo: str, s: ServicioRed = S) -> dict:
        """Estudiante con sus amigos, materias y habilidades."""
        return s.perfil(correo)

    @r.patch("/estudiantes", tags=["estudiantes"])
    def modificar_estudiante(correo: str, datos: EstudianteCambios, s: ServicioRed = S) -> dict:
        """Cambio parcial: solo se modifican los campos enviados."""
        e = s.actualizar_estudiante(correo, datos.nombre, datos.carrera, datos.semestre)
        return _ok(f"Estudiante actualizado: {e['nombre']}.", estudiante=e)

    @r.delete("/estudiantes", tags=["estudiantes"])
    def eliminar_estudiante(correo: str, s: ServicioRed = S) -> dict:
        resultado = s.eliminar_estudiante(correo)
        return _ok(
            f"Se eliminó a {resultado['nombre']} junto con {resultado['relaciones']} relación(es).",
            **resultado,
        )

    # --- amistades ------------------------------------------------------
    @r.get("/amistades", tags=["amistades"])
    def listar_amigos(correo: str, s: ServicioRed = S) -> list[dict]:
        return s.listar_amigos(correo)

    @r.post("/amistades", status_code=201, tags=["amistades"])
    def agregar_amistad(datos: ParEstudiantes, s: ServicioRed = S) -> dict:
        a, b = s.agregar_amistad(datos.correo_a, datos.correo_b)
        return _ok(f"{a} y {b} ahora son amigos.")

    @r.delete("/amistades", tags=["amistades"])
    def eliminar_amistad(correo_a: str, correo_b: str, s: ServicioRed = S) -> dict:
        a, b = s.eliminar_amistad(correo_a, correo_b)
        return _ok(f"{a} y {b} dejaron de ser amigos.")

    # --- materias -------------------------------------------------------
    @r.get("/materias", tags=["materias"])
    def listar_materias(s: ServicioRed = S) -> list[dict]:
        return s.listar_materias()

    @r.post("/materias", status_code=201, tags=["materias"])
    def crear_materia(datos: MateriaNueva, s: ServicioRed = S) -> dict:
        m = s.crear_materia(datos.codigo, datos.nombre)
        return _ok(f"Materia creada: {m['codigo']} {m['nombre']}.", materia=m)

    @r.post("/inscripciones", status_code=201, tags=["materias"])
    def inscribir(datos: Inscripcion, s: ServicioRed = S) -> dict:
        s.inscribir_materia(datos.correo, datos.codigo, datos.periodo)
        return _ok("Inscripción registrada.")

    @r.delete("/inscripciones", tags=["materias"])
    def dar_de_baja(correo: str, codigo: str, s: ServicioRed = S) -> dict:
        s.dar_de_baja_materia(correo, codigo)
        return _ok("Baja registrada.")

    # --- habilidades ----------------------------------------------------
    @r.get("/habilidades", tags=["habilidades"])
    def listar_habilidades(s: ServicioRed = S) -> list[str]:
        return s.listar_habilidades()

    @r.post("/habilidades", tags=["habilidades"])
    def agregar_habilidad(datos: HabilidadDeEstudiante, s: ServicioRed = S) -> dict:
        """Agrega la habilidad o actualiza su nivel (1 a 5) si ya la tenía."""
        s.agregar_habilidad(datos.correo, datos.habilidad, datos.nivel)
        return _ok("Habilidad guardada.")

    @r.delete("/habilidades", tags=["habilidades"])
    def quitar_habilidad(correo: str, habilidad: str, s: ServicioRed = S) -> dict:
        s.quitar_habilidad(correo, habilidad)
        return _ok("Habilidad quitada.")

    # --- consultas del grafo -------------------------------------------
    @r.get("/consultas/sugerir-amigos", tags=["consultas"])
    def sugerir_amigos(correo: str, limite: str = LIMITE, s: ServicioRed = S) -> list[dict]:
        return s.sugerir_amigos(correo, limite)

    @r.get("/consultas/camino", tags=["consultas"])
    def camino(origen: str, destino: str, s: ServicioRed = S) -> dict:
        return s.camino_mas_corto(origen, destino)

    @r.get("/consultas/amigos-en-comun", tags=["consultas"])
    def amigos_en_comun(correo_a: str, correo_b: str, s: ServicioRed = S) -> list[dict]:
        return s.amigos_en_comun(correo_a, correo_b)

    @r.get("/consultas/vecindad", tags=["consultas"])
    def vecindad(correo: str, grados: str = "2", s: ServicioRed = S) -> list[dict]:
        return s.vecindad(correo, grados)

    @r.get("/consultas/companeros", tags=["consultas"])
    def companeros(correo: str, s: ServicioRed = S) -> list[dict]:
        return s.companeros_de_materia(correo)

    @r.get("/consultas/equipo", tags=["consultas"])
    def equipo(correo: str, codigo: str, limite: str = LIMITE, s: ServicioRed = S) -> list[dict]:
        return s.sugerir_equipo(correo, codigo, limite)

    @r.get("/consultas/mas-conectados", tags=["consultas"])
    def mas_conectados(limite: str = LIMITE, s: ServicioRed = S) -> list[dict]:
        return s.mas_conectados(limite)

    @r.get("/consultas/habilidades-populares", tags=["consultas"])
    def habilidades_populares(limite: str = LIMITE, s: ServicioRed = S) -> list[dict]:
        return s.habilidades_populares(limite)

    # --- grafo para visualizar -----------------------------------------
    @r.get("/grafo", tags=["grafo"])
    def grafo(materias: bool = False, habilidades: bool = False, s: ServicioRed = S) -> dict:
        """Nodos y aristas: estudiantes y AMIGO_DE; opcionalmente CURSA y DOMINA."""
        return s.grafo(incluir_materias=materias, incluir_habilidades=habilidades)

    return r


# Instancia que arranca uvicorn: ``uvicorn app.web.api:app``
app = crear_app()
