const loginPanel = document.querySelector("#loginPanel");
const dashboard = document.querySelector("#dashboard");
const loginForm = document.querySelector("#loginForm");
const cerrarSesion = document.querySelector("#cerrarSesion");
const loginMensaje = document.querySelector("#loginMensaje");

let usuarioActual = null;
let sondeoPartida = null;

const ESTADOS_JUGADOR = {normal: "Normal", stunned: "Aturdido", frozen: "Atrapado"};
const ESTADOS_REACTOR = {available: "Disponible", in_use: "En uso", overload: "Sobrecargado"};
const NOMBRES_EVENTO = {
  energy: "Energia extra", extra_guardians: "+5 guardianes", overload: "Sobrecarga",
  speed_boost: "Impulso", guardian_truce: "Tregua",
};

async function solicitar(ruta, opciones = {}) {
  const cabeceras = {...(opciones.headers || {})};
  const token = localStorage.getItem("token");
  if (token) cabeceras.Authorization = `Bearer ${token}`;
  const respuesta = await fetch(ruta, {...opciones, headers: cabeceras});
  let datos = {};
  try { datos = await respuesta.json(); } catch (_) {}
  if (!respuesta.ok) throw new Error(datos.detail || "Solicitud rechazada");
  return datos;
}

function duracion(segundos) {
  const valor = Math.max(0, Math.round(Number(segundos) || 0));
  const minutos = Math.floor(valor / 60);
  const resto = valor % 60;
  return `${minutos}:${String(resto).padStart(2, "0")}`;
}

function fechaLegible(iso) {
  const fecha = iso ? new Date(iso) : null;
  if (!fecha || Number.isNaN(fecha.getTime())) return "Sin fecha";
  return fecha.toLocaleString("es-CR", {dateStyle: "short", timeStyle: "short"});
}

// Los datos del servidor se insertan como texto, nunca como HTML.
function celda(valor, clase = "") {
  const td = document.createElement("td");
  td.textContent = String(valor);
  if (clase) td.className = clase;
  return td;
}

function llenarTabla(cuerpo, filas, columnas, textoVacio) {
  if (!filas.length) {
    const vacia = celda(textoVacio);
    vacia.colSpan = columnas;
    filas = [[vacia]];
  }
  cuerpo.replaceChildren(...filas.map(celdas => {
    const fila = document.createElement("tr");
    fila.append(...celdas);
    return fila;
  }));
}

function mostrarDashboard(nombre) {
  usuarioActual = nombre;
  loginPanel.classList.add("oculto");
  dashboard.classList.remove("oculto");
  cerrarSesion.classList.remove("oculto");
  document.querySelector("#nombreJugador").textContent = nombre;
  cargarDatos();
  iniciarSondeoPartida();
}

function textoEstadoPartida(estado) {
  if (estado.finalizada) {
    const ganador = estado.ganador ? (estado.jugadores[estado.ganador].usuario || estado.ganador) : "-";
    return `Finalizada: gano ${ganador}`;
  }
  if (estado.en_curso) return estado.tiempo.prorrogas ? `Prorroga ${estado.tiempo.prorrogas}` : "En curso";
  const conectados = Object.values(estado.jugadores).filter(jugador => jugador.conectado).length;
  return conectados ? `En espera (${conectados}/2)` : "Sin partida";
}

function mostrarPartida(estado) {
  document.querySelector("#partidaEstado").textContent = textoEstadoPartida(estado);
  const tiempo = estado.tiempo.restante !== null
    ? `Quedan ${duracion(Math.ceil(estado.tiempo.restante))}`
    : `Objetivo ${estado.objetivo} puntos, ${duracion(estado.tiempo.transcurrido)} jugados`;
  document.querySelector("#partidaDetalle").textContent = `${estado.escenario} - ${tiempo}`;
  for (const [puesto, prefijo] of [["red", "Rojo"], ["blue", "Azul"]]) {
    const jugador = estado.jugadores[puesto];
    document.querySelector(`#partida${prefijo}Nombre`).textContent = jugador.usuario || "Libre";
    document.querySelector(`#partida${prefijo}Puntaje`).textContent = jugador.puntaje;
    document.querySelector(`#partida${prefijo}Estado`).textContent = jugador.conectado
      ? (ESTADOS_JUGADOR[jugador.estado] || jugador.estado)
      : "Desconectado";
  }
  const operador = estado.reactor.operador ? estado.jugadores[estado.reactor.operador].usuario : null;
  document.querySelector("#partidaReactor").textContent =
    `Reactor: ${ESTADOS_REACTOR[estado.reactor.estado] || estado.reactor.estado}${operador ? ` (${operador})` : ""}`;
  document.querySelector("#partidaEventos").textContent = estado.eventos_activos.length
    ? `Eventos: ${estado.eventos_activos.map(e => `${NOMBRES_EVENTO[e.tipo] || e.tipo} (${Math.ceil(e.restante)} s)`).join(", ")}`
    : "";
}

