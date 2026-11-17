// Sección 1: Estudiantes (tabla con búsqueda, crear/editar, eliminar, perfil).
import { api } from "./api.js";
import { estado, refrescarCatalogos } from "./estado.js";
import {
  avisarError, cargando, conBoton, confirmar, el, errorCarga, etiquetas, nivel, reemplazar, tabla,
} from "./ui.js";

const $ = (id) => document.getElementById(id);
let correoEnEdicion = null; // null = modo "crear"
let textoBuscado = "";

/** Pinta la tabla de estudiantes (todos o los que coinciden con la búsqueda). */
export async function cargarTabla() {
  const zona = $("tabla-estudiantes");
  reemplazar(zona, cargando("Cargando estudiantes…"));
  try {
    const lista = textoBuscado
      ? await api("GET", "/estudiantes", { query: { q: textoBuscado } })
      : estado.estudiantes;
    $("contador-estudiantes").textContent = `${estado.estudiantes.length} en total`;
    reemplazar(zona, tabla(
      [
        { titulo: "Nombre", valor: (e) => e.nombre },
        { titulo: "Correo", valor: (e) => e.correo },
        { titulo: "Carrera", valor: (e) => e.carrera },
        { titulo: "Sem.", valor: (e) => e.semestre, num: true },
        { titulo: "Acciones", valor: botonesFila },
      ],
      lista,
      textoBuscado ? `Ningún estudiante coincide con «${textoBuscado}».` : "Todavía no hay estudiantes.",
    ));
  } catch (error) {
    reemplazar(zona, errorCarga(error.message));
  }
}

function botonesFila(e) {
  return el(
    "div", { class: "acciones" },
    el("button", { type: "button", class: "btn btn-sec btn-chico", "aria-label": `Ver perfil de ${e.nombre}`, onclick: () => abrirPerfil(e.correo) }, "Perfil"),
    el("button", { type: "button", class: "btn btn-sec btn-chico", "aria-label": `Editar a ${e.nombre}`, onclick: () => editar(e) }, "Editar"),
    el("button", { type: "button", class: "btn btn-peligro btn-chico", "aria-label": `Eliminar a ${e.nombre}`, onclick: (ev) => eliminar(e, ev.currentTarget) }, "Eliminar"),
  );
}

// --- formulario crear / editar -----------------------------------------
function modoCrear() {
  correoEnEdicion = null;
  $("form-estudiante").reset();
  $("est-correo").disabled = false;
  $("titulo-form-estudiante").textContent = "Nuevo estudiante";
  $("btn-guardar-estudiante").textContent = "Crear estudiante";
  $("btn-cancelar-edicion").hidden = true;
  $("error-estudiante").textContent = "";
  marcarInvalidos([]);
}

function editar(e) {
  correoEnEdicion = e.correo;
  $("est-correo").value = e.correo;
  $("est-correo").disabled = true;
  $("est-nombre").value = e.nombre;
  $("est-carrera").value = e.carrera;
  $("est-semestre").value = e.semestre;
  $("titulo-form-estudiante").textContent = `Editar a ${e.nombre}`;
  $("btn-guardar-estudiante").textContent = "Guardar cambios";
  $("btn-cancelar-edicion").hidden = false;
  $("error-estudiante").textContent = "";
  marcarInvalidos([]);
  $("est-nombre").focus();
}

function marcarInvalidos(ids) {
  for (const id of ["est-correo", "est-nombre", "est-carrera", "est-semestre"]) {
    $(id).setAttribute("aria-invalid", ids.includes(id) ? "true" : "false");
  }
}

/** Validación básica en el navegador; la validación real la hace el servicio. */
function validarFormulario(datos) {
  const errores = [];
  const invalidos = [];
  if (!correoEnEdicion && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(datos.correo)) {
    errores.push("Escribe un correo válido (ej. nombre@dominio.com).");
    invalidos.push("est-correo");
  }
  if (!datos.nombre) { errores.push("El nombre es obligatorio."); invalidos.push("est-nombre"); }
  if (!datos.carrera) { errores.push("La carrera es obligatoria."); invalidos.push("est-carrera"); }
  const sem = Number(datos.semestre);
  if (!Number.isInteger(sem) || sem < 1 || sem > 12) {
    errores.push("El semestre debe ser un entero entre 1 y 12.");
    invalidos.push("est-semestre");
  }
  marcarInvalidos(invalidos);
  $("error-estudiante").textContent = errores.join(" ");
  if (invalidos.length) $(invalidos[0]).focus();
  return errores.length === 0;
}

