"""Tkinter GUI: tabulka procesů s rychlostmi a ovládání limitů.

GUI běží v hlavním vlákně a se zachytávacími vlákny komunikuje jen přes
thread-safe metody CaptureEngine / TrafficStats / PortMapper.
"""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox, ttk

import about
import i18n
import settings
import theme
import tray
import winutil
from capture import CaptureEngine
from i18n import t
from monitor import DOWN, UNKNOWN_PID, UP, PortMapper, Rate, TrafficStats
from version import __version__

REFRESH_MS = 1000
MBIT = 125_000  # 1 Mb/s v bajtech za sekundu (10^6 bitů, stejně jako Správce úloh)
ACTIVE_WINDOW = 30.0  # s – jak dlouho ukazovat proces po posledním provozu

# Výchozí řazení: podle názvu procesu A→Z.
DEFAULT_SORT = "name"
DEFAULT_DESC = False

# (id sloupce, klíč textu v i18n, šířka, zarovnání)
COLUMNS = (
    ("name", "col_name", 200, tk.W),
    ("pid", "col_pid", 70, tk.E),
    ("down", "col_down", 120, tk.E),
    ("up", "col_up", 120, tk.E),
    ("ldown", "col_ldown", 80, tk.E),
    ("lup", "col_lup", 80, tk.E),
    ("drop", "col_drop", 80, tk.E),
)


def _fmt_rate(bps: float) -> str:
    """B/s -> text v Mb/s."""
    return f"{bps / MBIT:.2f}"


def _fmt_mbit(bps: float) -> str:
    """Limit v B/s -> Mb/s bez zbytečných nul (8, 0.5, 12.25)."""
    return f"{round(bps / MBIT, 3):g}"


def _fmt_limit(v: float | None) -> str:
    return "–" if v is None else _fmt_mbit(v)


def sort_rows(rows: list[dict], col: str | None, desc: bool) -> list[dict]:
    """Seřadí řádky podle sloupce. Prázdné hodnoty (bez limitu, nepřiřazený
    PID) jsou vždy na konci. Při shodě rozhoduje název a PID, aby řádky
    mezi obnoveními neposkakovaly."""
    def tiebreak(r):
        return (r["name"].lower(), r["pid"])

    rows = sorted(rows, key=tiebreak)  # stabilní řazení -> sekundární klíč
    if col is None:
        return sorted(rows, key=lambda r: r["down"] + r["up"], reverse=True)
    if col == "name":  # "(nepřiřazeno)" vždy na konec
        named = [r for r in rows if r["pid"] is not None]
        return sorted(named, key=lambda r: r["name"].lower(), reverse=desc) + \
            [r for r in rows if r["pid"] is None]
    present = [r for r in rows if r[col] is not None]
    missing = [r for r in rows if r[col] is None]
    return sorted(present, key=lambda r: r[col], reverse=desc) + missing


