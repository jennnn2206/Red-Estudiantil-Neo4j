// Cliente de la API de UniRed. Todas las llamadas pasan por aquí.
// Los parámetros viajan con URLSearchParams, que codifica "@", "." y acentos.

/** Error con el mensaje en español que devuelve la API y su código HTTP. */
export class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje);
    this.estado = estado;
  }
}

/**
 * Hace una petición a /api.
 * @param {string} metodo GET, POST, PATCH o DELETE
 * @param {string} ruta   p. ej. "/estudiantes"
 * @param {{query?: object, cuerpo?: object}} opciones
 */
export async function api(metodo, ruta, { query, cuerpo } = {}) {
  let url = `/api${ruta}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [clave, valor] of Object.entries(query)) {
      if (valor !== undefined && valor !== null && valor !== "") params.set(clave, valor);
    }
    const texto = params.toString();
    if (texto) url += `?${texto}`;
  }
  const opciones = { method: metodo, headers: { Accept: "application/json" } };
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }

  let respuesta;
  try {
    respuesta = await fetch(url, opciones);
  } catch {
    throw new ErrorApi("No se pudo contactar al servidor. ¿Está corriendo uvicorn?", 0);
  }

  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    /* respuesta sin JSON */
  }
  if (!respuesta.ok) {
    const mensaje = (datos && datos.mensaje) || `Error ${respuesta.status} del servidor.`;
    throw new ErrorApi(mensaje, respuesta.status);
  }
  return datos;
}
