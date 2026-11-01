"""Datos de ejemplo (personas ficticias) para poblar la base antes de las pruebas."""
from __future__ import annotations

DOMINIO = "unired.example"

_EST = [
    # clave, nombre, carrera, semestre
    ("ana.lopez", "Ana López", "Ingeniería en Tecnologías de la Información", 7),
    ("carlos.perez", "Carlos Pérez", "Ingeniería en Tecnologías de la Información", 7),
    ("sofia.ramirez", "Sofía Ramírez", "Ingeniería en Tecnologías de la Información", 5),
    ("diego.herrera", "Diego Herrera", "Ingeniería Industrial", 5),
    ("valeria.castro", "Valeria Castro", "Diseño Gráfico", 3),
    ("mateo.guzman", "Mateo Guzmán", "Ingeniería Mecatrónica", 9),
    ("camila.ortiz", "Camila Ortiz", "Ingeniería en Tecnologías de la Información", 3),
    ("luis.mendoza", "Luis Mendoza", "Ingeniería Civil", 7),
    ("fernanda.ruiz", "Fernanda Ruiz", "Administración de Empresas", 5),
    ("andres.vega", "Andrés Vega", "Ingeniería en Tecnologías de la Información", 9),
    ("paola.salazar", "Paola Salazar", "Ingeniería Industrial", 7),
    ("jorge.campos", "Jorge Campos", "Ingeniería Mecatrónica", 5),
    ("renata.silva", "Renata Silva", "Diseño Gráfico", 7),
    ("emilio.navarro", "Emilio Navarro", "Ingeniería en Tecnologías de la Información", 5),
]

_MATERIAS = [
    ("BDA-401", "Bases de Datos Avanzadas"),
    ("ISW-301", "Ingeniería de Software"),
    ("RED-310", "Redes de Computadoras"),
    ("EST-201", "Estadística"),
    ("CAL-102", "Cálculo Diferencial"),
    ("UXD-220", "Diseño de Interfaces"),
    ("ADM-210", "Fundamentos de Administración"),
    ("PRG-110", "Programación"),
]

_AMISTADES = [
    ("ana.lopez", "carlos.perez"), ("ana.lopez", "sofia.ramirez"), ("ana.lopez", "camila.ortiz"),
    ("carlos.perez", "sofia.ramirez"), ("carlos.perez", "diego.herrera"),
    ("sofia.ramirez", "camila.ortiz"), ("sofia.ramirez", "andres.vega"),
    ("diego.herrera", "paola.salazar"), ("diego.herrera", "jorge.campos"),
    ("paola.salazar", "fernanda.ruiz"), ("paola.salazar", "jorge.campos"),
    ("fernanda.ruiz", "valeria.castro"), ("valeria.castro", "renata.silva"),
    ("renata.silva", "luis.mendoza"), ("luis.mendoza", "mateo.guzman"),
    ("mateo.guzman", "jorge.campos"), ("andres.vega", "emilio.navarro"),
    ("emilio.navarro", "camila.ortiz"), ("renata.silva", "camila.ortiz"),
]

_PERIODO = "2026-Otoño"
_CURSAN = {
    "BDA-401": ["ana.lopez", "carlos.perez", "andres.vega", "emilio.navarro", "sofia.ramirez"],
    "ISW-301": ["ana.lopez", "carlos.perez", "sofia.ramirez", "camila.ortiz", "emilio.navarro"],
    "RED-310": ["andres.vega", "emilio.navarro", "jorge.campos", "mateo.guzman"],
    "EST-201": ["diego.herrera", "paola.salazar", "fernanda.ruiz", "luis.mendoza", "camila.ortiz"],
    "CAL-102": ["camila.ortiz", "sofia.ramirez", "luis.mendoza", "jorge.campos", "valeria.castro"],
    "UXD-220": ["valeria.castro", "renata.silva", "camila.ortiz", "sofia.ramirez"],
    "ADM-210": ["fernanda.ruiz", "paola.salazar", "diego.herrera"],
    "PRG-110": ["camila.ortiz", "sofia.ramirez", "jorge.campos", "valeria.castro"],
}

_HABILIDADES = {
    "ana.lopez": {"python": 4, "sql": 4, "scrum": 3},
    "carlos.perez": {"java": 4, "sql": 3, "python": 3},
    "sofia.ramirez": {"diseño ux": 4, "python": 2, "figma": 3},
    "diego.herrera": {"excel": 5, "estadística": 4, "liderazgo": 3},
    "valeria.castro": {"figma": 5, "diseño ux": 4, "ilustración": 4},
    "mateo.guzman": {"arduino": 5, "redes": 3, "c++": 4},
    "camila.ortiz": {"python": 3, "oratoria": 4, "figma": 2},
    "luis.mendoza": {"autocad": 4, "excel": 3, "estadística": 3},
    "fernanda.ruiz": {"liderazgo": 5, "oratoria": 4, "excel": 4},
    "andres.vega": {"neo4j": 4, "redes": 4, "python": 5, "sql": 5},
    "paola.salazar": {"estadística": 5, "excel": 4, "scrum": 4},
    "jorge.campos": {"arduino": 4, "c++": 3, "redes": 3},
    "renata.silva": {"ilustración": 5, "figma": 4, "oratoria": 3},
    "emilio.navarro": {"java": 3, "redes": 4, "neo4j": 3, "scrum": 2},
}


def _correo(clave: str) -> str:
    return f"{clave}@{DOMINIO}"


def obtener_datos() -> dict[str, list[dict]]:
    """Arma las listas de diccionarios que recibe ``RepositorioRed.sembrar``."""
    return {
        "materias": [{"codigo": c, "nombre": n} for c, n in _MATERIAS],
        "estudiantes": [
            {"correo": _correo(k), "nombre": n, "carrera": ca, "semestre": s} for k, n, ca, s in _EST
        ],
        "amistades": [{"a": _correo(a), "b": _correo(b), "desde": "2026-08-17"} for a, b in _AMISTADES],
        "inscripciones": [
            {"correo": _correo(k), "codigo": cod, "periodo": _PERIODO}
            for cod, claves in _CURSAN.items() for k in claves
        ],
        "habilidades": [
            {"correo": _correo(k), "habilidad": h, "nivel": nv}
            for k, hs in _HABILIDADES.items() for h, nv in hs.items()
        ],
    }
