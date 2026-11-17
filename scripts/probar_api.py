"""Prueba de humo del API web contra la base REAL en AuraDB.

Recorre todos los endpoints (CRUD, amistades, inscripciones, habilidades, las 8
consultas y el grafo) usando datos de prueba que se borran al terminar. Al
final compara los conteos de la base con los del inicio para asegurar que
quedó igual.

Uso (con el servidor corriendo en otra terminal):
    uvicorn app.web.api:app
    python3 -m scripts.probar_api                    # usa http://127.0.0.1:8000
    python3 -m scripts.probar_api --url http://127.0.0.1:8001

Requiere haber cargado los datos de ejemplo (python3 -m scripts.seed).
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from app.config import cargar_configuracion
from app.conexion import ConexionNeo4j
from app.errores import ErrorDeAplicacion
from app.repositorio import RepositorioRed

CORREO_A = "prueba.web.a@unired.example"
CORREO_B = "prueba.web.b@unired.example"
CODIGO_PRUEBA = "PRB-999"
SEMILLA = "ana.lopez@unired.example"  # estudiante de los datos de ejemplo


class Probador:
    """Cliente HTTP mínimo (solo biblioteca estándar) que cuenta aciertos y fallas."""

    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.aciertos = 0
        self.fallas: list[str] = []

    def pedir(self, metodo: str, ruta: str, query: Optional[dict] = None, cuerpo: Any = None) -> tuple[int, Any]:
        url = f"{self.base}/api{ruta}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        peticion = urllib.request.Request(url, data=datos, method=metodo)
        if datos is not None:
            peticion.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(peticion, timeout=60) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"null")

    def esperar(self, nombre: str, metodo: str, ruta: str, codigo: int, query=None, cuerpo=None, revisar=None) -> Any:
        """Hace la petición y comprueba el código HTTP (y opcionalmente el contenido)."""
        estado, datos = self.pedir(metodo, ruta, query, cuerpo)
        ok = estado == codigo
        detalle = ""
        if ok and revisar is not None:
            try:
                resultado = revisar(datos)
                ok = resultado is not False
            except Exception as error:  # la verificación misma falló
                ok, detalle = False, f" ({type(error).__name__}: {error})"
        if ok:
            self.aciertos += 1
        else:
            self.fallas.append(f"{nombre}: HTTP {estado} (se esperaba {codigo}){detalle} -> {datos}")
        mensaje = datos.get("mensaje", "") if isinstance(datos, dict) else f"{len(datos)} fila(s)" if isinstance(datos, list) else ""
        print(f"  [{'OK' if ok else 'FALLA'}] {estado} {metodo:6} {ruta:32} {nombre}  {mensaje}"[:180])
        return datos


def ejecutar(p: Probador) -> None:
    p.esperar("salud", "GET", "/salud", 200)

    print("\n-- Estudiantes --")
    p.esperar("crear A", "POST", "/estudiantes", 201, cuerpo={
        "correo": CORREO_A.upper(), "nombre": "  Prueba   Web A ", "carrera": "Ingeniería en Tecnologías de la Información", "semestre": "4"})
    p.esperar("crear B", "POST", "/estudiantes", 201, cuerpo={
        "correo": CORREO_B, "nombre": "Prueba Web B", "carrera": "Diseño Gráfico", "semestre": 2})
    p.esperar("duplicado", "POST", "/estudiantes", 409, cuerpo={
        "correo": CORREO_A, "nombre": "X", "carrera": "X", "semestre": 1})
    p.esperar("semestre inválido", "POST", "/estudiantes", 422, cuerpo={
        "correo": "otro@unired.example", "nombre": "X", "carrera": "X", "semestre": 40})
    p.esperar("correo inválido", "POST", "/estudiantes", 422, cuerpo={
        "correo": "sin-arroba", "nombre": "X", "carrera": "X", "semestre": 1})
    p.esperar("listar", "GET", "/estudiantes", 200, revisar=lambda d: any(e["correo"] == CORREO_A for e in d))
    p.esperar("buscar", "GET", "/estudiantes", 200, query={"q": "prueba web"}, revisar=lambda d: len(d) == 2)
    p.esperar("detalle (normalizado)", "GET", "/estudiantes/detalle", 200, query={"correo": CORREO_A},
              revisar=lambda d: d["nombre"] == "Prueba Web A" and d["semestre"] == 4)
    p.esperar("no encontrado", "GET", "/estudiantes/detalle", 404, query={"correo": "nadie@unired.example"})
    p.esperar("modificar parcial", "PATCH", "/estudiantes", 200, query={"correo": CORREO_A}, cuerpo={"semestre": 5},
              revisar=lambda d: d["estudiante"]["semestre"] == 5 and d["estudiante"]["carrera"].startswith("Ingeniería"))
    p.esperar("modificar sin cambios", "PATCH", "/estudiantes", 422, query={"correo": CORREO_A}, cuerpo={"semestre": 5})

    print("\n-- Amistades --")
    p.esperar("A-B", "POST", "/amistades", 201, cuerpo={"correo_a": CORREO_A, "correo_b": CORREO_B})
    p.esperar("A-semilla", "POST", "/amistades", 201, cuerpo={"correo_a": CORREO_A, "correo_b": SEMILLA})
    p.esperar("repetida", "POST", "/amistades", 409, cuerpo={"correo_a": CORREO_B, "correo_b": CORREO_A})
    p.esperar("consigo mismo", "POST", "/amistades", 422, cuerpo={"correo_a": CORREO_A, "correo_b": CORREO_A})
    p.esperar("listar amigos", "GET", "/amistades", 200, query={"correo": CORREO_A}, revisar=lambda d: len(d) == 2)

    print("\n-- Materias --")
    materias = p.esperar("listar", "GET", "/materias", 200, revisar=lambda d: len(d) > 0)
    p.esperar("crear", "POST", "/materias", 201, cuerpo={"codigo": CODIGO_PRUEBA.lower(), "nombre": "Materia de prueba"})
    p.esperar("duplicada", "POST", "/materias", 409, cuerpo={"codigo": CODIGO_PRUEBA, "nombre": "X"})
    p.esperar("código inválido", "POST", "/materias", 422, cuerpo={"codigo": "123", "nombre": "X"})
    codigo = materias[0]["codigo"] if materias else "BDA-401"
    p.esperar("inscribir A", "POST", "/inscripciones", 201, cuerpo={"correo": CORREO_A, "codigo": codigo, "periodo": "2026-otoño"})
    p.esperar("inscribir B", "POST", "/inscripciones", 201, cuerpo={"correo": CORREO_B, "codigo": codigo, "periodo": "2026-Otoño"})
    p.esperar("inscribir B prueba", "POST", "/inscripciones", 201, cuerpo={"correo": CORREO_B, "codigo": CODIGO_PRUEBA, "periodo": "2027-Primavera"})
    p.esperar("periodo inválido", "POST", "/inscripciones", 422, cuerpo={"correo": CORREO_A, "codigo": codigo, "periodo": "otoño"})
    p.esperar("dar de baja", "DELETE", "/inscripciones", 200, query={"correo": CORREO_B, "codigo": CODIGO_PRUEBA})
    p.esperar("baja inexistente", "DELETE", "/inscripciones", 404, query={"correo": CORREO_B, "codigo": CODIGO_PRUEBA})

    print("\n-- Habilidades --")
    habilidades = p.esperar("listar", "GET", "/habilidades", 200)
    # Se usan habilidades que ya existen para no dejar nodos Habilidad huérfanos.
    h1 = habilidades[0] if habilidades else "python"
    h2 = habilidades[1] if len(habilidades) > 1 else h1
    p.esperar("agregar a B", "POST", "/habilidades", 200, cuerpo={"correo": CORREO_B, "habilidad": h1.upper(), "nivel": 3})
    p.esperar("actualizar nivel", "POST", "/habilidades", 200, cuerpo={"correo": CORREO_B, "habilidad": h1, "nivel": "5"})
    p.esperar("agregar otra", "POST", "/habilidades", 200, cuerpo={"correo": CORREO_B, "habilidad": h2, "nivel": 2})
    p.esperar("nivel fuera de rango", "POST", "/habilidades", 422, cuerpo={"correo": CORREO_B, "habilidad": h1, "nivel": 9})
    p.esperar("perfil", "GET", "/estudiantes/perfil", 200, query={"correo": CORREO_B},
              revisar=lambda d: len(d["amigos"]) == 1 and len(d["materias"]) == 1
              and any(h["habilidad"] == h1 and h["nivel"] == 5 for h in d["habilidades"]))
    p.esperar("quitar", "DELETE", "/habilidades", 200, query={"correo": CORREO_B, "habilidad": h2})
    p.esperar("quitar inexistente", "DELETE", "/habilidades", 404, query={"correo": CORREO_B, "habilidad": h2})

    print("\n-- Consultas del grafo --")
    p.esperar("sugerir amigos", "GET", "/consultas/sugerir-amigos", 200, query={"correo": CORREO_B, "limite": 5},
              revisar=lambda d: any(x["correo"] == SEMILLA for x in d))
    p.esperar("camino más corto", "GET", "/consultas/camino", 200, query={"origen": CORREO_B, "destino": SEMILLA},
              revisar=lambda d: d["grados"] == 2 and d["correos"] == [CORREO_B, CORREO_A, SEMILLA])
    p.esperar("camino mismo", "GET", "/consultas/camino", 422, query={"origen": CORREO_B, "destino": CORREO_B})
    p.esperar("amigos en común", "GET", "/consultas/amigos-en-comun", 200, query={"correo_a": CORREO_B, "correo_b": SEMILLA},
              revisar=lambda d: [x["correo"] for x in d] == [CORREO_A])
    p.esperar("vecindad 2", "GET", "/consultas/vecindad", 200, query={"correo": CORREO_B, "grados": 2},
              revisar=lambda d: {x["correo"]: x["grados"] for x in d}.get(SEMILLA) == 2)
    p.esperar("vecindad 9", "GET", "/consultas/vecindad", 422, query={"correo": CORREO_B, "grados": 9})
    p.esperar("compañeros", "GET", "/consultas/companeros", 200, query={"correo": CORREO_A},
              revisar=lambda d: any(x["correo"] == CORREO_B for x in d))
    p.esperar("sugerir equipo", "GET", "/consultas/equipo", 200, query={"correo": CORREO_A, "codigo": codigo, "limite": 10},
              revisar=lambda d: any(x["correo"] == CORREO_B for x in d))
    p.esperar("más conectados", "GET", "/consultas/mas-conectados", 200, query={"limite": 3}, revisar=lambda d: len(d) == 3)
    p.esperar("habilidades populares", "GET", "/consultas/habilidades-populares", 200, query={"limite": 5},
              revisar=lambda d: 0 < len(d) <= 5)
    p.esperar("límite inválido", "GET", "/consultas/mas-conectados", 422, query={"limite": "abc"})

    print("\n-- Grafo --")

    def revisar_grafo(d: dict, con_extras: bool) -> bool:
        ids = {n["id"] for n in d["nodos"]}
        assert f"e:{CORREO_A}" in ids, "falta el nodo de prueba"
        assert all(a["origen"] in ids and a["destino"] in ids for a in d["aristas"]), "arista sin nodo"
        tipos = {a["tipo"] for a in d["aristas"]}
        return tipos == ({"AMIGO_DE", "CURSA", "DOMINA"} if con_extras else {"AMIGO_DE"})

    p.esperar("solo amistades", "GET", "/grafo", 200, revisar=lambda d: revisar_grafo(d, False))
    p.esperar("completo", "GET", "/grafo", 200, query={"materias": "true", "habilidades": "true"},
              revisar=lambda d: revisar_grafo(d, True))

    print("\n-- Limpieza --")
    p.esperar("quitar amistad", "DELETE", "/amistades", 200, query={"correo_a": CORREO_A, "correo_b": SEMILLA})
    p.esperar("quitar amistad inexistente", "DELETE", "/amistades", 404, query={"correo_a": CORREO_A, "correo_b": SEMILLA})


def limpiar(p: Probador, repositorio: RepositorioRed, conexion: ConexionNeo4j) -> None:
    """Borra todo lo de prueba aunque alguna prueba haya fallado a medias."""
    for correo in (CORREO_A, CORREO_B):
        estado, _ = p.pedir("GET", "/estudiantes/detalle", {"correo": correo})
        if estado == 200:
            p.esperar(f"eliminar {correo}", "DELETE", "/estudiantes", 200, query={"correo": correo})
    # No existe endpoint para borrar materias: se borra directo y solo si es la de prueba.
    conexion.escribir("MATCH (m:Materia {codigo: $codigo}) DETACH DELETE m", {"codigo": CODIGO_PRUEBA})
    p.esperar("eliminado ya no existe", "GET", "/estudiantes/detalle", 404, query={"correo": CORREO_A})


def main(argumentos: list[str]) -> int:
    base = argumentos[argumentos.index("--url") + 1] if "--url" in argumentos else "http://127.0.0.1:8000"
    p = Probador(base)
    try:
        with ConexionNeo4j(cargar_configuracion()) as conexion:
            repositorio = RepositorioRed(conexion)
            antes = repositorio.contar_datos()
            print(f"Conteos iniciales: {antes}")
            try:
                ejecutar(p)
            finally:
                limpiar(p, repositorio, conexion)
            despues = repositorio.contar_datos()
    except ErrorDeAplicacion as error:
        print(f"[ERROR] {error}")
        return 1
    except urllib.error.URLError as error:
        print(f"[ERROR] No se pudo contactar al servidor en {base}: {error.reason}. ¿Está corriendo uvicorn?")
        return 1

    print(f"\nConteos finales:  {despues}")
    if antes != despues:
        p.fallas.append(f"La base no quedó igual: {antes} -> {despues}")
    print(f"\n{p.aciertos} verificaciones correctas, {len(p.fallas)} falla(s).")
    for falla in p.fallas:
        print(f"  - {falla}")
    return 0 if not p.fallas else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
