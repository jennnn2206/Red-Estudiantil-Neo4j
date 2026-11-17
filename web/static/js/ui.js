// Utilidades de interfaz: creación segura de elementos, avisos, tablas,
// estados de carga y confirmaciones.
//
// Seguridad (XSS): los datos del usuario NUNCA se insertan con innerHTML.
// Todo el texto pasa por textContent (vía la función el()).

/**
 * Crea un elemento. Los hijos de tipo texto se agregan como nodos de texto.
 * @param {string} etiqueta
 * @param {object} [atributos] class, dataset, on* (eventos) y atributos normales
 * @param {...(Node|string|number|null)} hijos
 */
export function el(etiqueta, atributos = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos || {})) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (clave === "class") nodo.className = valor;
    else if (clave === "dataset") Object.assign(nodo.dataset, valor);
    else if (clave.startsWith("on") && typeof valor === "function") {
      nodo.addEventListener(clave.slice(2), valor);
    } else if (valor === true) nodo.setAttribute(clave, "");
    else nodo.setAttribute(clave, String(valor));
  }
  for (const hijo of hijos.flat(Infinity)) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
  return nodo;
}

/** Sustituye el contenido de un contenedor. */
export function reemplazar(contenedor, ...hijos) {
  contenedor.replaceChildren(...hijos.flat().filter(Boolean));
}

// ---------------------------------------------------------------------
// Avisos (toasts)
// ---------------------------------------------------------------------
export function avisar(mensaje, tipo = "exito") {
  const zona = document.getElementById("avisos");
  const cerrar = () => aviso.remove();
  const aviso = el(
    "div",
    { class: `aviso ${tipo}`, role: tipo === "error" ? "alert" : "status" },
    el("p", {}, el("strong", {}, tipo === "error" ? "Error" : "Listo"), mensaje),
    el("button", { type: "button", "aria-label": "Cerrar aviso", onclick: cerrar }, "×"),
  );
  zona.append(aviso);
  setTimeout(cerrar, tipo === "error" ? 8000 : 4500);
}

export const avisarError = (error) => avisar(error.message || String(error), "error");

// ---------------------------------------------------------------------
// Estados de carga / vacío / error
// ---------------------------------------------------------------------
export const cargando = (texto = "Cargando…") => el("p", { class: "cargando" }, texto);
export const vacio = (texto = "Sin resultados.") => el("p", { class: "vacio" }, texto);
export const errorCarga = (texto) => el("p", { class: "error-carga", role: "alert" }, texto);

/**
 * Ejecuta una acción asíncrona marcando el botón como ocupado.
 * Muestra el mensaje de éxito o de error de la API como aviso.
 */
export async function conBoton(boton, accion) {
  if (boton) {
    boton.disabled = true;
    boton.setAttribute("aria-busy", "true");
  }
  try {
    const resultado = await accion();
    if (resultado && resultado.mensaje) avisar(resultado.mensaje);
    return resultado;
  } catch (error) {
    avisarError(error);
    return undefined;
  } finally {
    if (boton) {
      boton.disabled = false;
      boton.removeAttribute("aria-busy");
    }
  }
}

// ---------------------------------------------------------------------
// Tablas
// ---------------------------------------------------------------------
/**
 * Construye una tabla a partir de columnas y filas.
 * @param {{titulo: string, valor: (fila) => (Node|string|number), num?: boolean}[]} columnas
 * @param {object[]} filas
 * @param {string} [textoVacio]
 */
export function tabla(columnas, filas, textoVacio = "Sin resultados.") {
  if (!filas || filas.length === 0) return vacio(textoVacio);
  const cabeza = el("thead", {}, el("tr", {}, columnas.map((c) => el("th", { scope: "col" }, c.titulo))));
  const cuerpo = el(
    "tbody",
    {},
    filas.map((fila) =>
      el("tr", {}, columnas.map((c) => el("td", { class: c.num ? "num" : null }, c.valor(fila) ?? ""))),
    ),
  );
  const contenedor = el("div", {}, el("div", { class: "tabla-scroll" }, el("table", {}, cabeza, cuerpo)));
  contenedor.append(el("p", { class: "pie-tabla" }, `${filas.length} resultado(s)`));
  return contenedor;
}

/** Lista de etiquetas (por ejemplo, materias o habilidades). */
export const etiquetas = (textos) => el("span", {}, (textos || []).map((t) => el("span", { class: "etiqueta" }, t)));

/** Nivel 1-5 como puntos, con texto accesible. */
export function nivel(n) {
  const valor = Number(n) || 0;
  return el(
    "span",
    { class: "nivel", "aria-label": `nivel ${valor} de 5`, title: `nivel ${valor} de 5` },
    "●".repeat(valor) + "○".repeat(Math.max(0, 5 - valor)),
  );
}

// ---------------------------------------------------------------------
// Confirmación con <dialog>
// ---------------------------------------------------------------------
export function confirmar(titulo, texto, textoSi = "Sí, eliminar") {
  const dialogo = document.getElementById("dlg-confirmar");
  document.getElementById("confirmar-titulo").textContent = titulo;
  document.getElementById("confirmar-texto").textContent = texto;
  const si = document.getElementById("confirmar-si");
  const no = document.getElementById("confirmar-no");
  si.textContent = textoSi;
  return new Promise((resolver) => {
    const terminar = (valor) => {
      si.removeEventListener("click", alSi);
      no.removeEventListener("click", alNo);
      dialogo.removeEventListener("close", alCerrar);
      if (dialogo.open) dialogo.close();
      resolver(valor);
    };
    const alSi = () => terminar(true);
    const alNo = () => terminar(false);
    const alCerrar = () => terminar(false); // tecla Escape
    si.addEventListener("click", alSi);
    no.addEventListener("click", alNo);
    dialogo.addEventListener("close", alCerrar);
    dialogo.showModal();
    no.focus();
  });
}

// ---------------------------------------------------------------------
// Listas desplegables
// ---------------------------------------------------------------------
/**
 * Llena un <select> conservando la opción elegida si sigue existiendo.
 * @param {HTMLSelectElement} select
 * @param {{valor: string, texto: string}[]} opciones
 * @param {string} [textoInicial] opción vacía inicial (p. ej. "Elige…")
 */
export function llenarSelect(select, opciones, textoInicial = "Elige…") {
  const anterior = select.value;
  const nodos = [el("option", { value: "" }, textoInicial)];
  for (const o of opciones) nodos.push(el("option", { value: o.valor }, o.texto));
  select.replaceChildren(...nodos);
  if (opciones.some((o) => o.valor === anterior)) select.value = anterior;
}
