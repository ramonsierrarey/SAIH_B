import json
import logging
import math
import threading
import time
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen


STATION_URL = "https://saihtajo.chtajo.es/index.php?w=get-estacion&x="
STATIONS = {
    "E_17": {
        "name": "El Burguillo",
        "url": STATION_URL + "%2F4ZGs%2B6M%2BZWfvq6%2Fyxpbhfug5v6QdmEbnkcbbPUchrAQm17PljU5sk9NrV8SjdgDgOJzq4683U7RnVQ5Yw0xDKUbVFxwN%2BErTEHT6LcELhg%3D",
        "required": {"E_17VICT01", "E_17VPCT01", "E_17LICT01", "E_17FICT95"},
    },
    "PN34": {
        "name": "Puerto del Pico",
        "url": STATION_URL + "%2F4ZGs%2B6M%2BZWfvq6%2FyxpbhXxe1RN4TjrOTwkB4X7BpMWQ8sr09LiFYx6MMIQVqZCLMTHoiMESs306twfMu8QzgHWEE7%2FyBhcWWoJ0dxbnxEg%3D",
        "required": {"PN34WIC101", "PN34WIC601"},
    },
    "AR21": {
        "name": "Alberche en Navaluenga",
        "url": STATION_URL + "%2F4ZGs%2B6M%2BZWfvq6%2FyxpbhZFiKGnIM5ctzq%2B7hlV7zLF01IVX%2Fc9IHw2nDfkgPwlcfW%2FgQ7e6aPPj8hiuuVHU3%2FJn0LflhVeicWUF7ehvWnI%3D",
        "required": {"AR21LI__01", "AR21FICT98"},
    },
    "E_18": {
        "name": "Charco del Cura",
        "url": STATION_URL + "%2F4ZGs%2B6M%2BZWfvq6%2FyxpbhcUvFn1hD938d6Di3gXW7yfOeOW5rG0ghJNKOfdIjAG98zC%2FCe6w858m2EylL9aEzSEWTfIdsX19FXCug68u47k%3D",
        "required": {"E_18VPCT01"},
    },
}
SOURCE_PAGE = "https://saihtajo.chtajo.es/tiemporeal"
STATION = "E_17"
INTERVAL = 3600
MANUAL_INTERVAL = 60
SIGNALS = {
    "E_17VICT01": ("Volumen embalsado · El Burguillo", "hm³", "E_17"),
    "E_17VPCT01": ("Capacidad utilizada · El Burguillo", "%", "E_17"),
    "E_17LICT01": ("Cota del embalse · El Burguillo", "m", "E_17"),
    "E_17FICT95": ("Salida al río · El Burguillo", "m³/s", "E_17"),
    "E_17WIC101": ("Precipitación última hora · El Burguillo", "mm/h", "E_17"),
    "E_17WIC601": ("Precipitación últimas 24 horas · El Burguillo", "mm", "E_17"),
    "E_17WI__01": ("Pluviómetro · El Burguillo", "mm", "E_17"),
    "PN34WIC101": ("Precipitación última hora · Puerto del Pico", "mm/h", "PN34"),
    "PN34WIC601": ("Precipitación últimas 24 horas · Puerto del Pico", "mm", "PN34"),
    "PN34WI__01": ("Pluviómetro · Puerto del Pico", "mm", "PN34"),
    "AR21LI__01": ("Nivel del río · Navaluenga", "m", "AR21"),
    "AR21FICT98": ("Caudal circulante · Navaluenga", "m³/s", "AR21"),
    "E_18VPCT01": ("Capacidad utilizada · Charco del Cura", "%", "E_18"),
    "E_18FICT95": ("Salida al río · Charco del Cura", "m³/s", "E_18"),
    "E_18LICT01": ("Cota del embalse · Charco del Cura", "m", "E_18"),
    "E_18VICT01": ("Volumen embalsado · Charco del Cura", "hm³", "E_18"),
}
REFRESH_LOCK = threading.Lock()
DATA_LOCK = threading.Lock()
READINGS = {}
STATION_STATUS = {
    code: {"last_success": None, "last_error": None}
    for code in STATIONS
}
LAST_ATTEMPT = float("-inf")
LAST_MANUAL = float("-inf")
LOGGER = logging.getLogger("burguillo")


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_response(payload, station):
    response = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(response, dict) or response.get("ok") != 1 or response.get("codigo") != station:
        raise ValueError("La fuente no devolvió la estación esperada.")
    signals = response.get("senales")
    if not isinstance(signals, list):
        raise ValueError("La fuente no devolvió la lista de señales.")
    readings = []
    seen = set()
    for signal in signals:
        if not isinstance(signal, dict):
            raise ValueError("Formato de señal inválido.")
        tag = signal.get("tag")
        if tag not in SIGNALS or SIGNALS[tag][2] != station:
            continue
        values = signal.get("valores")
        if not isinstance(values, list):
            raise ValueError(f"Faltan las mediciones de {tag}.")
        for item in values:
            if not isinstance(item, dict) or item.get("tag") != tag or item.get("remota") != station:
                raise ValueError(f"Medición inválida en {tag}.")
            value = item.get("valor")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Valor inválido en {tag}.")
            try:
                measured_at = datetime.strptime(item["tiempo"], "%d/%m/%Y %H:%M").isoformat(timespec="minutes")
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Fecha inválida en {tag}.") from exc
            readings.append((tag, measured_at, value))
            seen.add(tag)
    if not STATIONS[station]["required"].issubset(seen):
        raise ValueError("Faltan mediciones principales en la respuesta del SAIH.")
    return readings


