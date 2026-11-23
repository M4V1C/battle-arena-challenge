import json
import os
import threading
from pathlib import Path
from typing import Any


ARCHIVO_RESULTADOS = Path(__file__).resolve().parents[1] / "data" / "resultados.json"


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
