// Sección 3: amistades, inscripciones a materias y habilidades.
import { api } from "./api.js";
import { alCambiarCatalogos, nombreDe, refrescarCatalogos } from "./estado.js";
import {
  avisarError, cargando, conBoton, confirmar, el, errorCarga, etiquetas, nivel, reemplazar, tabla, vacio,
} from "./ui.js";

const $ = (id) => document.getElementById(id);

/** Muestra un error de validación local como aviso y devuelve false. */
function exigir(condicion, mensaje) {
  if (!condicion) avisarError(new Error(mensaje));
  return condicion;
}

// --- amistades ---------------------------------------------------------
async function pintarAmigos() {
  const correo = $("am-a").value;
  const zona = $("lista-amigos");
  $("am-nombre").textContent = correo ? nombreDe(correo) : "…";
  if (!correo) return reemplazar(zona, vacio("Elige un estudiante para ver sus amigos."));
  reemplazar(zona, cargando());
  try {
    const amigos = await api("GET", "/amistades", { query: { correo } });
    reemplazar(zona, tabla([
      { titulo: "Amigo", valor: (a) => a.estudiante.nombre },
      { titulo: "Desde", valor: (a) => a.desde ?? "" },
      {
        titulo: "", valor: (a) => el("button", {
          type: "button", class: "btn btn-peligro btn-chico", "aria-label": `Quitar amistad con ${a.estudiante.nombre}`,
          onclick: (ev) => quitarAmistad(correo, a.estudiante.correo, ev.currentTarget),
        }, "Quitar"),
      },
    ], amigos, "Todavía no tiene amigos registrados."));
  } catch (error) {
    reemplazar(zona, errorCarga(error.message));
  }
}

async function agregarAmistad(evento) {
  evento.preventDefault();
  const a = $("am-a").value;
  const b = $("am-b").value;
  if (!exigir(a && b, "Elige a los dos estudiantes.")) return;
  if (!exigir(a !== b, "Un estudiante no puede ser amigo de sí mismo.")) return;
  const ok = await conBoton(evento.submitter, () => api("POST", "/amistades", { cuerpo: { correo_a: a, correo_b: b } }));
  if (ok) await refrescarCatalogos();
}

async function quitarAmistad(a, b, boton) {
  if (!exigir(a && b, "Elige a los dos estudiantes.")) return;
  const si = await confirmar("Quitar amistad", `${nombreDe(a)} y ${nombreDe(b)} dejarán de ser amigos.`, "Sí, quitar");
  if (!si) return;
  const ok = await conBoton(boton, () => api("DELETE", "/amistades", { query: { correo_a: a, correo_b: b } }));
  if (ok) await refrescarCatalogos();
}

// --- materias ----------------------------------------------------------
/** Periodos del año anterior al siguiente; elige por defecto el actual. */
function llenarPeriodos() {
  const hoy = new Date();
  const año = hoy.getFullYear();
  const mes = hoy.getMonth() + 1;
  const actual = `${año}-${mes <= 5 ? "Primavera" : mes <= 7 ? "Verano" : "Otoño"}`;
  const opciones = [];
  for (let a = año - 1; a <= año + 1; a++) {
    for (const t of ["Primavera", "Verano", "Otoño"]) opciones.push(el("option", { value: `${a}-${t}` }, `${a}-${t}`));
  }
  $("ins-periodo").replaceChildren(...opciones);
  $("ins-periodo").value = actual;
}

async function pintarMateriasDeEstudiante() {
  const correo = $("ins-estudiante").value;
  const zona = $("lista-materias-est");
  if (!correo) return reemplazar(zona, vacio("Elige un estudiante para ver sus materias."));
  reemplazar(zona, cargando());
  try {
    const p = await api("GET", "/estudiantes/perfil", { query: { correo } });
    reemplazar(zona, tabla([
      { titulo: "Código", valor: (m) => m.materia.codigo },
      { titulo: "Materia", valor: (m) => m.materia.nombre },
      { titulo: "Periodo", valor: (m) => m.periodo ?? "" },
      {
        titulo: "", valor: (m) => el("button", {
          type: "button", class: "btn btn-peligro btn-chico", "aria-label": `Dar de baja ${m.materia.nombre}`,
          onclick: (ev) => darDeBaja(correo, m.materia.codigo, ev.currentTarget),
        }, "Baja"),
      },
    ], p.materias, "No cursa ninguna materia."));
  } catch (error) {
    reemplazar(zona, errorCarga(error.message));
  }
}

async function inscribir(evento) {
  evento.preventDefault();
  const correo = $("ins-estudiante").value;
  const codigo = $("ins-materia").value;
  const periodo = $("ins-periodo").value;
  if (!exigir(correo && codigo && periodo, "Elige estudiante, materia y periodo.")) return;
  const ok = await conBoton(evento.submitter, () => api("POST", "/inscripciones", { cuerpo: { correo, codigo, periodo } }));
  if (ok) await refrescarCatalogos();
}

