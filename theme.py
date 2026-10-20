"""Tmavý vzhled pro tkinter/ttk (základ: motiv 'clam', který jde plně obarvit)."""

from __future__ import annotations

import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk

BG = "#15181e"  # pozadí okna
SURFACE = "#1d2129"  # karty, tabulka
SURFACE_ALT = "#21262f"  # sudé řádky
SURFACE_HI = "#2a303b"  # hlavička tabulky, sekundární tlačítka
BORDER = "#2e3440"
FIELD = "#252a34"
FG = "#e6e9ef"
MUTED = "#8b93a3"
ACCENT = "#4cc2ff"  # download, hlavní tlačítko
ACCENT_HOVER = "#7ad3ff"
UPLOAD = "#a48bff"
SELECT = "#2b4766"
LIMITED_BG = "#3a3122"
LIMITED_FG = "#ffcf70"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI Semibold", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI Semibold", 15)
FONT_TILE = ("Segoe UI Semibold", 17)


def resource_path(name: str) -> str:
    """Cesta k přibalenému souboru (funguje i v .exe z PyInstalleru)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def apply_theme(root: tk.Tk) -> None:
    root.configure(background=BG)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=FG, font=FONT, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, troughcolor=SURFACE,
                    fieldbackground=FIELD, selectbackground=SELECT, selectforeground=FG,
                    insertcolor=FG, focuscolor=BORDER)

    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=SURFACE)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Card.TLabel", background=SURFACE, foreground=FG)
    style.configure("CardMuted.TLabel", background=SURFACE, foreground=MUTED, font=FONT_SMALL)
    style.configure("CardBold.TLabel", background=SURFACE, foreground=FG, font=FONT_BOLD)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT_SMALL)
    style.configure("Title.TLabel", background=BG, foreground=FG, font=FONT_TITLE)
    style.configure("TileCaption.TLabel", background=SURFACE, foreground=MUTED, font=FONT_SMALL)
    style.configure("TileDown.TLabel", background=SURFACE, foreground=ACCENT, font=FONT_TILE)
    style.configure("TileUp.TLabel", background=SURFACE, foreground=UPLOAD, font=FONT_TILE)

    # tabulka bez rámečku, vyšší řádky
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=FG,
                    rowheight=28, borderwidth=0, font=FONT)
    style.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", FG)])
    style.configure("Treeview.Heading", background=SURFACE_HI, foreground=MUTED, font=FONT_BOLD,
                    relief="flat", borderwidth=0, padding=(8, 6))
    style.map("Treeview.Heading", background=[("active", BORDER)], foreground=[("active", FG)])

    style.configure("TButton", background=SURFACE_HI, foreground=FG, borderwidth=0,
                    relief="flat", padding=(16, 6), font=FONT_BOLD)
    style.map("TButton", background=[("pressed", BORDER), ("active", "#353c49")])
    style.configure("Accent.TButton", background=ACCENT, foreground="#0b1620")
    style.map("Accent.TButton", background=[("pressed", "#3aa6dd"), ("active", ACCENT_HOVER)])

    # přepínač jazyka
    style.configure("Lang.TButton", background=SURFACE, foreground=MUTED, padding=(6, 3),
                    font=("Segoe UI Semibold", 9))
    style.map("Lang.TButton", background=[("active", SURFACE_HI)], foreground=[("active", FG)])
    style.configure("LangOn.TButton", background=ACCENT, foreground="#0b1620", padding=(6, 3),
                    font=("Segoe UI Semibold", 9))
    style.map("LangOn.TButton", background=[("active", ACCENT_HOVER)])

    # tlačítko ⓘ – větší písmo, stejná výška jako přepínač jazyka
    style.configure("Info.TButton", background=SURFACE, foreground=MUTED, padding=(6, 0),
                    font=("Segoe UI Semibold", 12))
    style.map("Info.TButton", background=[("active", SURFACE_HI)], foreground=[("active", FG)])

    # odkazy v okně O programu
    style.configure("Link.TLabel", background=BG, foreground=ACCENT, font=FONT)
    style.map("Link.TLabel", foreground=[("active", ACCENT_HOVER)])
    style.configure("LinkSmall.TLabel", background=BG, foreground=ACCENT, font=FONT_SMALL)
    style.map("LinkSmall.TLabel", foreground=[("active", ACCENT_HOVER)])

    style.configure("TEntry", fieldbackground=FIELD, foreground=FG, bordercolor=BORDER,
                    lightcolor=FIELD, darkcolor=FIELD, padding=(8, 5), insertcolor=FG)
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])

    style.configure("TCheckbutton", background=BG, foreground=MUTED, indicatorbackground=FIELD,
                    indicatorforeground=BG, indicatormargin=(0, 0, 8, 0), focuscolor=BG)
    style.map("TCheckbutton", indicatorbackground=[("selected", ACCENT)],
              foreground=[("active", FG)], background=[("active", BG)])

    style.configure("Vertical.TScrollbar", background=SURFACE_HI, troughcolor=SURFACE,
                    bordercolor=SURFACE, arrowcolor=MUTED, lightcolor=SURFACE_HI,
                    darkcolor=SURFACE_HI, gripcount=0)
    style.map("Vertical.TScrollbar", background=[("active", BORDER)])

    try:
        root.iconbitmap(default=resource_path("icon.ico"))
    except tk.TclError:
        pass  # ikona chybí – nevadí


def dark_title_bar(root: tk.Tk) -> None:
    """Tmavý titulek okna na Windows 10 (20H1+) / 11."""
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        on = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))
        # Windows 11: barva titulku = barva okna (COLORREF 0x00BBGGRR)
        r, g, b = (int(BG[i:i + 2], 16) for i in (1, 3, 5))
        color = ctypes.c_int(r | (g << 8) | (b << 16))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
    except Exception:
        pass
