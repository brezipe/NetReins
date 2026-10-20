"""Okno „O programu“: verze, autor, licence, odkaz na GitHub a komponenty třetích stran."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import ttk

import theme
from i18n import t
from version import APP_NAME, AUTHOR, COPYRIGHT_YEAR, REPO_URL, __version__

# Komponenty přibalené v exe (viz THIRD_PARTY_NOTICES.md).
THIRD_PARTY = (
    ("WinDivert", "LGPL-3.0 / GPL-2.0"),
    ("pydivert", "LGPL-3.0 / GPL-2.0"),
    ("psutil", "BSD-3-Clause"),
    ("pystray", "LGPL-3.0"),
    ("Pillow", "MIT-CMU"),
    ("Python, Tcl/Tk", "PSF, Tcl/Tk License"),
    ("PyInstaller", "GPL-2.0 + bootloader exception"),
)


class AboutDialog:
    """Modální okno. Zavírá se tlačítkem, klávesou Esc nebo křížkem."""

    def __init__(self, root: tk.Tk):
        self.win = win = tk.Toplevel(root)
        win.title(t("about_title"))
        win.configure(background=theme.BG)
        win.resizable(False, False)
        win.transient(root)
        try:
            win.iconbitmap(theme.resource_path("icon.ico"))
        except tk.TclError:
            pass

        body = ttk.Frame(win, padding=(24, 20, 24, 18))
        body.pack(fill=tk.BOTH, expand=True)

        head = ttk.Frame(body)
        head.pack(fill=tk.X)
        try:
            self._logo = tk.PhotoImage(file=theme.resource_path("icon.png")).subsample(4)
            ttk.Label(head, image=self._logo).pack(side=tk.LEFT, padx=(0, 14))
        except tk.TclError:
            pass
        names = ttk.Frame(head)
        names.pack(side=tk.LEFT, anchor=tk.W)
        ttk.Label(names, text=APP_NAME, style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(names, text=t("about_version", version=__version__), style="Muted.TLabel").pack(anchor=tk.W)

        ttk.Label(body, text=t("about_description"), wraplength=380,
                  justify=tk.LEFT).pack(anchor=tk.W, pady=(16, 12))

        ttk.Label(body, text=f"© {COPYRIGHT_YEAR} {AUTHOR}").pack(anchor=tk.W)
        ttk.Label(body, text=t("about_license"), style="Muted.TLabel").pack(anchor=tk.W)

        links = ttk.Frame(body)
        links.pack(anchor=tk.W, pady=(12, 0))
        self._link(links, t("about_source"), REPO_URL).pack(anchor=tk.W)
        self._link(links, t("about_issues"), REPO_URL + "/issues").pack(anchor=tk.W)

        ttk.Label(body, text=t("about_components"), style="Muted.TLabel").pack(anchor=tk.W, pady=(16, 4))
        card = ttk.Frame(body, style="Card.TFrame", padding=(12, 8))
        card.pack(fill=tk.X)
        for row, (name, license_) in enumerate(THIRD_PARTY):
            ttk.Label(card, text=name, style="Card.TLabel").grid(row=row, column=0, sticky=tk.W, padx=(0, 18))
            ttk.Label(card, text=license_, style="CardMuted.TLabel").grid(row=row, column=1, sticky=tk.W)
        self._link(body, t("about_notices"), REPO_URL + "/blob/main/THIRD_PARTY_NOTICES.md",
                   small=True).pack(anchor=tk.W, pady=(6, 0))

        close = ttk.Button(body, text=t("about_close"), style="Accent.TButton", command=self.close)
        close.pack(anchor=tk.E, pady=(18, 0))

        win.bind("<Escape>", lambda _e: self.close())
        win.protocol("WM_DELETE_WINDOW", self.close)
        self._center_on(root)
        theme.dark_title_bar(win)
        win.grab_set()
        close.focus_set()

    def _link(self, parent, text: str, url: str, small: bool = False) -> ttk.Label:
        label = ttk.Label(parent, text=text, style="LinkSmall.TLabel" if small else "Link.TLabel",
                          cursor="hand2")
        label.bind("<Button-1>", lambda _e: webbrowser.open(url))
        return label

    def _center_on(self, root: tk.Tk) -> None:
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x = root.winfo_rootx() + (root.winfo_width() - w) // 2
        y = root.winfo_rooty() + (root.winfo_height() - h) // 3
        self.win.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def exists(self) -> bool:
        try:
            return bool(self.win.winfo_exists())
        except tk.TclError:
            return False

    def close(self) -> None:
        try:
            self.win.grab_release()
            self.win.destroy()
        except tk.TclError:
            pass
