# UniRed: red de estudiantes sobre Neo4j AuraDB

**Materia:** Bases de Datos Avanzadas · **Profesor:** Fernando Martínez Chacón · Universidad Anáhuac Mayab
**Autor:** Jennifer Briceño

Aplicación de consola en Python conectada a una base de datos de **grafos** (Neo4j AuraDB, servicio administrado en la nube). Permite registrar estudiantes, sus amistades, materias y habilidades, y responder preguntas que se resuelven recorriendo el grafo: sugerencia de amigos, camino más corto entre dos personas, vecindad y recomendación de equipo.

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
python3 main.py                         # abre la aplicación
```

- `python3 -m scripts.seed --reiniciar` borra los Estudiantes, Materias y Habilidades de la base y vuelve a cargar los datos de ejemplo (pide confirmación).
- `python3 -m unittest discover -v` corre las pruebas unitarias (no necesitan internet).

## 3. Qué hace la aplicación

| Menú | Opciones |
|---|---|
| Estudiantes | crear, listar, buscar por correo o nombre, modificar, eliminar (con sus relaciones), ver perfil completo |
| Relaciones, materias y habilidades | agregar o eliminar amistad, ver amigos, crear y listar materias, inscribir o dar de baja, agregar o quitar habilidad |
| Consultas del grafo | sugerir amigos (amigos de amigos), camino más corto, amigos en común, vecindad hasta N grados, compañeros de materia, sugerir equipo, más conectados, habilidades populares |

Modelo: `(:Estudiante)-[:AMIGO_DE]-(:Estudiante)`, `(:Estudiante)-[:CURSA {periodo}]->(:Materia)`, `(:Estudiante)-[:DOMINA {nivel}]->(:Habilidad)`.

## 4. Estructura del proyecto

```
main.py                     punto de entrada
app/config.py               variables de entorno (rechaza localhost)
app/conexion.py             driver oficial de Neo4j
app/consultas.py            catálogo de consultas Cypher
app/repositorio.py          ejecuta las consultas
app/servicio.py             reglas de negocio y validaciones
app/validaciones.py         validación y normalización de datos
app/menu.py, entrada.py     interfaz de consola
app/errores.py              excepciones propias
scripts/seed.py             carga de datos iniciales (idempotente)
scripts/datos_iniciales.py  datos ficticios: 14 estudiantes, 8 materias, 19 amistades...
scripts/verificar_conexion.py
pruebas/test_aplicacion.py  pruebas unitarias
docs/                       PDF de diseño, figuras y guía de defensa
```

## 5. Ver el grafo en el navegador (útil para la demostración)

En la consola de Aura abre **Query** (o **Explore**) y ejecuta:

```cypher
MATCH p = (:Estudiante)-[:AMIGO_DE]-(:Estudiante) RETURN p LIMIT 50
```

## 6. Problemas frecuentes

| Mensaje | Qué hacer |
|---|---|
| `Faltan variables de entorno` | Falta el archivo `.env` o está en otra carpeta. Debe estar junto a `main.py`. |
| `rechazó el usuario o la contraseña` | Copia de nuevo los datos del archivo de credenciales. Si perdiste la contraseña, en Aura usa **Reset password**. |
| `No se pudo conectar` | Revisa tu internet y que la instancia esté en **Running**. Las instancias gratuitas se **pausan por inactividad**: reanúdala en console.neo4j.io **antes del examen**. |
| `CERTIFICATE_VERIFY_FAILED` (macOS con Python de python.org) | Ejecuta `Install Certificates.command` de la carpeta de Python en Aplicaciones. |
| `NEO4J_URI apunta a una máquina local` | La tarea exige base en la nube: usa la URI `neo4j+s://...databases.neo4j.io`. |