async function actualizarPartida() {
  try {
    mostrarPartida(await solicitar("/partida/estado"));
  } catch (_) {
    document.querySelector("#partidaEstado").textContent = "Sin conexion";
  }
}

function iniciarSondeoPartida() {
  detenerSondeoPartida();
  actualizarPartida();
  sondeoPartida = setInterval(actualizarPartida, 1500);
}

function detenerSondeoPartida() {
  if (sondeoPartida) clearInterval(sondeoPartida);
  sondeoPartida = null;
}

async function cargarDatos() {
  const usuarioCodificado = encodeURIComponent(usuarioActual);

  const [perfil, ranking, historial] = await Promise.all([
    solicitar(`/usuarios/${usuarioCodificado}/perfil`),
    solicitar("/ranking"),
    solicitar(`/usuarios/${usuarioCodificado}/historial`),
  ]);

  const estadisticas = perfil.estadisticas;
  document.querySelector("#posicionJugador").textContent = perfil.posicion ? `Posicion #${perfil.posicion}` : "Sin ranking";
  document.querySelector("#partidas").textContent = estadisticas.partidas_jugadas;
  document.querySelector("#victorias").textContent = estadisticas.victorias;
  document.querySelector("#puntaje").textContent = estadisticas.puntaje_total;
  document.querySelector("#mejor").textContent = estadisticas.mejor_puntaje;

  const historialBody = document.querySelector("#historialBody");
  llenarTabla(historialBody, historial.historial.map(partida => [
    celda(fechaLegible(partida.fecha)),
    celda(String(partida.match_id).slice(0, 8)),
    celda(partida.resultado, partida.resultado === "victoria" ? "victoria" : "derrota"),
    celda(partida.score),
    celda(duracion(partida.elapsed)),
  ]), 5, "Todavia no hay partidas.");

  const rankingBody = document.querySelector("#rankingBody");
  llenarTabla(rankingBody, ranking.ranking.map((fila, indice) => [
    celda(indice + 1),
    celda(fila.usuario),
    celda(fila.puntaje_total),
    celda(fila.victorias),
  ]), 4, "Sin datos.");
}

loginForm.addEventListener("submit", async evento => {
  evento.preventDefault();
  loginMensaje.textContent = "";
  const datos = new FormData(loginForm);
  try {
    const respuesta = await solicitar("/auth/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        identificador: datos.get("identificador"),
        clave: datos.get("clave"),
      }),
    });

    if (respuesta.no_verificado) {
      loginMensaje.textContent = "El correo todavia no esta verificado.";
      return;
    }

    localStorage.setItem("token", respuesta.token);
    mostrarDashboard(respuesta.usuario);
  } catch (error) {
    loginMensaje.textContent = error.message;
  }
});

cerrarSesion.addEventListener("click", () => {
  localStorage.removeItem("token");
  detenerSondeoPartida();
  usuarioActual = null;
  dashboard.classList.add("oculto");
  cerrarSesion.classList.add("oculto");
  loginPanel.classList.remove("oculto");
  loginForm.reset();
});

document.querySelector("#googleLogin").addEventListener("click", async () => {
  loginMensaje.textContent = "";
  try {
    const inicio = await solicitar("/auth/social/google/start", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({redirect_uri: `${location.origin}/auth/social/google/callback`}),
    });
    location.href = inicio.authorization_url;
  } catch (error) {
    loginMensaje.textContent = error.message;
  }
});

async function revisarLoginGoogle() {
  const parametros = new URLSearchParams(location.search);
  const state = parametros.get("google_state");
  if (!state) return;

  for (let intento = 0; intento < 40; intento++) {
    try {
      const estado = await solicitar(`/auth/social/google/status?state=${encodeURIComponent(state)}`);
      if (estado.estado === "completado") {
        const resultado = estado.resultado;
        localStorage.setItem("token", resultado.token);
        history.replaceState({}, "", location.pathname);
        mostrarDashboard(resultado.usuario);
        return;
      }
      if (estado.estado === "expirado") break;
    } catch (_) {}
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}

// La sesión solo se restaura si el servidor confirma el token guardado.
async function restaurarSesion() {
  localStorage.removeItem("usuario");
  const token = localStorage.getItem("token");
  if (!token) return;
  try {
    const sesion = await solicitar("/auth/validate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({token}),
    });
    mostrarDashboard(sesion.usuario);
  } catch (_) {
    localStorage.removeItem("token");
    loginMensaje.textContent = "Tu sesion expiro. Inicia sesion de nuevo.";
  }
}

restaurarSesion();
revisarLoginGoogle();
