"""Menús de consola. Solo piden datos y muestran resultados; delegan en el servicio."""
from __future__ import annotations

from typing import Callable, Sequence

from .entrada import EntradaCancelada, confirmar, pedir_opcion, pedir_opcional, pedir_texto
from .errores import ErrorDeAplicacion
from .servicio import ServicioRed

PROMPT = "Elige una opción: "


# --- presentación ------------------------------------------------------
def _ok(mensaje: str) -> None:
    print(f"[OK] {mensaje}")


def _tabla(encabezados: Sequence[str], filas: Sequence[Sequence[object]]) -> None:
    """Imprime una tabla de texto con columnas alineadas."""
    if not filas:
        print("(sin resultados)")
        return
    texto = [[str(celda) for celda in fila] for fila in filas]
    anchos = [max(len(encabezados[i]), *(len(f[i]) for f in texto)) for i in range(len(encabezados))]
    print("  ".join(h.ljust(anchos[i]) for i, h in enumerate(encabezados)))
    print("  ".join("-" * a for a in anchos))
    for fila in texto:
        print("  ".join(c.ljust(anchos[i]) for i, c in enumerate(fila)))
    print(f"({len(texto)} resultado(s))")


def _tabla_estudiantes(estudiantes: Sequence[dict]) -> None:
    _tabla(
        ["CORREO", "NOMBRE", "CARRERA", "SEM", "CREADO"],
        [[e["correo"], e["nombre"], e["carrera"], e["semestre"], e.get("creado", "")] for e in estudiantes],
    )


def _ejecutar(accion: Callable[[], None]) -> None:
    """Corre una acción; cualquier falla se muestra sin cerrar el programa."""
    try:
        accion()
    except EntradaCancelada:
        raise
    except ErrorDeAplicacion as error:
        print(f"[ERROR] {error}")
    except Exception as error:  # último recurso: el programa nunca se cae
        print(f"[ERROR] Problema inesperado ({type(error).__name__}): {error}")


def _submenu(titulo: str, opciones: dict[str, str], acciones: dict[str, Callable[[], None]]) -> None:
    """Muestra un submenú en bucle hasta elegir 0."""
    while True:
        print(f"\n=== {titulo} ===")
        for clave, texto in opciones.items():
            print(f"  {clave}. {texto}")
        print("  0. Volver al menú principal")
        eleccion = pedir_opcion(PROMPT, [*opciones, "0"])
        if eleccion == "0":
            return
        _ejecutar(acciones[eleccion])


# --- estudiantes -------------------------------------------------------
def _menu_estudiantes(s: ServicioRed) -> None:
    def crear() -> None:
        e = s.crear_estudiante(
            pedir_texto("Correo: "), pedir_texto("Nombre: "),
            pedir_texto("Carrera: "), pedir_texto("Semestre (1-12): "),
        )
        _ok(f"Estudiante creado: {e['nombre']} ({e['correo']}).")

    def listar() -> None:
        _tabla_estudiantes(s.listar_estudiantes())

    def buscar_correo() -> None:
        _tabla_estudiantes([s.obtener_estudiante(pedir_texto("Correo: "))])

    def buscar_nombre() -> None:
        _tabla_estudiantes(s.buscar_estudiantes(pedir_texto("Texto del nombre: ")))

    def modificar() -> None:
        actual = s.obtener_estudiante(pedir_texto("Correo del estudiante a modificar: "))
        print(f"Actual: {actual['nombre']} | {actual['carrera']} | semestre {actual['semestre']}")
        print("(ENTER vacío = dejar el valor actual)")
        nuevo = s.actualizar_estudiante(
            actual["correo"], pedir_opcional("Nuevo nombre: "),
            pedir_opcional("Nueva carrera: "), pedir_opcional("Nuevo semestre: "),
        )
        _ok(f"Actualizado: {nuevo['nombre']} | {nuevo['carrera']} | semestre {nuevo['semestre']}.")

    def eliminar() -> None:
        e = s.obtener_estudiante(pedir_texto("Correo del estudiante a eliminar: "))
        if not confirmar(f"¿Eliminar a {e['nombre']} y todas sus relaciones?"):
            print("Operación cancelada.")
            return
        r = s.eliminar_estudiante(e["correo"])
        _ok(f"Eliminado {r['nombre']} junto con {r['relaciones']} relación(es).")

    def perfil() -> None:
        e = s.obtener_estudiante(pedir_texto("Correo: "))
        print(f"\n{e['nombre']} | {e['carrera']} | semestre {e['semestre']} | {e['correo']}")
        print("\nAmigos:")
        _tabla(["NOMBRE", "CARRERA", "DESDE"],
               [[a["estudiante"]["nombre"], a["estudiante"]["carrera"], a["desde"]] for a in s.listar_amigos(e["correo"])])
        print("\nMaterias:")
        _tabla(["CODIGO", "MATERIA", "PERIODO"],
               [[m["materia"]["codigo"], m["materia"]["nombre"], m["periodo"]] for m in s.materias_de(e["correo"])])
        print("\nHabilidades:")
        _tabla(["HABILIDAD", "NIVEL (1-5)"], [[h["habilidad"], h["nivel"]] for h in s.habilidades_de(e["correo"])])

    _submenu("ESTUDIANTES", {
        "1": "Crear estudiante", "2": "Listar estudiantes", "3": "Buscar por correo",
        "4": "Buscar por nombre", "5": "Modificar estudiante", "6": "Eliminar estudiante",
        "7": "Ver perfil completo (amigos, materias, habilidades)",
    }, {"1": crear, "2": listar, "3": buscar_correo, "4": buscar_nombre,
        "5": modificar, "6": eliminar, "7": perfil})


