// Ejecuta server/web/app.js con un DOM, almacenamiento y fetch simulados.
// Uso: node webapp_harness.js <app.js> <index.html> <escenario>
// Escribe en stdout, como JSON, el estado visible de la pagina al terminar.
"use strict";
const fs = require("fs");
const vm = require("vm");

const [rutaApp, rutaHtml, escenario] = process.argv.slice(2);

// Los elementos que el HTML marca como ocultos empiezan ocultos.
const html = fs.readFileSync(rutaHtml, "utf8");
const ocultosIniciales = new Set();
for (const [etiqueta] of html.matchAll(/<[^>]*\bid="[^"]+"[^>]*>/g)) {
  const id = etiqueta.match(/\bid="([^"]+)"/)[1];
  const clase = (etiqueta.match(/\bclass="([^"]*)"/) || [, ""])[1];
  if (clase.split(/\s+/).includes("oculto")) ocultosIniciales.add(`#${id}`);
}

class Elemento {
  constructor(nombre) {
    this.nombre = nombre;
    this.textContent = "";
    this.className = "";
    this.colSpan = 1;
    this.hijos = [];
    this.clases = new Set(ocultosIniciales.has(nombre) ? ["oculto"] : []);
    this.classList = {
      add: clase => this.clases.add(clase),
      remove: clase => this.clases.delete(clase),
      toggle: (clase, forzar) => ((forzar ?? !this.clases.has(clase))
        ? this.clases.add(clase) : this.clases.delete(clase)),
      contains: clase => this.clases.has(clase),
    };
  }
  addEventListener() {}
  reset() {}
  append(...hijos) { this.hijos.push(...hijos); }
  replaceChildren(...hijos) { this.hijos = hijos; }
}

const elementos = new Map();
const document = {
  querySelector: selector => {
    if (!elementos.has(selector)) elementos.set(selector, new Elemento(selector));
    return elementos.get(selector);
  },
  createElement: etiqueta => new Elemento(etiqueta),
};

const almacen = new Map(escenario.startsWith("google_") ? [] : [["token", "token-valido"]]);
const localStorage = {
  getItem: clave => (almacen.has(clave) ? almacen.get(clave) : null),
  setItem: (clave, valor) => almacen.set(clave, String(valor)),
  removeItem: clave => almacen.delete(clave),
};
// Flujos de Google: "propio" es el que se inicio desde este navegador.
const sesion = new Map(["google_propio", "google_entregado"].includes(escenario)
  ? [["google_state", "S1"]] : []);
const sessionStorage = {
  getItem: clave => (sesion.has(clave) ? sesion.get(clave) : null),
  setItem: (clave, valor) => sesion.set(clave, String(valor)),
  removeItem: clave => sesion.delete(clave),
};
const BUSQUEDAS = {
  google_cancelado: "?google_error=cancelado",
  google_ajeno: "?google_state=S1",
  google_propio: "?google_state=S1",
  google_entregado: "?google_state=S1",
};
let consultasGoogle = 0;
let urlLimpia = false;

const JUGADOR_LIBRE = {usuario: null, puntaje: 0, conectado: false, estado: "normal"};
const DATOS = {
  "/usuarios/ana/perfil": {
    usuario: "ana", posicion: 1,
    estadisticas: {partidas_jugadas: 3, victorias: 2, puntaje_total: 40, mejor_puntaje: 20},
  },
  "/ranking": {ranking: [{usuario: "ana", puntaje_total: 40, victorias: 2}], total: 1},
  "/usuarios/ana/historial": {
    usuario: "ana",
    historial: [{fecha: "2026-11-24T23:11:00+00:00", match_id: "abcdef123456", resultado: "victoria",
                 score: 20, elapsed: 59.99999999999764}],
  },
  "/partida/estado": {
    match_id: null, iniciada: false, finalizada: false, en_curso: false, escenario: "Arena",
    condicion: "time", objetivo: 3, ganador: null, eventos_activos: [],
    tiempo: {transcurrido: 0, limite: null, restante: null, prorrogas: 0},
    reactor: {estado: "available", operador: null},
    jugadores: {red: JUGADOR_LIBRE, blue: JUGADOR_LIBRE},
  },
};

function respuesta(estado, cuerpo) {
  return {
    ok: estado >= 200 && estado < 300,
    status: estado,
    json: async () => {
      if (typeof cuerpo === "string") throw new SyntaxError("Unexpected token <");
      return cuerpo;
    },
  };
}

async function fetch(ruta) {
  if (ruta.startsWith("/auth/social/google/status")) {
    consultasGoogle++;
    return respuesta(200, escenario === "google_propio"
      ? {estado: "completado", resultado: {token: "token-google", usuario: "ana"}}
      : {estado: "entregado"});
  }
  if (ruta === "/auth/validate") {
    if (escenario === "validar_sin_red") throw new TypeError("Failed to fetch");
    if (escenario === "validar_401") return respuesta(401, {detail: "Sesión inválida."});
    return respuesta(200, {usuario: "ana"});
  }
  if (ruta === "/partida/estado") return respuesta(200, DATOS[ruta]);
  switch (escenario) {
    case "sin_red": throw new TypeError("Failed to fetch");
    case "token_vencido": return respuesta(401, {detail: "Sesión inválida."});
    case "error_servidor": return respuesta(500, {detail: "Error interno del servidor."});
    case "respuesta_no_json": return respuesta(200, "<html>proxy</html>");
    case "respuesta_incompleta": return respuesta(200, {});
    default: return respuesta(200, DATOS[ruta]);
  }
}

const contexto = vm.createContext({
  document, localStorage, sessionStorage, fetch, URLSearchParams, console,
  location: {search: BUSQUEDAS[escenario] || "", origin: "http://servidor", pathname: "/webapp/", href: ""},
  history: {replaceState() { urlLimpia = true; }},
  setTimeout, clearTimeout,
  setInterval: () => 1,
  clearInterval: () => {},
});
vm.runInContext(fs.readFileSync(rutaApp, "utf8"), contexto, {filename: "app.js"});

setTimeout(() => {
  const elemento = selector => document.querySelector(selector);
  process.stdout.write(JSON.stringify({
    token: localStorage.getItem("token"),
    dashboardVisible: !elemento("#dashboard").clases.has("oculto"),
    loginMensaje: elemento("#loginMensaje").textContent,
    datosMensaje: elemento("#datosMensaje").textContent,
    datosMensajeVisible: !elemento("#datosMensaje").clases.has("oculto"),
    partidas: String(elemento("#partidas").textContent),
    historial: elemento("#historialBody").hijos.map(fila => fila.hijos.map(celda => celda.textContent)),
    consultasGoogle,
    urlLimpia,
    googleStatePendiente: sessionStorage.getItem("google_state"),
  }));
}, 100);
