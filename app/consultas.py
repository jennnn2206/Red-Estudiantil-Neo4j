"""Catálogo de consultas Cypher de la aplicación.

Todas usan parámetros (``$nombre``): los datos nunca se pegan dentro del texto
de la consulta. La única excepción es la profundidad de los recorridos, porque
Cypher no permite parametrizar los límites de ``*1..N``; ese número se valida
como entero entre 1 y 4 antes de insertarse.
"""

# ----------------------------------------------------------------------
# Esquema: restricciones de unicidad (también crean un índice automático)
# ----------------------------------------------------------------------
ESQUEMA = [
    "CREATE CONSTRAINT estudiante_correo_unico IF NOT EXISTS "
    "FOR (e:Estudiante) REQUIRE e.correo IS UNIQUE",
    "CREATE CONSTRAINT materia_codigo_unico IF NOT EXISTS "
    "FOR (m:Materia) REQUIRE m.codigo IS UNIQUE",
    "CREATE CONSTRAINT habilidad_nombre_unico IF NOT EXISTS "
    "FOR (h:Habilidad) REQUIRE h.nombre IS UNIQUE",
]

# ----------------------------------------------------------------------
# CRUD de Estudiante (nodo)
# ----------------------------------------------------------------------
CREAR_ESTUDIANTE = """
CREATE (e:Estudiante {
    correo: $correo, nombre: $nombre, carrera: $carrera,
    semestre: $semestre, creado: toString(date())
})
RETURN e {.*} AS estudiante
"""

OBTENER_ESTUDIANTE = """
MATCH (e:Estudiante {correo: $correo})
RETURN e {.*} AS estudiante
"""

LISTAR_ESTUDIANTES = """
MATCH (e:Estudiante)
RETURN e {.*} AS estudiante
ORDER BY e.nombre
"""

BUSCAR_ESTUDIANTES = """
MATCH (e:Estudiante)
WHERE toLower(e.nombre) CONTAINS toLower($texto)
RETURN e {.*} AS estudiante
ORDER BY e.nombre
"""

ACTUALIZAR_ESTUDIANTE = """
MATCH (e:Estudiante {correo: $correo})
SET e += $cambios
RETURN e {.*} AS estudiante
"""

ELIMINAR_ESTUDIANTE = """
MATCH (e:Estudiante {correo: $correo})
WITH e, e.nombre AS nombre, COUNT { (e)--() } AS relaciones
DETACH DELETE e
RETURN nombre, relaciones
"""

# ----------------------------------------------------------------------
# Materias (nodo)
# ----------------------------------------------------------------------
CREAR_MATERIA = """
CREATE (m:Materia {codigo: $codigo, nombre: $nombre})
RETURN m {.*} AS materia
"""

OBTENER_MATERIA = """
MATCH (m:Materia {codigo: $codigo})
RETURN m {.*} AS materia
"""

LISTAR_MATERIAS = """
MATCH (m:Materia)
RETURN m {.*} AS materia
ORDER BY m.codigo
"""

# ----------------------------------------------------------------------
# Relaciones: AMIGO_DE, CURSA, DOMINA
# ----------------------------------------------------------------------
EXISTE_AMISTAD = """
MATCH (:Estudiante {correo: $correo_a})-[r:AMIGO_DE]-
      (:Estudiante {correo: $correo_b})
RETURN count(r) AS total
"""

# Patrón sin dirección en MERGE: no crea una segunda relación si ya existe en cualquier sentido.
AGREGAR_AMISTAD = """
MATCH (a:Estudiante {correo: $correo_a}), (b:Estudiante {correo: $correo_b})
MERGE (a)-[r:AMIGO_DE]-(b)
ON CREATE SET r.desde = toString(date())
RETURN a.nombre AS a, b.nombre AS b
"""

ELIMINAR_AMISTAD = """
MATCH (a:Estudiante {correo: $correo_a})-[r:AMIGO_DE]-(b:Estudiante {correo: $correo_b})
DELETE r
RETURN a.nombre AS a, b.nombre AS b
"""

