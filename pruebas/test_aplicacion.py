"""Pruebas unitarias con una conexión simulada (no necesitan internet ni AuraDB).

Comprueban las validaciones, las reglas de negocio y que cada consulta reciba
exactamente los parámetros que declara. La prueba contra la nube real se hace
con ``python3 -m scripts.verificar_conexion`` y ``python3 main.py``.
"""
from __future__ import annotations

import inspect
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from app import consultas as c
from app import validaciones as val
from app.config import cargar_configuracion
from app.errores import (
    ErrorDeConfiguracion,
    ErrorDeValidacion,
    ErrorDuplicado,
    ErrorNoEncontrado,
)
from app.repositorio import RepositorioRed
from app.servicio import ServicioRed


class ConexionFalsa:
    """Imita a ConexionNeo4j: registra llamadas y devuelve respuestas programadas."""

    def __init__(self, respuestas: dict[str, list[dict]] | None = None) -> None:
        self.respuestas = {k.strip(): v for k, v in (respuestas or {}).items()}
        self.llamadas: list[tuple[str, dict]] = []

    def _registrar(self, consulta: str, parametros: dict | None) -> list[dict]:
        parametros = parametros or {}
        declarados = set(re.findall(r"\$(\w+)", consulta))
        assert declarados == set(parametros), (
            f"Parámetros enviados {sorted(parametros)} != declarados {sorted(declarados)}"
        )
        self.llamadas.append((consulta, parametros))
        respuesta = self.respuestas.get(consulta.strip(), [])
        return respuesta(parametros) if callable(respuesta) else respuesta

    def leer(self, consulta, parametros=None):
        return self._registrar(consulta, parametros)

    def escribir(self, consulta, parametros=None):
        return self._registrar(consulta, parametros)


def estudiante(correo="ana@x.com", nombre="Ana", semestre=5):
    return {"correo": correo, "nombre": nombre, "carrera": "ITI", "semestre": semestre, "creado": "2026-10-31"}


def conocidos(*correos):
    """Respuesta programada: solo existen los estudiantes cuyos correos se indican."""
    return lambda p: [{"estudiante": estudiante(p["correo"])}] if p["correo"] in correos else []


def armar(respuestas=None):
    bd = ConexionFalsa(respuestas)
    return bd, ServicioRed(RepositorioRed(bd))


class PruebasConfiguracion(unittest.TestCase):
    def _cargar(self, entorno):
        with mock.patch.dict(os.environ, entorno, clear=True):
            return cargar_configuracion(Path("/no/existe/.env"))

    def test_faltan_variables(self):
        with self.assertRaises(ErrorDeConfiguracion) as ctx:
            self._cargar({})
        self.assertIn("NEO4J_URI", str(ctx.exception))

    def test_rechaza_localhost(self):
        base = {"NEO4J_USERNAME": "u", "NEO4J_PASSWORD": "p"}
        for uri in ["neo4j+s://localhost", "bolt+s://127.0.0.1:7687"]:
            with self.subTest(uri=uri), self.assertRaises(ErrorDeConfiguracion):
                self._cargar({**base, "NEO4J_URI": uri})

    def test_rechaza_esquema_sin_tls(self):
        with self.assertRaises(ErrorDeConfiguracion):
            self._cargar({"NEO4J_URI": "bolt://abc.databases.neo4j.io", "NEO4J_USERNAME": "u", "NEO4J_PASSWORD": "p"})

    def test_configuracion_valida_y_clave_oculta(self):
        cfg = self._cargar({"NEO4J_URI": "neo4j+s://abc.databases.neo4j.io", "NEO4J_USERNAME": "u", "NEO4J_PASSWORD": "secreto"})
        self.assertEqual(cfg.base_de_datos, "neo4j")
        self.assertNotIn("secreto", repr(cfg))


class PruebasValidaciones(unittest.TestCase):
    def test_correo(self):
        self.assertEqual(val.validar_correo("  ANA@X.com "), "ana@x.com")
        for malo in ["", "   ", "sinarroba", "a@b", "a b@c.com"]:
            with self.subTest(correo=malo), self.assertRaises(ErrorDeValidacion):
                val.validar_correo(malo)

    def test_entero(self):
        self.assertEqual(val.validar_entero("7", "semestre", 1, 12), 7)
        for malo in ["abc", "1.5", "-3", "0", "13", "", " ", True, None]:
            with self.subTest(valor=malo), self.assertRaises(ErrorDeValidacion):
                val.validar_entero(malo, "semestre", 1, 12)

    def test_texto_obligatorio(self):
        self.assertEqual(val.validar_texto("  Ana   López ", "nombre"), "Ana López")
        for malo in ["", "   ", None]:
            with self.assertRaises(ErrorDeValidacion):
                val.validar_texto(malo, "nombre")

    def test_codigo_y_periodo(self):
        self.assertEqual(val.validar_codigo_materia(" bda-401 "), "BDA-401")
        self.assertEqual(val.validar_periodo("2026-otoño"), "2026-Otoño")
        with self.assertRaises(ErrorDeValidacion):
            val.validar_codigo_materia("BD401")
        with self.assertRaises(ErrorDeValidacion):
            val.validar_periodo("otoño 2026")

    def test_habilidad_en_minusculas(self):
        self.assertEqual(val.validar_habilidad("  Python "), "python")