async function guardar(evento) {
  evento.preventDefault();
  const datos = {
    correo: $("est-correo").value.trim(),
    nombre: $("est-nombre").value.trim(),
    carrera: $("est-carrera").value.trim(),
    semestre: $("est-semestre").value.trim(),
  };
  if (!validarFormulario(datos)) return;

  const boton = $("btn-guardar-estudiante");
  const resultado = await conBoton(boton, () =>
    correoEnEdicion
      ? api("PATCH", "/estudiantes", {
        query: { correo: correoEnEdicion },
        cuerpo: { nombre: datos.nombre, carrera: datos.carrera, semestre: datos.semestre },
      })
      : api("POST", "/estudiantes", { cuerpo: datos }),
  );
  if (resultado) {
    modoCrear();
    await refrescarCatalogos();
  }
}

async function eliminar(e, boton) {
  const ok = await confirmar(
    "Eliminar estudiante",
    `Se eliminará a ${e.nombre} (${e.correo}) junto con todas sus amistades, materias y habilidades. Esta acción no se puede deshacer.`,
  );
  if (!ok) return;
  const resultado = await conBoton(boton, () => api("DELETE", "/estudiantes", { query: { correo: e.correo } }));
  if (resultado) {
    if (correoEnEdicion === e.correo) modoCrear();
    await refrescarCatalogos();
  }
}

// --- perfil ------------------------------------------------------------
export async function abrirPerfil(correo) {
  const dialogo = $("dlg-perfil");
  const cuerpo = $("perfil-cuerpo");
  $("perfil-titulo").textContent = "Perfil";
  reemplazar(cuerpo, cargando("Cargando perfil…"));
  if (!dialogo.open) dialogo.showModal();
  try {
    const p = await api("GET", "/estudiantes/perfil", { query: { correo } });
    const e = p.estudiante;
    $("perfil-titulo").textContent = e.nombre;
    reemplazar(
      cuerpo,
      el("p", { class: "datos-perfil" },
        el("span", {}, e.correo), el("span", {}, e.carrera),
        el("span", {}, `Semestre ${e.semestre}`), e.creado ? el("span", {}, `Alta: ${e.creado}`) : null),
      el("h3", {}, `Amigos (${p.amigos.length})`),
      tabla([
        { titulo: "Nombre", valor: (a) => a.estudiante.nombre },
        { titulo: "Carrera", valor: (a) => a.estudiante.carrera },
        { titulo: "Desde", valor: (a) => a.desde ?? "" },
      ], p.amigos, "Sin amigos registrados."),
      el("h3", {}, `Materias (${p.materias.length})`),
      tabla([
        { titulo: "Código", valor: (m) => m.materia.codigo },
        { titulo: "Materia", valor: (m) => m.materia.nombre },
        { titulo: "Periodo", valor: (m) => m.periodo ?? "" },
      ], p.materias, "No cursa materias."),
      el("h3", {}, `Habilidades (${p.habilidades.length})`),
      tabla([
        { titulo: "Habilidad", valor: (h) => etiquetas([h.habilidad]) },
        { titulo: "Nivel", valor: (h) => nivel(h.nivel) },
      ], p.habilidades, "Sin habilidades registradas."),
    );
  } catch (error) {
    reemplazar(cuerpo, errorCarga(error.message));
    avisarError(error);
  }
}

/** Conecta los eventos de la sección. */
export function iniciarEstudiantes() {
  $("form-estudiante").addEventListener("submit", guardar);
  $("btn-cancelar-edicion").addEventListener("click", modoCrear);
  $("form-busqueda").addEventListener("submit", (ev) => {
    ev.preventDefault();
    textoBuscado = $("busqueda").value.trim();
    cargarTabla();
  });
  $("btn-limpiar-busqueda").addEventListener("click", () => {
    $("busqueda").value = "";
    textoBuscado = "";
    cargarTabla();
  });
  const dialogo = $("dlg-perfil");
  dialogo.querySelector("[data-cerrar]").addEventListener("click", () => dialogo.close());
  // Clic fuera del contenido cierra el diálogo
  dialogo.addEventListener("click", (ev) => { if (ev.target === dialogo) dialogo.close(); });
}
