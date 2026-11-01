# Guía rápida para la exposición (8 a 10 minutos)

## Demostración en vivo (4 minutos)
Antes de entrar: instancia en **Running**, `python3 -m scripts.seed` ya ejecutado, terminal abierta en la carpeta y la consola de Aura abierta en **Query**.

1. (30 s) `python3 main.py`. Decir: la app corre en mi equipo y la base está en Neo4j AuraDB, en la nube.
2. (60 s) CRUD: Estudiantes → crear uno nuevo → buscar por correo → modificar el semestre → intentar crear el mismo correo otra vez (error de duplicado controlado).
3. (60 s) Relaciones: agregar amistad entre el nuevo y Ana → ver amigos → agregar una habilidad.
4. (90 s) Consultas del grafo: sugerir amigos para Ana, camino más corto entre Mateo y Andrés, sugerir equipo para Ana en BDA-401.
5. (30 s) Persistencia: salir, volver a entrar y listar. Mostrar el grafo en la consola de Aura. Eliminar al estudiante de prueba.

## Preguntas probables y respuesta corta
- **¿Por qué grafo y no SQL?** Porque las preguntas son recorridos de profundidad variable (amigos de amigos, camino más corto). En SQL cada salto es un JOIN y el camino más corto exige WITH RECURSIVE; en Cypher es un patrón y shortestPath().
- **¿Por qué no clave valor?** Redis busca por llave, pero no recorre conexiones; habría que hacer muchas consultas desde la aplicación y combinar los resultados a mano.
- **¿Cuándo usarías SQL?** Reportes agregados sobre muchos datos tabulares o esquemas rígidos con integridad declarativa compleja.
- **¿Por qué Habilidad es un nodo?** Para poder preguntar quién más la domina y agregarla; en una lista dentro del estudiante no se puede recorrer.
- **¿Por qué AMIGO_DE se guarda en un solo sentido?** La amistad es simétrica; MERGE sin dirección evita duplicarla y las consultas la recorren sin dirección.
- **¿Cómo evitas inyección?** Todas las consultas usan parámetros ($correo). La única excepción es la profundidad de la vecindad (Cypher no permite parametrizarla): se valida como entero de 1 a 4.
- **¿Cómo manejas credenciales?** Variables de entorno desde `.env`, que está en `.gitignore`. La app rechaza localhost y exige `neo4j+s://` (TLS).
- **¿Qué hace la restricción UNIQUE?** Impide dos estudiantes con el mismo correo y crea un índice, que acelera el punto de partida de cada consulta.
- **¿Consistencia?** Neo4j es ACID: cada escritura es una transacción. `execute_query` la confirma o revierte y maneja los bookmarks para consistencia causal.
- **¿Rendimiento?** Las consultas arrancan en un nodo indexado y recorren sus vecinos (adyacencia sin índices); los recorridos tienen límite de profundidad y LIMIT en los resultados.
- **¿Qué usa el driver para conectarse?** `GraphDatabase.driver(uri, auth=...)` y `driver.execute_query(...)` con `RoutingControl.READ` o `WRITE` (archivo `app/conexion.py`).