# --- relaciones --------------------------------------------------------
def _menu_relaciones(s: ServicioRed) -> None:
    def amistad_alta() -> None:
        a, b = s.agregar_amistad(pedir_texto("Correo del primer estudiante: "), pedir_texto("Correo del segundo: "))
        _ok(f"{a} y {b} ahora son amigos.")

    def amistad_baja() -> None:
        a, b = s.eliminar_amistad(pedir_texto("Correo del primer estudiante: "), pedir_texto("Correo del segundo: "))
        _ok(f"{a} y {b} dejaron de ser amigos.")

    def ver_amigos() -> None:
        amigos = s.listar_amigos(pedir_texto("Correo: "))
        _tabla(["CORREO", "NOMBRE", "CARRERA", "DESDE"],
               [[a["estudiante"]["correo"], a["estudiante"]["nombre"], a["estudiante"]["carrera"], a["desde"]] for a in amigos])

    def materia_nueva() -> None:
        m = s.crear_materia(pedir_texto("Código (ej. BDA-401): "), pedir_texto("Nombre de la materia: "))
        _ok(f"Materia creada: {m['codigo']} {m['nombre']}.")

    def materias() -> None:
        _tabla(["CODIGO", "NOMBRE"], [[m["codigo"], m["nombre"]] for m in s.listar_materias()])

    def inscribir() -> None:
        s.inscribir_materia(pedir_texto("Correo: "), pedir_texto("Código de materia: "), pedir_texto("Periodo (ej. 2026-Otoño): "))
        _ok("Inscripción registrada.")

    def baja() -> None:
        s.dar_de_baja_materia(pedir_texto("Correo: "), pedir_texto("Código de materia: "))
        _ok("Materia dada de baja.")

    def habilidad_alta() -> None:
        s.agregar_habilidad(pedir_texto("Correo: "), pedir_texto("Habilidad (ej. python): "), pedir_texto("Nivel (1-5): "))
        _ok("Habilidad registrada o actualizada.")

    def habilidad_baja() -> None:
        s.quitar_habilidad(pedir_texto("Correo: "), pedir_texto("Habilidad a quitar: "))
        _ok("Habilidad quitada.")

    _submenu("RELACIONES, MATERIAS Y HABILIDADES", {
        "1": "Agregar amistad", "2": "Eliminar amistad", "3": "Ver amigos de un estudiante",
        "4": "Crear materia", "5": "Listar materias", "6": "Inscribir estudiante en materia",
        "7": "Dar de baja una materia", "8": "Agregar o actualizar habilidad", "9": "Quitar habilidad",
    }, {"1": amistad_alta, "2": amistad_baja, "3": ver_amigos, "4": materia_nueva, "5": materias,
        "6": inscribir, "7": baja, "8": habilidad_alta, "9": habilidad_baja})


