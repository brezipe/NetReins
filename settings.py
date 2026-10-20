"""Uložená nastavení (jazyk, chování křížku) v %APPDATA%\\NetReins\\settings.json."""

from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)

DEFAULTS = {"language": "en", "to_tray": True}


def _path(folder: str = "NetReins") -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, folder, "settings.json")


def load() -> dict:
    data = dict(DEFAULTS)
    path = _path()
    legacy = _path("MiniNetLimiter")  # nastavení z verzí před přejmenováním
    if not os.path.exists(path) and os.path.exists(legacy):
        path = legacy
    try:
        with open(path, encoding="utf-8") as f:
            stored = json.load(f)
        if isinstance(stored, dict):
            data.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:  # poškozený soubor -> výchozí hodnoty
        log.warning("Nastavení nejde načíst (%s), použiju výchozí", e)
    return data


def save(data: dict) -> None:
    path = _path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError as e:
        log.warning("Nastavení nejde uložit: %s", e)
