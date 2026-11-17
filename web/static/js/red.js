// Sección 2: visualización del grafo con vis-network (incluida localmente en
// /static/vendor). Las etiquetas se dibujan en un <canvas>, así que no hay
// riesgo de inyección de HTML; el panel de detalle usa textContent.
import { api } from "./api.js";
import { abrirPerfil } from "./estudiantes.js";
import { alCambiarCatalogos, estado } from "./estado.js";
import { avisarError, conBoton, el, reemplazar, vacio } from "./ui.js";

const $ = (id) => document.getElementById(id);

// Colores por tipo de nodo (alineados con la leyenda de la página).
const ESTILOS = {
  Estudiante: { shape: "dot", color: { background: "#fb923c", border: "#c2410c", highlight: { background: "#fdba74", border: "#7c2d12" }, hover: { background: "#fdba74", border: "#9a3412" } } },
  Materia: { shape: "box", color: { background: "#ccfbf1", border: "#0f766e", highlight: { background: "#99f6e4", border: "#115e59" }, hover: { background: "#99f6e4", border: "#115e59" } }, font: { color: "#134e4a" } },
  Habilidad: { shape: "diamond", size: 10, color: { background: "#f3e8ff", border: "#7e22ce", highlight: { background: "#e9d5ff", border: "#581c87" }, hover: { background: "#e9d5ff", border: "#581c87" } }, font: { color: "#581c87", size: 12 } },
};
const ARISTAS = {
  AMIGO_DE: { color: { color: "#c9b3a2", highlight: "#9a3412", hover: "#9a3412" }, width: 2 },
  CURSA: { color: { color: "#5eead4", highlight: "#0f766e", hover: "#0f766e" }, width: 1, dashes: [6, 4], arrows: { to: { enabled: true, scaleFactor: 0.5 } } },
  DOMINA: { color: { color: "#d8b4fe", highlight: "#7e22ce", hover: "#7e22ce" }, width: 1, dashes: [2, 4], arrows: { to: { enabled: true, scaleFactor: 0.5 } } },
};
const ATENUADO = { background: "#f1ebe6", border: "#ddd2c8" };
const CAMINO = "#dc2626";

let red = null;          // instancia de vis.Network
let nodos = null;        // vis.DataSet
let aristas = null;      // vis.DataSet
let originales = { nodos: new Map(), aristas: new Map() };
let caminoActivo = null; // lista de correos resaltados

function idArista(a) {
  return `${a.tipo}|${a.origen}|${a.destino}`;
}

/** Convierte la respuesta de /api/grafo al formato de vis-network. */
function convertir(grafo) {
  const listaNodos = grafo.nodos.map((n) => {
    const base = ESTILOS[n.tipo] || {};
    const nodo = { id: n.id, label: n.etiqueta, grupoTipo: n.tipo, datos: n.datos, ...structuredClone(base) };
    if (n.tipo === "Estudiante") nodo.size = 12 + 3 * Math.min(n.datos.amigos || 0, 8);
    return nodo;
  });
  const listaAristas = grafo.aristas.map((a) => ({
    id: idArista(a), from: a.origen, to: a.destino, tipo: a.tipo, datos: a.datos,
    ...structuredClone(ARISTAS[a.tipo] || {}),
  }));
  return { listaNodos, listaAristas };
}

let cargaEnCurso = null; // evita dos cargas simultáneas (y dos redes)

/** Pide el grafo a la API y lo dibuja. */
export function cargarGrafo(boton) {
  if (!cargaEnCurso) cargaEnCurso = cargarGrafoAhora(boton).finally(() => { cargaEnCurso = null; });
  return cargaEnCurso;
}

