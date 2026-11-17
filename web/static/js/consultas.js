// Sección 4: un panel por cada una de las 8 consultas del grafo.
// Los paneles se generan a partir de una definición declarativa.
import { api } from "./api.js";
import { avisarError, cargando, el, errorCarga, etiquetas, reemplazar, tabla } from "./ui.js";

const LIMITES = [3, 5, 10, 20, 50];

/** Definición de cada consulta: campos del formulario, ruta y columnas. */
const CONSULTAS = [
  {
    id: "sugerir", titulo: "1. Sugerir amigos",
    descripcion: "Amigos de mis amigos que todavía no son mis amigos (2 saltos).",
    campos: [{ tipo: "estudiante", nombre: "correo", etiqueta: "Estudiante" }, { tipo: "limite" }],
    ruta: "/consultas/sugerir-amigos",
    columnas: [
      { titulo: "Nombre", valor: (f) => f.nombre },
      { titulo: "Correo", valor: (f) => f.correo },
      { titulo: "Amigos en común", valor: (f) => f.amigos_en_comun, num: true },
    ],
  },
  {
    id: "camino", titulo: "2. Camino más corto",
    descripcion: "Ruta de amistades más corta entre dos estudiantes (hasta 6 grados).",
    campos: [
      { tipo: "estudiante", nombre: "origen", etiqueta: "Origen" },
      { tipo: "estudiante", nombre: "destino", etiqueta: "Destino" },
    ],
    ruta: "/consultas/camino",
    // La API devuelve un objeto; se convierte en una fila por paso del camino.
    filas: (r) => r.camino.map((nombre, i) => ({ paso: i, nombre, correo: r.correos[i] })),
    resumen: (r) => `${r.grados} grado(s) de separación: ${r.camino.join(" → ")}`,
    columnas: [
      { titulo: "Paso", valor: (f) => f.paso, num: true },
      { titulo: "Nombre", valor: (f) => f.nombre },
      { titulo: "Correo", valor: (f) => f.correo },
    ],
  },
  {
    id: "comun", titulo: "3. Amigos en común",
    descripcion: "Estudiantes que son amigos de ambos.",
    campos: [
      { tipo: "estudiante", nombre: "correo_a", etiqueta: "Estudiante A" },
      { tipo: "estudiante", nombre: "correo_b", etiqueta: "Estudiante B" },
    ],
    ruta: "/consultas/amigos-en-comun",
    columnas: [
      { titulo: "Nombre", valor: (f) => f.nombre },
      { titulo: "Correo", valor: (f) => f.correo },
    ],
  },
  {
    id: "vecindad", titulo: "4. Vecindad hasta N grados",
    descripcion: "Todos los estudiantes alcanzables y su distancia mínima.",
    campos: [{ tipo: "estudiante", nombre: "correo", etiqueta: "Estudiante" }, { tipo: "grados" }],
    ruta: "/consultas/vecindad",
    columnas: [
      { titulo: "Grados", valor: (f) => f.grados, num: true },
      { titulo: "Nombre", valor: (f) => f.nombre },
      { titulo: "Correo", valor: (f) => f.correo },
    ],
  },
  {
    id: "companeros", titulo: "5. Compañeros de materia",
    descripcion: "Quiénes cursan las mismas materias que el estudiante.",
    campos: [{ tipo: "estudiante", nombre: "correo", etiqueta: "Estudiante" }],
    ruta: "/consultas/companeros",
    columnas: [
      { titulo: "Nombre", valor: (f) => f.nombre },
      { titulo: "Materias en común", valor: (f) => etiquetas(f.materias_en_comun) },
      { titulo: "Total", valor: (f) => f.total, num: true },
    ],
  },
  {
    id: "equipo", titulo: "6. Sugerir equipo",
    descripcion: "Compañeros de una materia que aportan habilidades que el estudiante no tiene.",
    campos: [
      { tipo: "estudiante", nombre: "correo", etiqueta: "Estudiante" },
      { tipo: "materia", nombre: "codigo", etiqueta: "Materia" },
      { tipo: "limite" },
    ],
    ruta: "/consultas/equipo",
    columnas: [
      { titulo: "Nombre", valor: (f) => f.nombre },
      { titulo: "Habilidades que aporta", valor: (f) => etiquetas(f.habilidades_que_aporta) },
      { titulo: "Puntaje", valor: (f) => f.puntaje, num: true },
    ],
  },
  {
    id: "conectados", titulo: "7. Estudiantes más conectados",
    descripcion: "Ranking por número de amistades (grado del nodo).",
    campos: [{ tipo: "limite" }],
    ruta: "/consultas/mas-conectados",
    columnas: [
      { titulo: "Nombre", valor: (f) => f.nombre },
      { titulo: "Carrera", valor: (f) => f.carrera },
      { titulo: "Amigos", valor: (f) => f.amigos, num: true },
    ],
  },
  {
    id: "populares", titulo: "8. Habilidades populares",
    descripcion: "Habilidades más frecuentes y su nivel promedio.",
    campos: [{ tipo: "limite" }],
    ruta: "/consultas/habilidades-populares",
    columnas: [
      { titulo: "Habilidad", valor: (f) => etiquetas([f.habilidad]) },
      { titulo: "Estudiantes", valor: (f) => f.estudiantes, num: true },
      { titulo: "Nivel promedio", valor: (f) => f.nivel_promedio, num: true },
    ],
  },
];