class PruebasEstudiantes(unittest.TestCase):
    def test_datos_invalidos_no_tocan_la_base(self):
        bd, s = armar()
        for args in [("mal", "Ana", "ITI", "5"), ("a@x.com", "  ", "ITI", "5"),
                     ("a@x.com", "Ana", "ITI", "abc"), ("a@x.com", "Ana", "ITI", "99")]:
            with self.subTest(args=args), self.assertRaises(ErrorDeValidacion):
                s.crear_estudiante(*args)
        self.assertEqual(bd.llamadas, [])

    def test_correo_duplicado(self):
        _, s = armar({c.OBTENER_ESTUDIANTE: [{"estudiante": estudiante()}]})
        with self.assertRaises(ErrorDuplicado):
            s.crear_estudiante("ANA@x.com", "Ana", "ITI", 5)

    def test_crear_normaliza_y_guarda(self):
        bd, s = armar({c.CREAR_ESTUDIANTE: [{"estudiante": estudiante()}]})
        s.crear_estudiante("  ANA@X.com ", " Ana ", "ITI", "5")
        consulta, parametros = bd.llamadas[-1]
        self.assertEqual(consulta.strip(), c.CREAR_ESTUDIANTE.strip())
        self.assertEqual(parametros, {"correo": "ana@x.com", "nombre": "Ana", "carrera": "ITI", "semestre": 5})

    def test_obtener_inexistente(self):
        _, s = armar()
        with self.assertRaises(ErrorNoEncontrado):
            s.obtener_estudiante("nadie@x.com")

    def test_actualizar_sin_cambios_y_con_cambios(self):
        bd, s = armar({c.OBTENER_ESTUDIANTE: [{"estudiante": estudiante()}],
                       c.ACTUALIZAR_ESTUDIANTE: [{"estudiante": estudiante(nombre="Ana María")}]})
        with self.assertRaises(ErrorDeValidacion):
            s.actualizar_estudiante("ana@x.com")
        with self.assertRaises(ErrorDeValidacion):
            s.actualizar_estudiante("ana@x.com", nombre="Ana")  # igual al actual
        with self.assertRaises(ErrorDeValidacion):
            s.actualizar_estudiante("ana@x.com", nombre="   ")
        s.actualizar_estudiante("ana@x.com", nombre="Ana María")
        self.assertEqual(bd.llamadas[-1][1], {"correo": "ana@x.com", "cambios": {"nombre": "Ana María"}})

    def test_eliminar(self):
        _, s = armar()
        with self.assertRaises(ErrorNoEncontrado):
            s.eliminar_estudiante("nadie@x.com")
        _, s = armar({c.OBTENER_ESTUDIANTE: [{"estudiante": estudiante()}],
                      c.ELIMINAR_ESTUDIANTE: [{"nombre": "Ana", "relaciones": 3}]})
        self.assertEqual(s.eliminar_estudiante("ana@x.com")["relaciones"], 3)


