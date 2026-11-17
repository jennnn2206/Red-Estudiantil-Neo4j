// Punto de entrada del frontend: navegación por pestañas y arranque.
import { api } from "./api.js";
import { iniciarConsultas } from "./consultas.js";
import { alCambiarCatalogos, estado, refrescarCatalogos } from "./estado.js";
import { cargarTabla, iniciarEstudiantes } from "./estudiantes.js";
import { alMostrarRed, iniciarRed } from "./red.js";
import { iniciarRelaciones } from "./relaciones.js";
import { avisarError } from "./ui.js";

const pestanas = [...document.querySelectorAll('[role="tab"]')];
let seccionActual = "estudiantes";

/** Muestra una sección y oculta las demás (patrón de pestañas accesible). */
function mostrarSeccion(nombre, enfocar = false) {
  seccionActual = nombre;
  for (const tab of pestanas) {
    const activa = tab.id === `tab-${nombre}`;
    tab.setAttribute("aria-selected", String(activa));
    tab.tabIndex = activa ? 0 : -1;
    document.getElementById(tab.getAttribute("aria-controls")).hidden = !activa;
    if (activa && enfocar) tab.focus();
  }
  if (location.hash !== `#${nombre}`) history.replaceState(null, "", `#${nombre}`);
  if (nombre === "red") alMostrarRed();
}

function iniciarPestanas() {
  pestanas.forEach((tab, i) => {
    tab.addEventListener("click", () => mostrarSeccion(tab.id.replace("tab-", "")));
    // Flechas izquierda/derecha para moverse entre pestañas
    tab.addEventListener("keydown", (ev) => {
      const paso = ev.key === "ArrowRight" ? 1 : ev.key === "ArrowLeft" ? -1 : 0;
      if (!paso) return;
      ev.preventDefault();
      const siguiente = pestanas[(i + paso + pestanas.length) % pestanas.length];
      mostrarSeccion(siguiente.id.replace("tab-", ""), true);
    });
  });
  const inicial = location.hash.slice(1);
  mostrarSeccion(pestanas.some((t) => t.id === `tab-${inicial}`) ? inicial : "estudiantes");
}

async function comprobarConexion() {
  const etiqueta = document.getElementById("estado-conexion");
  try {
    const salud = await api("GET", "/salud");
    etiqueta.textContent = `Conectado a AuraDB · ${salud.estudiantes} estudiantes`;
    etiqueta.className = "estado-conexion ok";
  } catch (error) {
    etiqueta.textContent = "Sin conexión con la base";
    etiqueta.className = "estado-conexion mal";
    avisarError(error);
  }
}

async function arrancar() {
  iniciarEstudiantes();
  iniciarRed();
  iniciarRelaciones();
  iniciarConsultas();
  iniciarPestanas();

  alCambiarCatalogos(() => {
    cargarTabla();
    const etiqueta = document.getElementById("estado-conexion");
    if (etiqueta.classList.contains("ok")) {
      etiqueta.textContent = `Conectado a AuraDB · ${estado.estudiantes.length} estudiantes`;
    }
    if (seccionActual === "red") alMostrarRed();
  });

  await comprobarConexion();
  try {
    await refrescarCatalogos();
  } catch (error) {
    avisarError(error);
    cargarTabla();
  }
}

arrancar();
