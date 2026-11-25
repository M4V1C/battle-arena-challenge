import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARCHIVO_RESULTADOS = Path(__file__).resolve().parents[1] / "data" / "resultados.json"


def fecha_actual_utc() -> str:
    """Fecha y hora actual en ISO 8601 con zona UTC, por ejemplo 2026-11-24T21:05:00+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AlmacenResultados:
    def __init__(self, ruta: Path = ARCHIVO_RESULTADOS):
        self.ruta = ruta
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._bloqueo = threading.RLock()
        self._datos = self._leer()

    def _leer(self) -> dict[str, Any]:
        if not self.ruta.exists():
            return {"partidas": []}
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            if isinstance(datos, list):
                # Resultados anteriores a la integración US-25.
                partidas = []
                for antiguo in datos:
                    if (not isinstance(antiguo, dict)
                            or not isinstance(antiguo.get("id"), str)
                            or not isinstance(antiguo.get("players"), dict)
                            or any(not isinstance(jugador, dict)
                                   for jugador in antiguo["players"].values())):
                        raise ValueError("El archivo de resultados anterior tiene datos inválidos.")
                    partidas.append({
                        "match_id": antiguo["id"],
                        "fecha": antiguo.get("fecha"),
                        "winner": antiguo.get("winner"),
                        "elapsed": float(antiguo.get("elapsed", 0)),
                        "overtime": int(antiguo.get("overtime", 0)),
                        "condition": antiguo.get("condition"),
                        "value": antiguo.get("value"),
                        "jugadores": {
                            puesto: {
                                "usuario": jugador.get("username"),
                                "score": int(jugador.get("score", 0)),
                                "avatar": jugador.get("avatar"),
                            }
                            for puesto, jugador in antiguo["players"].items()
                        },
                    })
                return {"partidas": partidas}
            if not isinstance(datos, dict) or not isinstance(datos.get("partidas"), list):
                return {"partidas": []}
            return datos
        except (json.JSONDecodeError, OSError):
            return {"partidas": []}

    def _guardar(self) -> None:
        temporal = self.ruta.with_suffix(self.ruta.suffix + ".tmp")
        temporal.write_text(json.dumps(self._datos, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temporal, self.ruta)

    def guardar_resultado(
        self,
        match_id: str,
        jugadores: dict[str, Any],
        winner: str | None,
        elapsed: float,
        overtime: int = 0,
        condition: str | None = None,
        value: int | None = None,
    ) -> dict[str, Any]:
        if not isinstance(match_id, str) or not match_id.strip():
            raise ValueError("match_id es requerido.")

        with self._bloqueo:
            for existente in self._datos["partidas"]:
                if existente.get("match_id") == match_id:
                    return {"ok": True, "duplicado": True, "resultado": existente}

            resultado = {
                "match_id": match_id,
                "fecha": fecha_actual_utc(),
                "winner": winner,
                "elapsed": float(elapsed),
                "overtime": int(overtime),
                "condition": condition,
                "value": value,
                "jugadores": {
                    nombre: {
                        "usuario": datos.get("usuario"),
                        "score": int(datos.get("score", 0)),
                        "avatar": datos.get("avatar"),
                    }
                    for nombre, datos in jugadores.items()
                },
            }
            self._datos["partidas"].append(resultado)
            self._guardar()
            return {"ok": True, "duplicado": False, "resultado": resultado}

    def listar(self) -> list[dict[str, Any]]:
        with self._bloqueo:
            return list(self._datos["partidas"])

    def obtener(self, match_id: str) -> dict[str, Any] | None:
        with self._bloqueo:
            return next((p for p in self._datos["partidas"] if p.get("match_id") == match_id), None)

    def ranking(self) -> list[dict[str, Any]]:
        totales: dict[str, dict[str, int]] = {}
        with self._bloqueo:
            for partida in self._datos["partidas"]:
                ganador = partida.get("winner")
                for puesto, datos in partida.get("jugadores", {}).items():
                    usuario = datos.get("usuario")
                    if not usuario:
                        continue
                    fila = totales.setdefault(usuario, {
                        "usuario": usuario,
                        "puntaje_total": 0,
                        "victorias": 0,
                        "partidas": 0,
                        "mejor_puntaje": 0,
                    })
                    puntaje = int(datos.get("score", 0))
                    fila["puntaje_total"] += puntaje
                    fila["partidas"] += 1
                    fila["mejor_puntaje"] = max(fila["mejor_puntaje"], puntaje)
                    if ganador == puesto:
                        fila["victorias"] += 1
        ranking = list(totales.values())
        ranking.sort(key=lambda fila: (
            -fila["puntaje_total"],
            -fila["victorias"],
            fila["usuario"].lower(),
        ))
        for posicion, fila in enumerate(ranking, 1):
            fila["posicion"] = posicion
        return ranking

    def historial(self, usuario: str) -> list[dict[str, Any]]:
        partidas = []
        with self._bloqueo:
            for partida in reversed(self._datos["partidas"]):
                for puesto, datos in partida.get("jugadores", {}).items():
                    if datos.get("usuario") == usuario:
                        partidas.append({
                            "match_id": partida["match_id"],
                            # Los registros anteriores a la fecha devuelven None.
                            "fecha": partida.get("fecha"),
                            "puesto": puesto,
                            "resultado": "victoria" if partida.get("winner") == puesto else "derrota",
                            "score": int(datos.get("score", 0)),
                            "winner": partida.get("winner"),
                            "elapsed": partida.get("elapsed", 0),
                            "overtime": partida.get("overtime", 0),
                            "condition": partida.get("condition"),
                            "value": partida.get("value"),
                        })
        return partidas