class PruebasRelacionesYConsultas(unittest.TestCase):
    def test_amistad_consigo_mismo(self):
        _, s = armar({c.OBTENER_ESTUDIANTE: [{"estudiante": estudiante()}]})
        with self.assertRaises(ErrorDeValidacion):
            s.agregar_amistad("ana@x.com", "ANA@x.com")

    def test_amistad_repetida_se_rechaza(self):
        _, s = armar({c.OBTENER_ESTUDIANTE: conocidos("a@x.com", "b@x.com"), c.EXISTE_AMISTAD: [{"total": 1}]})
        with self.assertRaises(ErrorDuplicado):
            s.agregar_amistad("a@x.com", "b@x.com")

    def test_amistad_nueva_se_guarda(self):
        bd, s = armar({c.OBTENER_ESTUDIANTE: conocidos("a@x.com", "b@x.com"), c.EXISTE_AMISTAD: [{"total": 0}]})
        s.agregar_amistad("A@x.com", "b@x.com")
        self.assertEqual(bd.llamadas[-1][1], {"correo_a": "a@x.com", "correo_b": "b@x.com"})

    def test_amistad_usuario_inexistente(self):
        _, s = armar()
        with self.assertRaises(ErrorNoEncontrado):
            s.agregar_amistad("a@x.com", "b@x.com")

    def test_eliminar_amistad_inexistente(self):
        _, s = armar({c.OBTENER_ESTUDIANTE: conocidos("a@x.com", "b@x.com")})
        with self.assertRaises(ErrorNoEncontrado):
            s.eliminar_amistad("a@x.com", "b@x.com")

    def test_camino_mismo_estudiante_y_sin_camino(self):
        _, s = armar({c.OBTENER_ESTUDIANTE: conocidos("a@x.com", "b@x.com")})
        with self.assertRaises(ErrorDeValidacion):
            s.camino_mas_corto("a@x.com", "A@x.com")
        with self.assertRaises(ErrorNoEncontrado):  # la consulta no devuelve filas
            s.camino_mas_corto("a@x.com", "b@x.com")
        _, s = armar({c.OBTENER_ESTUDIANTE: conocidos("a@x.com", "b@x.com"),
                      c.CAMINO_MAS_CORTO: [{"camino": ["A", "C", "B"], "grados": 2}]})
        self.assertEqual(s.camino_mas_corto("a@x.com", "b@x.com")["grados"], 2)

    def test_vecindad_valida_grados_e_inserta_entero(self):
        bd, s = armar()
        with self.assertRaises(ErrorDeValidacion):
            s.vecindad("ana@x.com", 9)
        consulta_2 = c.VECINDAD.replace("__GRADOS__", "2")
        bd, s = armar({c.OBTENER_ESTUDIANTE: [{"estudiante": estudiante()}], consulta_2: [{"correo": "b@x.com", "nombre": "B", "grados": 1}]})
        self.assertEqual(len(s.vecindad("ana@x.com", "2")), 1)
        self.assertNotIn("__GRADOS__", bd.llamadas[-1][0])

    def test_limite_y_nivel_fuera_de_rango(self):
        _, s = armar({c.OBTENER_ESTUDIANTE: [{"estudiante": estudiante()}]})
        with self.assertRaises(ErrorDeValidacion):
            s.sugerir_amigos("ana@x.com", 0)
        with self.assertRaises(ErrorDeValidacion):
            s.agregar_habilidad("ana@x.com", "python", 6)
        with self.assertRaises(ErrorDeValidacion):
            s.mas_conectados("abc")


class PruebasConsultas(unittest.TestCase):
    TODAS = {n: v for n, v in vars(c).items() if n.isupper() and isinstance(v, str)}

    def test_delimitadores_balanceados(self):
        pares = {")": "(", "]": "[", "}": "{"}
        for nombre, texto in self.TODAS.items():
            pila = []
            for ch in texto:
                if ch in "([{":
                    pila.append(ch)
                elif ch in pares:
                    self.assertTrue(pila and pila.pop() == pares[ch], f"{nombre}: delimitadores desbalanceados")
            self.assertFalse(pila, f"{nombre}: delimitadores sin cerrar")
            self.assertEqual(texto.count("'") % 2, 0, f"{nombre}: comillas impares")

    def test_solo_vecindad_usa_marcador(self):
        for nombre, texto in self.TODAS.items():
            self.assertEqual("__GRADOS__" in texto, nombre == "VECINDAD", nombre)

    def test_cada_metodo_del_repositorio_envia_los_parametros_que_su_consulta_declara(self):
        """La ConexionFalsa falla si faltan o sobran parámetros en alguna llamada."""
        bd = ConexionFalsa()
        repo = RepositorioRed(bd)
        argumentos = {
            "datos": {"materias": [], "estudiantes": [], "amistades": [], "inscripciones": [], "habilidades": []},
            "cambios": {"nombre": "X"},
        }
        llamados = 0
        for nombre, metodo in inspect.getmembers(repo, inspect.ismethod):
            if nombre.startswith("_"):
                continue
            params = inspect.signature(metodo).parameters
            kwargs = {}
            for p in params:
                kwargs[p] = argumentos.get(p, 2 if p in ("limite", "grados", "semestre", "nivel") else "x")
            try:
                metodo(**kwargs)
            except (IndexError, KeyError):
                pass  # la respuesta vacía no tiene la forma esperada; solo importa el envío
            llamados += 1
        self.assertGreaterEqual(llamados, 30)
        self.assertGreaterEqual(len(bd.llamadas), 30)


if __name__ == "__main__":
    unittest.main()