LISTAR_AMIGOS = """
MATCH (:Estudiante {correo: $correo})-[r:AMIGO_DE]-(amigo:Estudiante)
RETURN amigo {.correo, .nombre, .carrera, .semestre} AS estudiante, r.desde AS desde
ORDER BY amigo.nombre
"""

INSCRIBIR_MATERIA = """
MATCH (e:Estudiante {correo: $correo}), (m:Materia {codigo: $codigo})
MERGE (e)-[r:CURSA]->(m)
ON CREATE SET r.periodo = $periodo
RETURN e.nombre AS estudiante, m.nombre AS materia, r.periodo AS periodo
"""

BAJA_MATERIA = """
MATCH (:Estudiante {correo: $correo})-[r:CURSA]->(m:Materia {codigo: $codigo})
DELETE r
RETURN m.nombre AS materia
"""

MATERIAS_DE_ESTUDIANTE = """
MATCH (:Estudiante {correo: $correo})-[r:CURSA]->(m:Materia)
RETURN m {.*} AS materia, r.periodo AS periodo
ORDER BY m.codigo
"""

# MERGE de la habilidad: se crea el nodo la primera vez y se reutiliza después.
AGREGAR_HABILIDAD = """
MATCH (e:Estudiante {correo: $correo})
MERGE (h:Habilidad {nombre: $habilidad})
MERGE (e)-[r:DOMINA]->(h)
SET r.nivel = $nivel
RETURN e.nombre AS estudiante, h.nombre AS habilidad, r.nivel AS nivel
"""

QUITAR_HABILIDAD = """
MATCH (:Estudiante {correo: $correo})-[r:DOMINA]->(h:Habilidad {nombre: $habilidad})
DELETE r
RETURN h.nombre AS habilidad
"""

HABILIDADES_DE_ESTUDIANTE = """
MATCH (:Estudiante {correo: $correo})-[r:DOMINA]->(h:Habilidad)
RETURN h.nombre AS habilidad, r.nivel AS nivel
ORDER BY r.nivel DESC, h.nombre
"""

# ----------------------------------------------------------------------
# Consultas especializadas del paradigma de grafos
# ----------------------------------------------------------------------
# 1) Amigos de amigos que aún no son mis amigos (recorrido de 2 saltos).
SUGERIR_AMIGOS = """
MATCH (yo:Estudiante {correo: $correo})-[:AMIGO_DE]-(:Estudiante)
      -[:AMIGO_DE]-(sugerido:Estudiante)
WHERE sugerido <> yo AND NOT (yo)-[:AMIGO_DE]-(sugerido)
RETURN sugerido.correo AS correo, sugerido.nombre AS nombre, count(*) AS amigos_en_comun
ORDER BY amigos_en_comun DESC, nombre
LIMIT $limite
"""

# 2) Camino más corto entre dos estudiantes (hasta 6 grados de separación).
CAMINO_MAS_CORTO = """
MATCH (a:Estudiante {correo: $origen}), (b:Estudiante {correo: $destino})
MATCH ruta = shortestPath((a)-[:AMIGO_DE*..6]-(b))
RETURN [n IN nodes(ruta) | n.nombre] AS camino, length(ruta) AS grados
"""

# 3) Amigos en común de dos estudiantes.
AMIGOS_EN_COMUN = """
MATCH (:Estudiante {correo: $correo_a})-[:AMIGO_DE]-(comun:Estudiante)
      -[:AMIGO_DE]-(:Estudiante {correo: $correo_b})
RETURN DISTINCT comun.correo AS correo, comun.nombre AS nombre
ORDER BY nombre
"""

# 4) Vecindad: todos los alcanzables hasta N grados, con su distancia mínima.
#    __GRADOS__ se sustituye por un entero validado (1 a 4); Cypher no admite
#    parámetros en los límites de longitud variable.
VECINDAD = """
MATCH ruta = (yo:Estudiante {correo: $correo})
             -[:AMIGO_DE*1..__GRADOS__]-(otro:Estudiante)
WHERE otro <> yo
RETURN otro.correo AS correo, otro.nombre AS nombre, min(length(ruta)) AS grados
ORDER BY grados, nombre
"""