async function cargarGrafoAhora(boton) {
  const query = {
    materias: $("chk-materias").checked ? "true" : "false",
    habilidades: $("chk-habilidades").checked ? "true" : "false",
  };
  const contenedor = $("grafo");
  contenedor.setAttribute("aria-busy", "true");
  await conBoton(boton, async () => {
    const grafo = await api("GET", "/grafo", { query });
    const { listaNodos, listaAristas } = convertir(grafo);
    originales = {
      nodos: new Map(listaNodos.map((n) => [n.id, { color: structuredClone(n.color), font: n.font ? structuredClone(n.font) : undefined }])),
      aristas: new Map(listaAristas.map((a) => [a.id, { color: structuredClone(a.color), width: a.width }])),
    };
    if (!red) crearRed(listaNodos, listaAristas);
    else {
      nodos.clear(); aristas.clear();
      nodos.add(listaNodos); aristas.add(listaAristas);
    }
    estado.grafoDesactualizado = false;
    if (caminoActivo) resaltarCamino(caminoActivo, false);
    if (listaNodos.length === 0) $("resultado-camino").textContent = "Sin estudiantes que mostrar.";
  });
  contenedor.removeAttribute("aria-busy");
}

function crearRed(listaNodos, listaAristas) {
  nodos = new vis.DataSet(listaNodos);
  aristas = new vis.DataSet(listaAristas);
  red = new vis.Network($("grafo"), { nodes: nodos, edges: aristas }, {
    nodes: { font: { face: "system-ui, sans-serif", size: 14, color: "#2b2420", strokeWidth: 3, strokeColor: "#fffdfb" }, borderWidth: 2 },
    edges: { smooth: { type: "continuous" }, selectionWidth: 2 },
    physics: { solver: "forceAtlas2Based", forceAtlas2Based: { gravitationalConstant: -60, springLength: 110 }, stabilization: { iterations: 250 } },
    interaction: { hover: true, tooltipDelay: 200, multiselect: false },
  });
  red.on("click", (params) => {
    if (params.nodes.length) mostrarNodo(nodos.get(params.nodes[0]));
    else if (params.edges.length) mostrarArista(aristas.get(params.edges[0]));
  });
}

// --- panel de detalle --------------------------------------------------
function filaDato(nombre, valor) {
  return [el("dt", {}, nombre), el("dd", {}, valor ?? "—")];
}

function mostrarNodo(n) {
  const panel = $("panel-nodo");
  const d = n.datos || {};
  const titulo = el("h3", {}, `${n.grupoTipo}: ${n.label}`);
  if (n.grupoTipo === "Estudiante") {
    const correo = d.correo;
    reemplazar(panel, titulo,
      el("dl", {}, filaDato("Correo", d.correo), filaDato("Carrera", d.carrera),
        filaDato("Semestre", d.semestre), filaDato("Amigos", d.amigos)),
      el("div", { class: "acciones" },
        el("button", { type: "button", class: "btn btn-sec btn-chico", onclick: () => { $("grafo-origen").value = correo; } }, "Usar como origen"),
        el("button", { type: "button", class: "btn btn-sec btn-chico", onclick: () => { $("grafo-destino").value = correo; } }, "Usar como destino"),
        el("button", { type: "button", class: "btn btn-chico", onclick: () => abrirPerfil(correo) }, "Ver perfil")));
  } else if (n.grupoTipo === "Materia") {
    reemplazar(panel, titulo, el("dl", {}, filaDato("Código", d.codigo), filaDato("Nombre", d.nombre),
      filaDato("Inscritos", aristas.get({ filter: (a) => a.to === n.id }).length)));
  } else {
    reemplazar(panel, titulo, el("dl", {}, filaDato("Habilidad", d.nombre),
      filaDato("Estudiantes", aristas.get({ filter: (a) => a.to === n.id }).length)));
  }
}

function mostrarArista(a) {
  const origen = nodos.get(a.from);
  const destino = nodos.get(a.to);
  const filas = [filaDato("De", origen?.label), filaDato("A", destino?.label)];
  if (a.tipo === "AMIGO_DE") filas.push(filaDato("Desde", a.datos.desde));
  if (a.tipo === "CURSA") filas.push(filaDato("Periodo", a.datos.periodo));
  if (a.tipo === "DOMINA") filas.push(filaDato("Nivel", `${a.datos.nivel} de 5`));
  reemplazar($("panel-nodo"), el("h3", {}, `Relación ${a.tipo}`), el("dl", {}, filas));
}

