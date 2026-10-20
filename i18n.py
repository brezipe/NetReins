"""Texty aplikace v angličtině a češtině."""

from __future__ import annotations

LANGUAGES = ("en", "cs")
LABELS = {"en": "EN", "cs": "CZ"}  # popisky přepínače

_lang = "en"

STRINGS: dict[str, dict[str, str]] = {
    "subtitle": {
        "en": "Network traffic and per-process limits",
        "cs": "Síťový provoz a limity jednotlivých procesů",
    },
    "show_idle": {
        "en": "Show idle processes with network connections",
        "cs": "Zobrazit i nečinné procesy se síťovým spojením",
    },
    "to_tray": {
        "en": "Minimize to tray when closed",
        "cs": "Při zavření skrýt do oznamovací oblasti",
    },
    "sort_hint": {"en": "Click a column header to sort", "cs": "Klik na hlavičku sloupce = řazení"},
    "col_name": {"en": "Process", "cs": "Proces"},
    "col_pid": {"en": "PID", "cs": "PID"},
    "col_down": {"en": "Download Mb/s", "cs": "Download Mb/s"},
    "col_up": {"en": "Upload Mb/s", "cs": "Upload Mb/s"},
    "col_ldown": {"en": "Limit DL", "cs": "Limit DL"},
    "col_lup": {"en": "Limit UL", "cs": "Limit UL"},
    "col_drop": {"en": "Dropped", "cs": "Zahozeno"},
    "selected": {"en": "SELECTED PROCESS", "cs": "VYBRANÝ PROCES"},
    "select_prompt": {"en": "Select a process in the table", "cs": "Vyber proces v tabulce"},
    "unassigned": {"en": "(unassigned)", "cs": "(nepřiřazeno)"},
    "unassigned_sel": {
        "en": "Unassigned traffic cannot be limited",
        "cs": "Nepřiřazený provoz nelze omezit",
    },
    "limit_down": {"en": "↓ Download limit (Mb/s)", "cs": "↓ Limit download (Mb/s)"},
    "limit_up": {"en": "↑ Upload limit (Mb/s)", "cs": "↑ Limit upload (Mb/s)"},
    "apply": {"en": "Limit", "cs": "Omezit"},
    "clear": {"en": "Remove", "cs": "Zrušit"},
    "footer": {
        "en": "Empty field = no limit for that direction  ·  Remove clears both limits  ·  1 Mb/s ≈ 122 kB/s",
        "cs": "Prázdné pole = směr neomezovat  ·  Zrušit odstraní oba limity  ·  1 Mb/s ≈ 122 kB/s",
    },
    "err_not_number": {"en": "{label}: '{text}' is not a number", "cs": "{label}: '{text}' není číslo"},
    "err_not_positive": {"en": "{label}: the limit must be positive", "cs": "{label}: limit musí být kladný"},
    "err_title": {"en": "Invalid limit", "cs": "Neplatný limit"},
    "need_selection": {"en": "Select a process in the table first.", "cs": "Nejdřív vyber proces v tabulce."},
    "need_limit": {
        "en": "Enter a download and/or upload limit.",
        "cs": "Zadej limit downloadu a/nebo uploadu.",
    },
    "tooltip_limited": {"en": "Limited processes: {n}", "cs": "Omezeno procesů: {n}"},
    "tooltip_none": {"en": "No limits", "cs": "Bez omezení"},
    "tray_hint": {
        "en": "Still running in the background and limits stay active. "
              "To quit: right-click the icon → Quit.",
        "cs": "Běží dál na pozadí a omezení zůstávají aktivní. "
              "Ukončit: pravé tlačítko na ikoně → Ukončit.",
    },
    "about_title": {"en": "About NetReins", "cs": "O programu NetReins"},
    "about_version": {"en": "Version {version}", "cs": "Verze {version}"},
    "about_description": {
        "en": "Per-process network monitor and bandwidth limiter for Windows. "
              "Shows which programs use the network and lets you cap their download and upload speed.",
        "cs": "Monitor a omezovač síťového provozu jednotlivých procesů pro Windows. "
              "Ukazuje, které programy používají síť, a umí omezit jejich rychlost stahování a odesílání.",
    },
    "about_license": {
        "en": "Free and open source software, MIT License",
        "cs": "Svobodný software s otevřeným kódem, licence MIT",
    },
    "about_source": {"en": "Source code on GitHub", "cs": "Zdrojový kód na GitHubu"},
    "about_issues": {"en": "Report a problem", "cs": "Nahlásit problém"},
    "about_components": {"en": "THIRD-PARTY COMPONENTS", "cs": "KOMPONENTY TŘETÍCH STRAN"},
    "about_notices": {"en": "Full license notices", "cs": "Úplné licenční informace"},
    "about_close": {"en": "Close", "cs": "Zavřít"},
    "tray_open": {"en": "Open", "cs": "Otevřít"},
    "tray_about": {"en": "About", "cs": "O programu"},
    "tray_clear_all": {"en": "Remove all limits", "cs": "Zrušit všechna omezení"},
    "tray_quit": {"en": "Quit", "cs": "Ukončit"},
    "need_admin": {
        "en": "The program must run as administrator (WinDivert installs a network driver).\n\n"
              "Open a terminal with 'Run as administrator' and start it again:\n"
              "    python main.py\n\n"
              "(The .exe version asks for administrator rights by itself.)",
        "cs": "Program musí běžet jako správce (WinDivert instaluje síťový ovladač).\n\n"
              "Otevři terminál přes 'Spustit jako správce' a spusť znovu:\n"
              "    python main.py\n\n"
              "(Verze .exe si o práva správce řekne sama.)",
    },
    "windows_only": {
        "en": "NetReins only works on Windows (WinDivert).",
        "cs": "NetReins funguje jen na Windows (WinDivert).",
    },
    "missing_lib": {
        "en": "Missing library: {name}. Install dependencies:\n    pip install -r requirements.txt",
        "cs": "Chybí knihovna: {name}. Nainstaluj závislosti:\n    pip install -r requirements.txt",
    },
    "windivert_failed": {
        "en": "Could not open WinDivert: {error}",
        "cs": "Nepodařilo se otevřít WinDivert: {error}",
    },
}


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGUAGES else "en"


def get_language() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    text = STRINGS[key].get(_lang) or STRINGS[key]["en"]
    return text.format(**kwargs) if kwargs else text