/** Crea el control (siempre un <select>) para un campo de la consulta. */
function crearCampo(idConsulta, campo) {
  const nombre = campo.nombre || campo.tipo;
  const id = `q-${idConsulta}-${nombre}`;
  let select;
  let etiqueta = campo.etiqueta;
  if (campo.tipo === "estudiante") {
    select = el("select", { id, name: nombre, class: "sel-estudiante", required: true });
  } else if (campo.tipo === "materia") {
    select = el("select", { id, name: nombre, class: "sel-materia", required: true });
  } else if (campo.tipo === "grados") {
    etiqueta = "Grados";
    select = el("select", { id, name: "grados" }, [1, 2, 3, 4].map((g) => el("option", { value: g }, `${g}`)));
    select.value = "2";
  } else {
    etiqueta = "Máximo de resultados";
    select = el("select", { id, name: "limite" }, LIMITES.map((n) => el("option", { value: n }, `${n}`)));
    select.value = "5";
  }
  return el("div", { class: "campo" }, el("label", { for: id }, etiqueta), select);
}

function crearPanel(def) {
  const resultado = el("div", { class: "zona-resultados", "aria-live": "polite" },
    el("p", { class: "vacio" }, "Elige los datos y pulsa «Consultar»."));
  const form = el("form", { "aria-describedby": `desc-${def.id}`, novalidate: true },
    el("div", { class: "fila-form" }, def.campos.map((c) => crearCampo(def.id, c))),
    el("div", { class: "acciones" }, el("button", { type: "submit", class: "btn" }, "Consultar")));

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const query = Object.fromEntries(new FormData(form));
    const faltan = def.campos.filter((c) => c.nombre && !query[c.nombre]);
    if (faltan.length) {
      reemplazar(resultado, errorCarga(`Elige: ${faltan.map((c) => c.etiqueta.toLowerCase()).join(", ")}.`));
      return;
    }
    reemplazar(resultado, cargando("Consultando el grafo…"));
    const boton = evento.submitter;
    boton.disabled = true;
    boton.setAttribute("aria-busy", "true");
    try {
      const datos = await api("GET", def.ruta, { query });
      const filas = def.filas ? def.filas(datos) : datos;
      reemplazar(resultado,
        def.resumen ? el("p", { class: "resultado-camino" }, def.resumen(datos)) : null,
        tabla(def.columnas, filas, "Sin resultados para esta consulta."));
    } catch (error) {
      reemplazar(resultado, errorCarga(error.message));
      avisarError(error);
    } finally {
      boton.disabled = false;
      boton.removeAttribute("aria-busy");
    }
  });

  return el("article", { class: "tarjeta", "aria-labelledby": `tit-${def.id}` },
    el("h2", { id: `tit-${def.id}` }, def.titulo),
    el("p", { class: "descripcion", id: `desc-${def.id}` }, def.descripcion),
    form, resultado);
}

export function iniciarConsultas() {
  // Los <select> se llenan con refrescarCatalogos() (clases sel-estudiante / sel-materia).
  document.getElementById("paneles-consultas").replaceChildren(...CONSULTAS.map(crearPanel));
}