// --- camino más corto --------------------------------------------------
function restaurarEstilos() {
  if (!nodos) return;
  nodos.update([...originales.nodos].map(([id, o]) => ({ id, color: o.color, font: o.font, borderWidth: 2 })));
  aristas.update([...originales.aristas].map(([id, o]) => ({ id, color: o.color, width: o.width })));
}

/** Resalta en rojo los nodos y aristas del camino; atenúa el resto. */
function resaltarCamino(correos, enfocar = true) {
  restaurarEstilos();
  const ids = correos.map((c) => `e:${c}`);
  const enCamino = new Set(ids);
  const aristasCamino = new Set();
  for (let i = 0; i < ids.length - 1; i++) {
    for (const id of [`AMIGO_DE|${ids[i]}|${ids[i + 1]}`, `AMIGO_DE|${ids[i + 1]}|${ids[i]}`]) {
      if (aristas.get(id)) aristasCamino.add(id);
    }
  }
  nodos.update(nodos.getIds().map((id) => enCamino.has(id)
    ? { id, color: { background: "#fecaca", border: CAMINO, highlight: { background: "#fecaca", border: CAMINO } }, borderWidth: 4 }
    : { id, color: { ...ATENUADO, highlight: ATENUADO }, font: { color: "#a39488" } }));
  aristas.update(aristas.getIds().map((id) => aristasCamino.has(id)
    ? { id, color: { color: CAMINO, highlight: CAMINO }, width: 5 }
    : { id, color: { color: "#efe6de", highlight: "#efe6de" }, width: 1 }));
  if (enfocar) red.fit({ nodes: ids, animation: { duration: 500 } });
}

async function buscarCamino(evento) {
  evento.preventDefault();
  const origen = $("grafo-origen").value;
  const destino = $("grafo-destino").value;
  if (!origen || !destino) {
    avisarError(new Error("Elige un estudiante de origen y uno de destino."));
    return;
  }
  if (origen === destino) {
    avisarError(new Error("Elige dos estudiantes distintos."));
    return;
  }
  const boton = evento.submitter;
  const salida = $("resultado-camino");
  salida.textContent = "Buscando camino…";
  const resultado = await conBoton(boton, () => api("GET", "/consultas/camino", { query: { origen, destino } }));
  if (!resultado) {
    salida.textContent = "";
    return;
  }
  caminoActivo = resultado.correos;
  salida.textContent = `${resultado.camino.join(" → ")} (${resultado.grados} grado(s) de separación)`;
  if (red) resaltarCamino(caminoActivo);
}

function quitarResaltado() {
  caminoActivo = null;
  $("resultado-camino").textContent = "";
  restaurarEstilos();
  if (red) red.fit({ animation: { duration: 400 } });
}

/** Se llama cada vez que se muestra la sección "Red". */
export async function alMostrarRed() {
  if (typeof vis === "undefined") {
    reemplazar($("grafo"), vacio("No se pudo cargar la librería de grafos (vendor/vis-network.min.js)."));
    return;
  }
  if (estado.grafoDesactualizado || !red) await cargarGrafo(null);
  else { red.redraw(); red.fit(); }
}

export function iniciarRed() {
  $("form-camino-grafo").addEventListener("submit", buscarCamino);
  $("btn-quitar-resaltado").addEventListener("click", quitarResaltado);
  $("btn-recargar-grafo").addEventListener("click", (ev) => cargarGrafo(ev.currentTarget));
  $("chk-materias").addEventListener("change", () => cargarGrafo(null));
  $("chk-habilidades").addEventListener("change", () => cargarGrafo(null));
  // Si se elimina un estudiante que estaba en el camino, se quita el resaltado.
  alCambiarCatalogos(() => {
    if (caminoActivo && !caminoActivo.every((c) => estado.estudiantes.some((e) => e.correo === c))) quitarResaltado();
  });
}