async function darDeBaja(correo, codigo, boton) {
  if (!exigir(correo && codigo, "Elige estudiante y materia.")) return;
  const si = await confirmar("Dar de baja", `${nombreDe(correo)} dejará de cursar ${codigo}.`, "Sí, dar de baja");
  if (!si) return;
  const ok = await conBoton(boton, () => api("DELETE", "/inscripciones", { query: { correo, codigo } }));
  if (ok) await refrescarCatalogos();
}

async function crearMateria(evento) {
  evento.preventDefault();
  const codigo = $("mat-codigo").value.trim().toUpperCase();
  const nombre = $("mat-nombre").value.trim();
  if (!exigir(/^[A-Z]{2,5}-\d{2,4}$/.test(codigo), "El código debe tener letras, guion y números (ej. BDA-401).")) return;
  if (!exigir(nombre, "El nombre de la materia es obligatorio.")) return;
  const ok = await conBoton(evento.submitter, () => api("POST", "/materias", { cuerpo: { codigo, nombre } }));
  if (ok) {
    $("form-materia").reset();
    await refrescarCatalogos();
    $("ins-materia").value = ok.materia.codigo;
  }
}

// --- habilidades -------------------------------------------------------
async function pintarHabilidades() {
  const correo = $("hab-estudiante").value;
  const zona = $("lista-habilidades-est");
  if (!correo) return reemplazar(zona, vacio("Elige un estudiante para ver sus habilidades."));
  reemplazar(zona, cargando());
  try {
    const p = await api("GET", "/estudiantes/perfil", { query: { correo } });
    reemplazar(zona, tabla([
      { titulo: "Habilidad", valor: (h) => etiquetas([h.habilidad]) },
      { titulo: "Nivel", valor: (h) => nivel(h.nivel) },
      {
        titulo: "", valor: (h) => el("div", { class: "acciones" },
          el("button", {
            type: "button", class: "btn btn-sec btn-chico", "aria-label": `Editar nivel de ${h.habilidad}`,
            onclick: () => { $("hab-nombre").value = h.habilidad; $("hab-nivel").value = String(h.nivel); $("hab-nivel").focus(); },
          }, "Editar"),
          el("button", {
            type: "button", class: "btn btn-peligro btn-chico", "aria-label": `Quitar ${h.habilidad}`,
            onclick: (ev) => quitarHabilidad(correo, h.habilidad, ev.currentTarget),
          }, "Quitar")),
      },
    ], p.habilidades, "Sin habilidades registradas."));
  } catch (error) {
    reemplazar(zona, errorCarga(error.message));
  }
}

async function guardarHabilidad(evento) {
  evento.preventDefault();
  const correo = $("hab-estudiante").value;
  const habilidad = $("hab-nombre").value.trim();
  const valorNivel = $("hab-nivel").value;
  if (!exigir(correo, "Elige un estudiante.")) return;
  if (!exigir(habilidad && habilidad.length <= 50, "Escribe el nombre de la habilidad (máximo 50 caracteres).")) return;
  const ok = await conBoton(evento.submitter, () =>
    api("POST", "/habilidades", { cuerpo: { correo, habilidad, nivel: valorNivel } }));
  if (ok) {
    $("hab-nombre").value = "";
    await refrescarCatalogos();
  }
}

async function quitarHabilidad(correo, habilidad, boton) {
  const si = await confirmar("Quitar habilidad", `Se quitará «${habilidad}» a ${nombreDe(correo)}.`, "Sí, quitar");
  if (!si) return;
  const ok = await conBoton(boton, () => api("DELETE", "/habilidades", { query: { correo, habilidad } }));
  if (ok) await refrescarCatalogos();
}

/** Repinta las listas de la sección (tras cualquier cambio en los datos). */
export function refrescarRelaciones() {
  pintarAmigos();
  pintarMateriasDeEstudiante();
  pintarHabilidades();
}

export function iniciarRelaciones() {
  llenarPeriodos();
  $("form-amistad").addEventListener("submit", agregarAmistad);
  $("btn-quitar-amistad").addEventListener("click", (ev) => quitarAmistad($("am-a").value, $("am-b").value, ev.currentTarget));
  $("am-a").addEventListener("change", pintarAmigos);

  $("form-inscripcion").addEventListener("submit", inscribir);
  $("btn-baja").addEventListener("click", (ev) => darDeBaja($("ins-estudiante").value, $("ins-materia").value, ev.currentTarget));
  $("ins-estudiante").addEventListener("change", pintarMateriasDeEstudiante);
  $("form-materia").addEventListener("submit", crearMateria);

  $("form-habilidad").addEventListener("submit", guardarHabilidad);
  $("hab-estudiante").addEventListener("change", pintarHabilidades);

  alCambiarCatalogos(refrescarRelaciones);
}