class NetReinsApp:
    def __init__(self, root: tk.Tk, engine: CaptureEngine, mapper: PortMapper, stats: TrafficStats):
        self.root = root
        self.engine = engine
        self.mapper = mapper
        self.stats = stats
        self._selected_pid: int | None = None
        self._after_id: str | None = None
        self._last_rates: dict[int, Rate] = {}
        self._sort_col: str | None = DEFAULT_SORT
        self._sort_desc = DEFAULT_DESC
        self._tray_commands: queue.Queue = queue.Queue()
        self.tray = tray.Tray(self._tray_commands)
        self._tray_hint_shown = False
        self._about: about.AboutDialog | None = None

        # stav ovládacích prvků žije mimo widgety, aby přežil přepnutí jazyka
        self.show_idle = tk.BooleanVar(value=False)
        self.to_tray = tk.BooleanVar(value=bool(settings.load()["to_tray"]))
        self.down_var = tk.StringVar()
        self.up_var = tk.StringVar()

        root.title("NetReins")
        root.geometry("900x600")
        root.minsize(720, 440)
        theme.apply_theme(root)
        theme.dark_title_bar(root)

        self.tray.start()
        self._build()
        self._tick()
        self._poll_tray()
        root.after(150, lambda: winutil.bring_to_front(root))  # po UAC okno jinak zůstane vzadu

    # --------------------------------------------------------------- layout
    def _build(self) -> None:
        # --- hlavička: ikona, název, přepínač jazyka, souhrnné rychlosti
        header = ttk.Frame(self.root, padding=(18, 16, 18, 10))
        header.pack(fill=tk.X)
        try:
            self._logo = tk.PhotoImage(file=theme.resource_path("icon.png")).subsample(6)
            ttk.Label(header, image=self._logo).pack(side=tk.LEFT, padx=(0, 12))
        except tk.TclError:
            pass
        titles = ttk.Frame(header)
        titles.pack(side=tk.LEFT)
        name_row = ttk.Frame(titles)
        name_row.pack(anchor=tk.W)
        ttk.Label(name_row, text="NetReins", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(name_row, text=f"v{__version__}", style="Muted.TLabel").pack(side=tk.LEFT, padx=(8, 0), pady=(6, 0))
        ttk.Label(titles, text=t("subtitle"), style="Muted.TLabel").pack(anchor=tk.W)

        langs = ttk.Frame(header)
        langs.pack(side=tk.RIGHT, anchor=tk.N, padx=(14, 0))
        ttk.Button(langs, text="ⓘ", style="Info.TButton", width=3,
                   command=self.show_about).pack(side=tk.LEFT, padx=(0, 8))
        for lang in i18n.LANGUAGES:
            style = "LangOn.TButton" if lang == i18n.get_language() else "Lang.TButton"
            ttk.Button(langs, text=i18n.LABELS[lang], style=style, width=3,
                       command=lambda l=lang: self.set_language(l)).pack(side=tk.LEFT, padx=(2, 0))

        self.tile_up = self._tile(header, "↑  UPLOAD", "TileUp.TLabel")
        self.tile_down = self._tile(header, "↓  DOWNLOAD", "TileDown.TLabel")

        # --- přepínače
        bar = ttk.Frame(self.root, padding=(18, 4, 18, 8))
        bar.pack(fill=tk.X)
        ttk.Checkbutton(bar, text=t("show_idle"), variable=self.show_idle,
                        command=self._refresh).pack(side=tk.LEFT)
        tray_check = ttk.Checkbutton(bar, text=t("to_tray"), variable=self.to_tray,
                                     command=self._save_to_tray)
        tray_check.pack(side=tk.LEFT, padx=(24, 0))
        if not self.tray.available:
            self.to_tray.set(False)  # jen pro tento běh, uložená volba zůstane
            tray_check.state(["disabled"])
        ttk.Label(bar, text=t("sort_hint"), style="Muted.TLabel").pack(side=tk.RIGHT)

        # --- tabulka v kartě
        card = ttk.Frame(self.root, style="Card.TFrame", padding=1)
        card.pack(fill=tk.BOTH, expand=True, padx=18)
        self.tree = ttk.Treeview(card, columns=[c[0] for c in COLUMNS], show="headings",
                                 selectmode="browse")
        for cid, _key, width, anchor in COLUMNS:
            self.tree.heading(cid, anchor=anchor, command=lambda c=cid: self._on_heading(c))
            self.tree.column(cid, width=width, anchor=anchor, stretch=(cid == "name"))
        self.tree.tag_configure("odd", background=theme.SURFACE_ALT)
        self.tree.tag_configure("limited", background=theme.LIMITED_BG, foreground=theme.LIMITED_FG)
        self.tree.tag_configure("muted", foreground=theme.MUTED)
        sb = ttk.Scrollbar(card, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._update_headings()

        # --- ovládání limitu
        panel = ttk.Frame(self.root, style="Card.TFrame", padding=(16, 12))
        panel.pack(fill=tk.X, padx=18, pady=(12, 0))
        panel.columnconfigure(0, weight=1)

        info = ttk.Frame(panel, style="Card.TFrame")
        info.grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info, text=t("selected"), style="CardMuted.TLabel").pack(anchor=tk.W)
        self.sel_lbl = ttk.Label(info, style="CardBold.TLabel")
        self.sel_lbl.pack(anchor=tk.W)
        self._update_sel_label()

        for col, (caption, var) in enumerate(((t("limit_down"), self.down_var),
                                              (t("limit_up"), self.up_var)), start=1):
            box = ttk.Frame(panel, style="Card.TFrame")
            box.grid(row=0, column=col, padx=(16, 0))
            ttk.Label(box, text=caption, style="CardMuted.TLabel").pack(anchor=tk.W)
            entry = ttk.Entry(box, textvariable=var, width=12)
            entry.pack(anchor=tk.W, pady=(2, 0))
            entry.bind("<Return>", lambda _e: self._apply())

        ttk.Button(panel, text=t("apply"), style="Accent.TButton",
                   command=self._apply).grid(row=0, column=3, padx=(20, 0), sticky=tk.S)
        ttk.Button(panel, text=t("clear"), command=self._clear).grid(row=0, column=4, padx=(8, 0), sticky=tk.S)

        ttk.Label(self.root, text=t("footer"), style="Muted.TLabel",
                  padding=(18, 8, 18, 12)).pack(anchor=tk.W)

    def _tile(self, parent, caption: str, value_style: str) -> ttk.Label:
        tile = ttk.Frame(parent, style="Card.TFrame", padding=(14, 8))
        tile.pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Label(tile, text=caption, style="TileCaption.TLabel").pack(anchor=tk.W)
        value = ttk.Label(tile, text="0.00 Mb/s", style=value_style, width=12)
        value.pack(anchor=tk.W)
        return value

    def _save_to_tray(self) -> None:
        settings.save({**settings.load(), "to_tray": self.to_tray.get()})

    def show_about(self) -> None:
        if self._about is not None and self._about.exists():
            self._about.win.lift()
            return
        self._about = about.AboutDialog(self.root)

    # ---------------------------------------------------------------- jazyk
    def set_language(self, lang: str) -> None:
        if lang == i18n.get_language():
            return
        i18n.set_language(lang)
        settings.save({**settings.load(), "language": lang})
        for child in self.root.winfo_children():
            child.destroy()
        self._build()
        self._refresh()
        if self._selected_pid is not None and self.tree.exists(str(self._selected_pid)):
            self.tree.selection_set(str(self._selected_pid))
        self.tray.refresh_menu()

    # ---------------------------------------------------------------- refresh
    def _tick(self) -> None:
        # vzorek statistik bereme jen tady, jednou za REFRESH_MS
        self._last_rates = self.stats.sample()
        self._refresh()
        self._after_id = self.root.after(REFRESH_MS, self._tick)

    def _process_name(self, pid: int) -> str:
        return t("unassigned") if pid == UNKNOWN_PID else self.mapper.process_name(pid)

    def _refresh(self) -> None:
        rates = self._last_rates
        limits = self.engine.get_limits()

        pids = self.stats.recently_active(ACTIVE_WINDOW) | set(limits)
        if self.show_idle.get():
            pids |= self.mapper.pids_with_connections()

        rows = []
        tot_down = tot_up = 0.0
        for pid in pids:
            r = rates.get(pid, Rate())
            tot_down += r.down
            tot_up += r.up
            lim = limits.get(pid, {})
            rows.append({
                "iid": str(pid),
                "name": self._process_name(pid),
                "pid": None if pid == UNKNOWN_PID else pid,
                "down": r.down,
                "up": r.up,
                "ldown": lim.get(DOWN),
                "lup": lim.get(UP),
                "drop": r.dropped or None,
            })
        rows = sort_rows(rows, self._sort_col, self._sort_desc)

        existing = set(self.tree.get_children())
        wanted = set()
        for index, row in enumerate(rows):
            iid = row["iid"]
            values = (
                row["name"],
                "–" if row["pid"] is None else row["pid"],
                _fmt_rate(row["down"]),
                _fmt_rate(row["up"]),
                _fmt_limit(row["ldown"]),
                _fmt_limit(row["lup"]),
                row["drop"] or "",
            )
            wanted.add(iid)
            if row["ldown"] is not None or row["lup"] is not None:
                tags = ("limited",)
            else:
                tags = ("odd",) if index % 2 else ()
                if row["pid"] is None or row["down"] + row["up"] < 1:
                    tags += ("muted",)
            if iid in existing:
                self.tree.item(iid, values=values, tags=tags)
                self.tree.move(iid, "", index)
            else:
                self.tree.insert("", index, iid=iid, values=values, tags=tags)
        for iid in existing - wanted:
            self.tree.delete(iid)

        self.tile_down.config(text=f"{_fmt_rate(tot_down)} Mb/s")
        self.tile_up.config(text=f"{_fmt_rate(tot_up)} Mb/s")
        n = len(limits)
        speeds = f"↓ {_fmt_rate(tot_down)} Mb/s   ↑ {_fmt_rate(tot_up)} Mb/s"
        status = t("tooltip_limited", n=n) if n else t("tooltip_none")
        self.tray.set_tooltip("\n".join(("NetReins", speeds, status)))

    # --------------------------------------------------------------- řazení
    def _on_heading(self, col: str) -> None:
        """Klik na hlavičku: stejný sloupec přepne směr, nový sloupec začne
        sestupně (u názvu vzestupně). Další klik vrátí výchozí řazení (název A→Z)."""
        if col != self._sort_col:
            self._sort_col, self._sort_desc = col, col != "name"
        elif self._sort_desc == (col != "name"):
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col, self._sort_desc = DEFAULT_SORT, DEFAULT_DESC
        self._update_headings()
        self._refresh()

    def _update_headings(self) -> None:
        for cid, key, _w, _a in COLUMNS:
            arrow = ""
            if cid == self._sort_col:
                arrow = " ▼" if self._sort_desc else " ▲"
            self.tree.heading(cid, text=t(key) + arrow)

    # ------------------------------------------------------------- ovládání
    def _update_sel_label(self) -> None:
        pid = self._selected_pid
        if pid is None:
            text = t("select_prompt")
        elif pid == UNKNOWN_PID:
            text = t("unassigned_sel")
        else:
            text = f"{self._process_name(pid)}  (PID {pid})"
        self.sel_lbl.config(text=text)

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        if pid == self._selected_pid:
            return
        self._selected_pid = pid
        self._update_sel_label()
        lim = self.engine.get_limits().get(pid, {})
        self.down_var.set(_fmt_mbit(lim[DOWN]) if DOWN in lim else "")
        self.up_var.set(_fmt_mbit(lim[UP]) if UP in lim else "")

    def _parse(self, text: str, label: str) -> float | None:
        text = text.strip().replace(",", ".")
        if not text:
            return None
        try:
            v = float(text)
        except ValueError:
            raise ValueError(t("err_not_number", label=label, text=text))
        if v <= 0:
            raise ValueError(t("err_not_positive", label=label))
        return v

    def _apply(self) -> None:
        pid = self._selected_pid
        if pid is None or pid == UNKNOWN_PID:
            messagebox.showinfo("NetReins", t("need_selection"))
            return
        try:
            down = self._parse(self.down_var.get(), "Download")
            up = self._parse(self.up_var.get(), "Upload")
        except ValueError as e:
            messagebox.showerror(t("err_title"), str(e))
            return
        if down is None and up is None:
            messagebox.showinfo("NetReins", t("need_limit"))
            return
        self.engine.set_limit(pid, None if down is None else down * MBIT,
                              None if up is None else up * MBIT)
        self._refresh()

    def _clear(self) -> None:
        if self._selected_pid is None:
            return
        self.engine.clear_limit(self._selected_pid)
        self.down_var.set("")
        self.up_var.set("")
        self._refresh()

    # ------------------------------------------------- okno a oznamovací oblast
    def on_close(self) -> None:
        """Křížek okna: skrýt do traye, nebo ukončit (podle checkboxu)."""
        if self.to_tray.get() and self.tray.available:
            self.root.withdraw()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.notify(t("tray_hint"))
        else:
            self.root.quit()

    def show_window(self) -> None:
        winutil.bring_to_front(self.root)

    def request_show(self) -> None:
        """Thread-safe: zobrazit okno (volá se např. z jiného vlákna)."""
        self._tray_commands.put(tray.SHOW)

    def clear_all_limits(self) -> None:
        for pid in list(self.engine.get_limits()):
            self.engine.clear_limit(pid)
        self.down_var.set("")
        self.up_var.set("")
        self._refresh()

    def _poll_tray(self) -> None:
        try:
            while True:
                cmd = self._tray_commands.get_nowait()
                if cmd == tray.SHOW:
                    self.show_window()
                elif cmd == tray.CLEAR_ALL:
                    self.clear_all_limits()
                elif cmd == tray.QUIT:
                    self.root.quit()
        except queue.Empty:
            pass
        self._poll_id = self.root.after(150, self._poll_tray)

    def stop_updates(self) -> None:
        for attr in ("_after_id", "_poll_id"):
            after_id = getattr(self, attr, None)
            if after_id is not None:
                self.root.after_cancel(after_id)
                setattr(self, attr, None)
        self.tray.stop()