def fetch_readings(station):
    request = Request(STATIONS[station]["url"], headers={"User-Agent": "BurguilloMonitor/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=25) as response:
        return parse_response(json.load(response), station)


def refresh(manual=False):
    global LAST_ATTEMPT, LAST_MANUAL
    if not REFRESH_LOCK.acquire(blocking=False):
        return False, "Ya hay una actualización en curso."
    try:
        now = time.monotonic()
        if manual and now - LAST_MANUAL < MANUAL_INTERVAL:
            return False, "Espera un minuto antes de volver a actualizar."
        if not manual and now - LAST_ATTEMPT < INTERVAL:
            return True, "Datos disponibles."
        LAST_ATTEMPT = now
        if manual:
            LAST_MANUAL = now
        failed = []
        for station, config in STATIONS.items():
            try:
                readings = fetch_readings(station)
                with DATA_LOCK:
                    READINGS[station] = readings
                    STATION_STATUS[station]["last_success"] = now_utc()
                    STATION_STATUS[station]["last_error"] = None
                LOGGER.info("%s: %s registros recibidos", station, len(readings))
            except (URLError, OSError, ValueError) as exc:
                failed.append(config["name"])
                LOGGER.exception("Error al actualizar %s", station)
                with DATA_LOCK:
                    STATION_STATUS[station]["last_error"] = f"{now_utc()} — {exc}"
        if failed:
            return False, f"No se pudieron actualizar: {', '.join(failed)}. Las demás estaciones se han procesado."
        return True, "Datos actualizados."
    finally:
        REFRESH_LOCK.release()


def get_data():
    with DATA_LOCK:
        readings = [
            {"tag": tag, "measured_at": measured_at, "value": value}
            for station_readings in READINGS.values()
            for tag, measured_at, value in station_readings
        ]
        stations = {
            code: {"name": config["name"], **STATION_STATUS[code]}
            for code, config in STATIONS.items()
        }
    readings.sort(key=lambda reading: (reading["measured_at"], reading["tag"]))
    latest_by_tag = {}
    for reading in readings:
        current = latest_by_tag.get(reading["tag"])
        if current is None or reading["measured_at"] > current["measured_at"]:
            latest_by_tag[reading["tag"]] = reading
    return {
        "station": STATION,
        "source": SOURCE_PAGE,
        "signals": {tag: {"name": name, "unit": unit, "station": station} for tag, (name, unit, station) in SIGNALS.items()},
        "stations": stations,
        "latest": sorted(latest_by_tag.values(), key=lambda reading: reading["tag"]),
        "readings": readings,
    }
