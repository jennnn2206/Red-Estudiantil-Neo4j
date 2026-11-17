// Estado compartido entre secciones: catálogos de estudiantes, materias y
// habilidades que alimentan todas las listas desplegables.
import { api } from "./api.js";
import { el, llenarSelect } from "./ui.js";

export const estado = {
  estudiantes: [],
  materias: [],
  habilidades: [],
  grafoDesactualizado: true, // el grafo se vuelve a pedir al entrar a "Red"
};

const oyentes = new Set();

/** Registra una función que se llama cada vez que cambian los catálogos. */
export function alCambiarCatalogos(funcion) {
  oyentes.add(funcion);
}

/** Nombre legible de un estudiante a partir de su correo. */
export function nombreDe(correo) {
  const e = estado.estudiantes.find((x) => x.correo === correo);
  return e ? e.nombre : correo;
}

/** Vuelve a pedir los catálogos a la API y actualiza todas las listas. */
export async function refrescarCatalogos() {
  const [estudiantes, materias, habilidades] = await Promise.all([
    api("GET", "/estudiantes"),
    api("GET", "/materias"),
    api("GET", "/habilidades"),
  ]);
  estado.estudiantes = estudiantes;
  estado.materias = materias;
  estado.habilidades = habilidades;
  estado.grafoDesactualizado = true;

  const opcionesEst = estudiantes.map((e) => ({ valor: e.correo, texto: `${e.nombre} · ${e.correo}` }));
  document.querySelectorAll("select.sel-estudiante").forEach((s) => llenarSelect(s, opcionesEst, "Elige un estudiante…"));

  const opcionesMat = materias.map((m) => ({ valor: m.codigo, texto: `${m.codigo} · ${m.nombre}` }));
  document.querySelectorAll("select.sel-materia").forEach((s) => llenarSelect(s, opcionesMat, "Elige una materia…"));

  document.getElementById("lista-habilidades").replaceChildren(...habilidades.map((h) => el("option", { value: h })));
  const carreras = [...new Set(estudiantes.map((e) => e.carrera))].sort();
  document.getElementById("lista-carreras").replaceChildren(...carreras.map((c) => el("option", { value: c })));

  oyentes.forEach((f) => f());
}
