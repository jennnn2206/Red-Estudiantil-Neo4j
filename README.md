# UniRed: red de estudiantes sobre Neo4j AuraDB

**Materia:** Bases de Datos Avanzadas · **Profesor:** Fernando Martínez Chacón · Universidad Anáhuac Mayab
**Autor:** Jennifer Briceño

Aplicación en Python, con **interfaz web** y **versión de consola**, conectada a una base de datos de **grafos** (Neo4j AuraDB, servicio administrado en la nube). Permite registrar estudiantes, sus amistades, materias y habilidades, y responder preguntas que se resuelven recorriendo el grafo: sugerencia de amigos, camino más corto entre dos personas, vecindad y recomendación de equipo.

La justificación del paradigma, la arquitectura, el modelo y el catálogo de consultas están en `docs/diseno_unired.pdf`.

## Requisitos

- Python 3.10 o superior
- Una instancia gratuita de Neo4j AuraDB (se crea en 5 minutos, abajo)
- Conexión a internet

## 1. Crear la instancia en la nube (una sola vez)

1. Entra a <https://console.neo4j.io> e inicia sesión (puedes usar tu cuenta de Google).
2. Pulsa **Create instance** y elige **AuraDB Free**. Ponle un nombre, por ejemplo `unired`.
3. **Muy importante:** en la ventana que aparece pulsa **Download and continue** para bajar el archivo de credenciales (`Neo4j-xxxx-Created-....txt`). La contraseña solo se muestra esta vez.
4. Espera uno o dos minutos hasta que el estado sea **Running**.
5. Renombra el archivo descargado a `.env` y colócalo en la carpeta del proyecto (junto a `main.py`). Ya contiene `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` y `NEO4J_DATABASE`. Si prefieres, copia `.env.example` como `.env` y llena los datos a mano.

> El archivo `.env` está en `.gitignore`: nunca lo subas a GitHub. Las credenciales no están escritas en el código.

## 2. Instalar y ejecutar

```bash
cd red_estudiantil_neo4j
python3 -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

python3 -m scripts.verificar_conexion   # comprueba que las credenciales funcionan
python3 -m scripts.seed                 # crea restricciones y carga los datos de ejemplo
python3 main.py                         # versión de consola (terminal)
uvicorn app.web.api:app --reload        # versión web (frontend)
```

Con el servidor web corriendo, abre **<http://127.0.0.1:8000>** en el navegador. La documentación interactiva de la API queda en <http://127.0.0.1:8000/docs>. Para detenerlo, `Ctrl+C`.

- Si la instancia de AuraDB está pausada, el servidor arranca igual: la página muestra «Sin conexión con la base» y la API responde 503 con el motivo. Al reanudar la instancia se reconecta sola (no hace falta reiniciar uvicorn).

- `python3 -m scripts.seed --reiniciar` borra los Estudiantes, Materias y Habilidades de la base y vuelve a cargar los datos de ejemplo (pide confirmación).
- `python3 -m unittest discover -v` corre las pruebas unitarias, incluidas las del API web (no necesitan internet).
- `python3 -m scripts.probar_api` (con uvicorn corriendo en otra terminal) prueba **todos** los endpoints contra la base real con datos temporales, los borra al terminar y comprueba que los conteos de la base quedaron iguales.

## 3. Qué hace la aplicación

| Menú | Opciones |
|---|---|
| Estudiantes | crear, listar, buscar por correo o nombre, modificar, eliminar (con sus relaciones), ver perfil completo |
| Relaciones, materias y habilidades | agregar o eliminar amistad, ver amigos, crear y listar materias, inscribir o dar de baja, agregar o quitar habilidad |
| Consultas del grafo | sugerir amigos (amigos de amigos), camino más corto, amigos en común, vecindad hasta N grados, compañeros de materia, sugerir equipo, más conectados, habilidades populares |

Modelo: `(:Estudiante)-[:AMIGO_DE]-(:Estudiante)`, `(:Estudiante)-[:CURSA {periodo}]->(:Materia)`, `(:Estudiante)-[:DOMINA {nivel}]->(:Habilidad)`.

### Interfaz web

| Sección | Qué hace |
|---|---|
| Estudiantes | tabla con búsqueda por nombre, formulario para crear y editar, eliminar con confirmación y perfil (amigos, materias y habilidades) |
| Red | grafo interactivo de estudiantes y amistades (opcionalmente materias y habilidades); al elegir origen y destino resalta el camino más corto; clic en un nodo o relación muestra sus datos |
| Relaciones | agregar y quitar amistades, crear materias, inscribir y dar de baja, agregar o actualizar y quitar habilidades |
| Consultas | un panel por cada una de las 8 consultas del grafo, con listas desplegables y resultados en tabla |

## 4. API REST

Todo bajo `/api`, en JSON. Los correos llevan `@` y puntos, por eso viajan como parámetros de consulta (`?correo=...`) o en el cuerpo, nunca en la ruta.

