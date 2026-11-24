const loginPanel = document.querySelector("#loginPanel");
const dashboard = document.querySelector("#dashboard");
const loginForm = document.querySelector("#loginForm");
const cerrarSesion = document.querySelector("#cerrarSesion");
const loginMensaje = document.querySelector("#loginMensaje");

let usuarioActual = null;

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

function mostrarDashboard(nombre) {
  usuarioActual = nombre;
  loginPanel.classList.add("oculto");
  dashboard.classList.remove("oculto");
  cerrarSesion.classList.remove("oculto");
  document.querySelector("#nombreJugador").textContent = nombre;
  cargarDatos();
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
  historialBody.innerHTML = historial.historial.length
    ? historial.historial.map(partida => `
      <tr>
        <td>${fechaLegible(partida.fecha)}</td>
        <td>${partida.match_id.slice(0, 8)}</td>
        <td class="${partida.resultado}">${partida.resultado}</td>
        <td>${partida.score}</td>
        <td>${duracion(partida.elapsed)}</td>
      </tr>`).join("")
    : `<tr><td colspan="5">Todavia no hay partidas.</td></tr>`;

  const rankingBody = document.querySelector("#rankingBody");
  rankingBody.innerHTML = ranking.ranking.length
    ? ranking.ranking.map((fila, indice) => `
      <tr>
        <td>${indice + 1}</td>
        <td>${fila.usuario}</td>
        <td>${fila.puntaje_total}</td>
        <td>${fila.victorias}</td>
      </tr>`).join("")
    : `<tr><td colspan="4">Sin datos.</td></tr>`;
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