# 5) Compañeros que cursan las mismas materias que yo.
COMPANEROS_DE_MATERIA = """
MATCH (yo:Estudiante {correo: $correo})-[:CURSA]->(m:Materia)<-[:CURSA]-(c:Estudiante)
WHERE c <> yo
RETURN c.correo AS correo, c.nombre AS nombre,
       collect(m.nombre) AS materias_en_comun, count(m) AS total
ORDER BY total DESC, nombre
"""

# 6) Recomendador de equipo: compañeros de una materia con habilidades que yo no tengo.
SUGERIR_EQUIPO = """
MATCH (yo:Estudiante {correo: $correo})-[:CURSA]->(:Materia {codigo: $codigo})
      <-[:CURSA]-(c:Estudiante)
WHERE c <> yo
MATCH (c)-[d:DOMINA]->(h:Habilidad)
WHERE NOT (yo)-[:DOMINA]->(h)
RETURN c.correo AS correo, c.nombre AS nombre,
       collect(h.nombre) AS habilidades_que_aporta, sum(d.nivel) AS puntaje
ORDER BY puntaje DESC, nombre
LIMIT $limite
"""

# 7) Estudiantes más conectados (grado del nodo).
MAS_CONECTADOS = """
MATCH (e:Estudiante)
OPTIONAL MATCH (e)-[:AMIGO_DE]-(amigo:Estudiante)
RETURN e.nombre AS nombre, e.carrera AS carrera, count(DISTINCT amigo) AS amigos
ORDER BY amigos DESC, nombre
LIMIT $limite
"""

# 8) Habilidades más frecuentes y su nivel promedio.
HABILIDADES_POPULARES = """
MATCH (:Estudiante)-[d:DOMINA]->(h:Habilidad)
RETURN h.nombre AS habilidad, count(*) AS estudiantes, round(avg(d.nivel), 1) AS nivel_promedio
ORDER BY estudiantes DESC, habilidad
LIMIT $limite
"""

# ----------------------------------------------------------------------
# Carga inicial (seeding). Idempotente: se puede ejecutar varias veces.
# ----------------------------------------------------------------------
SEMILLA_MATERIAS = """
UNWIND $materias AS m
MERGE (x:Materia {codigo: m.codigo})
SET x.nombre = m.nombre
"""

SEMILLA_ESTUDIANTES = """
UNWIND $estudiantes AS s
MERGE (e:Estudiante {correo: s.correo})
ON CREATE SET e.creado = toString(date())
SET e.nombre = s.nombre, e.carrera = s.carrera, e.semestre = s.semestre
"""

SEMILLA_AMISTADES = """
UNWIND $amistades AS p
MATCH (a:Estudiante {correo: p.a}), (b:Estudiante {correo: p.b})
MERGE (a)-[r:AMIGO_DE]-(b)
ON CREATE SET r.desde = p.desde
"""

SEMILLA_INSCRIPCIONES = """
UNWIND $inscripciones AS i
MATCH (e:Estudiante {correo: i.correo}), (m:Materia {codigo: i.codigo})
MERGE (e)-[r:CURSA]->(m)
SET r.periodo = i.periodo
"""

SEMILLA_HABILIDADES = """
UNWIND $habilidades AS h
MATCH (e:Estudiante {correo: h.correo})
MERGE (x:Habilidad {nombre: h.habilidad})
MERGE (e)-[r:DOMINA]->(x)
SET r.nivel = h.nivel
"""

# Solo borra los tres tipos de nodo de esta aplicación, nada más.
REINICIAR_DATOS = """
MATCH (n)
WHERE n:Estudiante OR n:Materia OR n:Habilidad
DETACH DELETE n
"""

CONTAR_DATOS = """
RETURN
  COUNT { (:Estudiante) } AS estudiantes,
  COUNT { (:Materia) } AS materias,
  COUNT { (:Habilidad) } AS habilidades,
  COUNT { (:Estudiante)-[:AMIGO_DE]-(:Estudiante) } / 2 AS amistades,
  COUNT { ()-[:CURSA]->() } AS inscripciones,
  COUNT { ()-[:DOMINA]->() } AS dominios
"""