| Método y ruta | Descripción |
|---|---|
| `GET /api/salud` | estado del servidor y de la conexión |
| `GET /api/estudiantes[?q=texto]` | listar todos o buscar por nombre |
| `POST /api/estudiantes` | crear `{correo, nombre, carrera, semestre}` |
| `GET /api/estudiantes/detalle?correo=` | obtener uno |
| `GET /api/estudiantes/perfil?correo=` | estudiante con amigos, materias y habilidades |
| `PATCH /api/estudiantes?correo=` | modificar parcial `{nombre?, carrera?, semestre?}` |
| `DELETE /api/estudiantes?correo=` | eliminar (con sus relaciones) |
| `GET /api/amistades?correo=` | amigos de un estudiante |
| `POST /api/amistades` | agregar `{correo_a, correo_b}` |
| `DELETE /api/amistades?correo_a=&correo_b=` | quitar amistad |
| `GET /api/materias` · `POST /api/materias` | listar · crear `{codigo, nombre}` |
| `POST /api/inscripciones` | inscribir `{correo, codigo, periodo}` (periodo como `2026-Otoño`) |
| `DELETE /api/inscripciones?correo=&codigo=` | dar de baja |
| `GET /api/habilidades` | nombres de habilidades existentes |
| `POST /api/habilidades` | agregar o actualizar nivel `{correo, habilidad, nivel 1-5}` |
| `DELETE /api/habilidades?correo=&habilidad=` | quitar |
| `GET /api/consultas/sugerir-amigos?correo=&limite=` | amigos de amigos |
| `GET /api/consultas/camino?origen=&destino=` | camino más corto (nombres, correos y grados) |
| `GET /api/consultas/amigos-en-comun?correo_a=&correo_b=` | amigos en común |
| `GET /api/consultas/vecindad?correo=&grados=1..4` | alcanzables hasta N grados |
| `GET /api/consultas/companeros?correo=` | compañeros de materia |
| `GET /api/consultas/equipo?correo=&codigo=&limite=` | sugerir equipo para una materia |
| `GET /api/consultas/mas-conectados?limite=` | ranking por número de amigos |
| `GET /api/consultas/habilidades-populares?limite=` | habilidades más frecuentes |
| `GET /api/grafo[?materias=true&habilidades=true]` | nodos y aristas para dibujar el grafo |

Errores: siempre JSON `{"error": "...", "mensaje": "texto en español"}` con estos códigos: validación **422**, no encontrado **404**, duplicado **409**, sin conexión con la nube **503**, error de Neo4j **500**.

## 5. Estructura del proyecto

```
main.py                     punto de entrada (consola)
app/config.py               variables de entorno (rechaza localhost)
app/conexion.py             driver oficial de Neo4j
app/consultas.py            catálogo de consultas Cypher
app/repositorio.py          ejecuta las consultas
app/servicio.py             reglas de negocio y validaciones
app/validaciones.py         validación y normalización de datos
app/menu.py, entrada.py     interfaz de consola
app/errores.py              excepciones propias
app/web/api.py              API REST con FastAPI; sirve también el frontend
web/static/index.html       frontend (una sola página)
web/static/css/, js/        estilos y módulos JavaScript (sin npm ni compilación)
web/static/vendor/          vis-network 9.1.9 local (dibuja el grafo sin depender de internet)
scripts/seed.py             carga de datos iniciales (idempotente)
scripts/datos_iniciales.py  datos ficticios: 14 estudiantes, 8 materias, 19 amistades...
scripts/verificar_conexion.py
scripts/probar_api.py       prueba de todos los endpoints contra la base real
pruebas/test_aplicacion.py  pruebas unitarias (servicio, validaciones, consultas)
pruebas/test_api.py         pruebas del API con un servicio simulado
docs/                       PDF de diseño, figuras y guía de defensa
```

## 6. Ver el grafo en la consola de Aura

La pestaña **Red** de la interfaz web ya dibuja el grafo. Para verlo también desde Neo4j, en la consola de Aura abre **Query** (o **Explore**) y ejecuta:

```cypher
MATCH p = (:Estudiante)-[:AMIGO_DE]-(:Estudiante) RETURN p LIMIT 50
```

## 7. Problemas frecuentes

| Mensaje | Qué hacer |
|---|---|
| `Faltan variables de entorno` | Falta el archivo `.env` o está en otra carpeta. Debe estar junto a `main.py`. |
| `rechazó el usuario o la contraseña` | Copia de nuevo los datos del archivo de credenciales. Si perdiste la contraseña, en Aura usa **Reset password**. |
| `No se pudo conectar` | Revisa tu internet y que la instancia esté en **Running**. Las instancias gratuitas se **pausan por inactividad**: reanúdala en console.neo4j.io **antes del examen**. |
| `CERTIFICATE_VERIFY_FAILED` (macOS con Python de python.org) | Ejecuta `Install Certificates.command` de la carpeta de Python en Aplicaciones. |
| La página dice «Sin conexión con la base» | La instancia está pausada o sin internet. Reanúdala en console.neo4j.io; la web se reconecta sola en unos segundos. |
| `Address already in use` al arrancar uvicorn | Ya hay otro servidor en el puerto 8000: ciérralo o usa `uvicorn app.web.api:app --port 8001`. |
| `NEO4J_URI apunta a una máquina local` | La tarea exige base en la nube: usa la URI `neo4j+s://...databases.neo4j.io`. |