# --- consultas de grafo ------------------------------------------------
def _menu_consultas(s: ServicioRed) -> None:
    def sugerencias() -> None:
        r = s.sugerir_amigos(pedir_texto("Correo del estudiante: "))
        _tabla(["CORREO", "NOMBRE", "AMIGOS EN COMUN"], [[x["correo"], x["nombre"], x["amigos_en_comun"]] for x in r])

    def camino() -> None:
        r = s.camino_mas_corto(pedir_texto("Correo de origen: "), pedir_texto("Correo de destino: "))
        print(" -> ".join(r["camino"]))
        _ok(f"{r['grados']} grado(s) de separación.")

    def en_comun() -> None:
        r = s.amigos_en_comun(pedir_texto("Correo del primer estudiante: "), pedir_texto("Correo del segundo: "))
        _tabla(["CORREO", "NOMBRE"], [[x["correo"], x["nombre"]] for x in r])

    def vecindad() -> None:
        r = s.vecindad(pedir_texto("Correo del estudiante: "), pedir_texto("Hasta cuántos grados (1-4): "))
        _tabla(["GRADOS", "CORREO", "NOMBRE"], [[x["grados"], x["correo"], x["nombre"]] for x in r])

    def companeros() -> None:
        r = s.companeros_de_materia(pedir_texto("Correo del estudiante: "))
        _tabla(["NOMBRE", "MATERIAS EN COMUN", "TOTAL"], [[x["nombre"], ", ".join(x["materias_en_comun"]), x["total"]] for x in r])

    def equipo() -> None:
        r = s.sugerir_equipo(pedir_texto("Correo del estudiante: "), pedir_texto("Código de la materia: "))
        _tabla(["NOMBRE", "HABILIDADES QUE APORTA", "PUNTAJE"], [[x["nombre"], ", ".join(x["habilidades_que_aporta"]), x["puntaje"]] for x in r])

    def conectados() -> None:
        r = s.mas_conectados()
        _tabla(["NOMBRE", "CARRERA", "AMIGOS"], [[x["nombre"], x["carrera"], x["amigos"]] for x in r])

    def populares() -> None:
        r = s.habilidades_populares()
        _tabla(["HABILIDAD", "ESTUDIANTES", "NIVEL PROMEDIO"], [[x["habilidad"], x["estudiantes"], x["nivel_promedio"]] for x in r])

    _submenu("CONSULTAS DEL GRAFO", {
        "1": "Sugerir amigos (amigos de amigos)", "2": "Camino más corto entre dos estudiantes",
        "3": "Amigos en común", "4": "Vecindad: alcanzables hasta N grados",
        "5": "Compañeros que cursan mis materias", "6": "Sugerir equipo para una materia",
        "7": "Estudiantes más conectados", "8": "Habilidades más populares",
    }, {"1": sugerencias, "2": camino, "3": en_comun, "4": vecindad,
        "5": companeros, "6": equipo, "7": conectados, "8": populares})


# --- principal ---------------------------------------------------------
def ejecutar_aplicacion(servicio: ServicioRed) -> None:
    """Bucle del menú principal; termina al elegir Salir o cerrar la entrada."""
    try:
        while True:
            print("\n===== UNIRED: RED DE ESTUDIANTES (Neo4j AuraDB) =====")
            print("  1. Estudiantes")
            print("  2. Relaciones, materias y habilidades")
            print("  3. Consultas del grafo")
            print("  4. Salir")
            eleccion = pedir_opcion(PROMPT, ["1", "2", "3", "4"])
            if eleccion == "1":
                _menu_estudiantes(servicio)
            elif eleccion == "2":
                _menu_relaciones(servicio)
            elif eleccion == "3":
                _menu_consultas(servicio)
            else:
                break
    except EntradaCancelada:
        print("Entrada cerrada.")
    print("Hasta luego.")
