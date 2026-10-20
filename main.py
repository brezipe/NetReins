"""NetReins – vstupní bod.

Spuštění (jako správce):  python main.py [--log soubor.log]
"""

from __future__ import annotations

import argparse
import atexit
import ctypes
import logging
import signal
import sys

from version import APP_NAME, __version__


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def fail(msg: str) -> None:
    logging.error(msg)
    if sys.stderr is not None:  # v .exe bez konzole je sys.stderr None
        print(msg, file=sys.stderr)
    # při spuštění přes pythonw.exe není konzole – ukaž i okno
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("NetReins", msg)
        r.destroy()
    except Exception:
        pass
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="NetReins")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--log", metavar="SOUBOR", help="zapisovat log do souboru (užitečné pro .exe bez konzole)")
    args = parser.parse_args()
    log_kwargs = {"filename": args.log, "encoding": "utf-8"} if args.log else {}
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        **log_kwargs)

    import i18n
    import settings
    from i18n import t

    i18n.set_language(settings.load()["language"])  # výchozí angličtina

    if sys.platform != "win32":
        fail(t("windows_only"))
    if not is_admin():
        fail(t("need_admin"))

    from winutil import SingleInstance

    instance = SingleInstance()
    if instance.already_running:
        # aplikace už běží (třeba skrytá v oznamovací oblasti) -> jen ukázat její okno
        instance.signal_existing()
        sys.exit(0)

    try:
        import psutil  # noqa: F401
        import pydivert  # noqa: F401
    except ImportError as e:
        fail(t("missing_lib", name=e.name))

    import tkinter as tk

    from capture import CaptureEngine
    from gui import NetReinsApp
    from monitor import PortMapper, TrafficStats

    mapper = PortMapper()
    stats = TrafficStats()
    engine = CaptureEngine(mapper, stats)

    def shutdown() -> None:
        engine.stop()  # idempotentní: vypustí fronty a zavře WinDivert handle
        mapper.stop()

    atexit.register(shutdown)

    # Zavření okna konzole / odhlášení / vypnutí: Windows proces po návratu
    # z handleru zabije, takže úklid musí proběhnout přímo tady.
    HANDLER = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

    @HANDLER
    def console_handler(event: int) -> bool:
        if event in (2, 5, 6):  # CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT
            shutdown()
            return True
        return False  # Ctrl+C / Ctrl+Break -> standardní Python signály níže

    ctypes.windll.kernel32.SetConsoleCtrlHandler(console_handler, True)

    mapper.start()
    try:
        engine.start()
    except OSError as e:
        mapper.stop()
        fail(t("windivert_failed", error=e))

    root = tk.Tk()
    app = NetReinsApp(root, engine, mapper, stats)

    def request_quit(*_args) -> None:
        root.quit()

    instance.listen(app.request_show)  # další spuštění -> ukázat toto okno
    root.protocol("WM_DELETE_WINDOW", app.on_close)  # skrýt do traye nebo ukončit
    signal.signal(signal.SIGINT, request_quit)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_quit)

    # Tk mainloop běží v C; krátký "tik" vrací řízení Pythonu, aby se Ctrl+C
    # z konzole doručilo včas.
    def keepalive() -> None:
        root.after(200, keepalive)

    keepalive()

    try:
        root.mainloop()
    finally:
        app.stop_updates()
        instance.close()
        shutdown()
        try:
            root.destroy()
        except tk.TclError:
            pass
    logging.info("Ukončeno.")


if __name__ == "__main__":
    main()
