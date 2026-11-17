"""Pruebas del API web con un servicio simulado (no necesitan internet ni AuraDB).

Se usa ``TestClient`` de FastAPI y un ``ServicioRed`` falso creado con
``create_autospec``: si la API llamara a un método inexistente o con
argumentos equivocados, la prueba fallaría.
"""
from __future__ import annotations

import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app.errores import (
    ErrorDeBaseDeDatos,
    ErrorDeConexion,
    ErrorDeValidacion,
    ErrorDuplicado,
    ErrorNoEncontrado,
)
from app.servicio import ServicioRed
from app.web.api import crear_app

ANA = {"correo": "ana@x.com", "nombre": "Ana", "carrera": "ITI", "semestre": 5, "creado": "2026-11-17"}


class PruebasApi(unittest.TestCase):
    def setUp(self):
        self.servicio = mock.create_autospec(ServicioRed, instance=True)
        # raise_server_exceptions=False: así se prueba la respuesta 500 en JSON.
        self.cliente = TestClient(crear_app(self.servicio), raise_server_exceptions=False)
        self.cliente.__enter__()  # ejecuta el lifespan
        self.addCleanup(self.cliente.__exit__, None, None, None)

    def assertError(self, respuesta, codigo, texto):
        self.assertEqual(respuesta.status_code, codigo, respuesta.text)
        cuerpo = respuesta.json()
        self.assertIn("mensaje", cuerpo)
        self.assertIn(texto, cuerpo["mensaje"])

    # --- estudiantes ---------------------------------------------------
    def test_crear_estudiante(self):
        self.servicio.crear_estudiante.return_value = ANA
        r = self.cliente.post("/api/estudiantes", json={
            "correo": "ana@x.com", "nombre": "Ana", "carrera": "ITI", "semestre": "5",
        })
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["estudiante"], ANA)
        self.assertIn("Estudiante creado", r.json()["mensaje"])
        self.servicio.crear_estudiante.assert_called_once_with("ana@x.com", "Ana", "ITI", "5")

    def test_crear_duplicado_409(self):
        self.servicio.crear_estudiante.side_effect = ErrorDuplicado("Ya existe un estudiante con el correo 'ana@x.com'.")
        r = self.cliente.post("/api/estudiantes", json={"correo": "ana@x.com", "nombre": "Ana", "carrera": "ITI", "semestre": 5})
        self.assertError(r, 409, "Ya existe")
        self.assertEqual(r.json()["error"], "ErrorDuplicado")

    def test_validacion_del_servicio_422(self):
        self.servicio.crear_estudiante.side_effect = ErrorDeValidacion("'semestre' debe estar entre 1 y 12.")
        r = self.cliente.post("/api/estudiantes", json={"correo": "ana@x.com", "nombre": "Ana", "carrera": "ITI", "semestre": 40})
        self.assertError(r, 422, "entre 1 y 12")

    def test_falta_parametro_422_en_espanol(self):
        r = self.cliente.get("/api/estudiantes/detalle")
        self.assertError(r, 422, "falta el dato 'correo'")
        self.servicio.obtener_estudiante.assert_not_called()

    def test_no_encontrado_404(self):
        self.servicio.obtener_estudiante.side_effect = ErrorNoEncontrado("No existe ningún estudiante con el correo 'zz@x.com'.")
        r = self.cliente.get("/api/estudiantes/detalle", params={"correo": "zz@x.com"})
        self.assertError(r, 404, "No existe")

    def test_correo_con_arroba_y_puntos_llega_intacto(self):
        self.servicio.perfil.return_value = {"estudiante": ANA, "amigos": [], "materias": [], "habilidades": []}
        r = self.cliente.get("/api/estudiantes/perfil", params={"correo": "ana.lopez+x@uni.red.mx"})
        self.assertEqual(r.status_code, 200)
        self.servicio.perfil.assert_called_once_with("ana.lopez+x@uni.red.mx")

    def test_listar_y_buscar(self):
        self.servicio.listar_estudiantes.return_value = [ANA]
        self.servicio.buscar_estudiantes.return_value = []
        self.assertEqual(self.cliente.get("/api/estudiantes").json(), [ANA])
        self.assertEqual(self.cliente.get("/api/estudiantes", params={"q": "zzz"}).json(), [])
        self.servicio.buscar_estudiantes.assert_called_once_with("zzz")

    def test_modificar_parcial_y_eliminar(self):
        self.servicio.actualizar_estudiante.return_value = {**ANA, "semestre": 6}
        r = self.cliente.patch("/api/estudiantes", params={"correo": "ana@x.com"}, json={"semestre": 6})
        self.assertEqual(r.status_code, 200)
        self.servicio.actualizar_estudiante.assert_called_once_with("ana@x.com", None, None, 6)

        self.servicio.eliminar_estudiante.return_value = {"nombre": "Ana", "relaciones": 3}
        r = self.cliente.delete("/api/estudiantes", params={"correo": "ana@x.com"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("3 relación", r.json()["mensaje"])

    # --- relaciones ----------------------------------------------------
    def test_amistad_e_inscripcion_y_habilidad(self):
        self.servicio.agregar_amistad.return_value = ("Ana", "Beto")
        r = self.cliente.post("/api/amistades", json={"correo_a": "ana@x.com", "correo_b": "beto@x.com"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["mensaje"], "Ana y Beto ahora son amigos.")

        r = self.cliente.post("/api/inscripciones", json={"correo": "ana@x.com", "codigo": "BDA-401", "periodo": "2026-Otoño"})
        self.assertEqual(r.status_code, 201)
        self.servicio.inscribir_materia.assert_called_once_with("ana@x.com", "BDA-401", "2026-Otoño")

        r = self.cliente.post("/api/habilidades", json={"correo": "ana@x.com", "habilidad": "Python", "nivel": 4})
        self.assertEqual(r.status_code, 200)
        self.servicio.agregar_habilidad.assert_called_once_with("ana@x.com", "Python", 4)

    # --- consultas y grafo --------------------------------------------
    def test_consulta_camino_mas_corto(self):
        self.servicio.camino_mas_corto.return_value = {
            "camino": ["Ana", "Beto", "Caro"], "correos": ["a@x.com", "b@x.com", "c@x.com"], "grados": 2,
        }
        r = self.cliente.get("/api/consultas/camino", params={"origen": "a@x.com", "destino": "c@x.com"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["grados"], 2)
        self.servicio.camino_mas_corto.assert_called_once_with("a@x.com", "c@x.com")

    def test_consulta_vecindad_pasa_grados_al_servicio(self):
        self.servicio.vecindad.return_value = [{"correo": "b@x.com", "nombre": "Beto", "grados": 1}]
        r = self.cliente.get("/api/consultas/vecindad", params={"correo": "a@x.com", "grados": "3"})
        self.assertEqual(r.status_code, 200)
        self.servicio.vecindad.assert_called_once_with("a@x.com", "3")

    def test_limite_por_defecto(self):
        self.servicio.mas_conectados.return_value = []
        self.assertEqual(self.cliente.get("/api/consultas/mas-conectados").json(), [])
        self.servicio.mas_conectados.assert_called_once_with("5")

    def test_grafo(self):
        self.servicio.grafo.return_value = {"nodos": [], "aristas": []}
        r = self.cliente.get("/api/grafo", params={"materias": "true"})
        self.assertEqual(r.json(), {"nodos": [], "aristas": []})
        self.servicio.grafo.assert_called_once_with(incluir_materias=True, incluir_habilidades=False)

    # --- errores de infraestructura -----------------------------------
    def test_conexion_503_y_base_500(self):
        self.servicio.listar_materias.side_effect = ErrorDeConexion("Se perdió la conexión con la instancia en la nube.")
        self.assertError(self.cliente.get("/api/materias"), 503, "conexión")
        self.servicio.listar_materias.side_effect = ErrorDeBaseDeDatos("Neo4j rechazó la consulta.")
        self.assertError(self.cliente.get("/api/materias"), 500, "Neo4j")

    def test_error_inesperado_500_en_json(self):
        self.servicio.listar_materias.side_effect = RuntimeError("boom")
        self.assertError(self.cliente.get("/api/materias"), 500, "problema inesperado")

    # --- frontend ------------------------------------------------------
    def test_sirve_frontend_y_libreria_local(self):
        r = self.cliente.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("UniRed", r.text)
        self.assertNotIn("neo4j+s://", r.text)
        self.assertEqual(self.cliente.get("/static/vendor/vis-network.min.js").status_code, 200)
        self.assertEqual(self.cliente.get("/static/js/main.js").status_code, 200)


class PruebasGrafoServicio(unittest.TestCase):
    """El servicio arma nodos y aristas con identificadores por tipo."""

    def test_grafo_con_materias_y_habilidades(self):
        repo = mock.Mock()
        repo.grafo_estudiantes.return_value = [
            {"estudiante": {"correo": "a@x.com", "nombre": "Ana", "carrera": "ITI", "semestre": 5}, "amigos": 1},
            {"estudiante": {"correo": "b@x.com", "nombre": "Beto", "carrera": "ITI", "semestre": 3}, "amigos": 1},
        ]
        repo.grafo_amistades.return_value = [{"origen": "a@x.com", "destino": "b@x.com", "desde": "2025-01-01"}]
        repo.listar_materias.return_value = [{"codigo": "BDA-401", "nombre": "BDA"}]
        repo.grafo_inscripciones.return_value = [{"origen": "a@x.com", "destino": "BDA-401", "periodo": "2026-Otoño"}]
        repo.listar_habilidades.return_value = ["python"]
        repo.grafo_habilidades.return_value = [{"origen": "b@x.com", "destino": "python", "nivel": 4}]

        solo_amistades = ServicioRed(repo).grafo()
        self.assertEqual(len(solo_amistades["nodos"]), 2)
        self.assertEqual(solo_amistades["aristas"][0]["origen"], "e:a@x.com")

        completo = ServicioRed(repo).grafo(incluir_materias=True, incluir_habilidades=True)
        ids = {n["id"] for n in completo["nodos"]}
        self.assertEqual(ids, {"e:a@x.com", "e:b@x.com", "m:BDA-401", "h:python"})
        self.assertEqual({a["tipo"] for a in completo["aristas"]}, {"AMIGO_DE", "CURSA", "DOMINA"})
        destinos = {a["destino"] for a in completo["aristas"]}
        self.assertTrue(destinos <= ids, "toda arista apunta a un nodo existente")


if __name__ == "__main__":
    unittest.main()
