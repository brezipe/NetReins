"""Okno O programu – otevře se, ukáže verzi a autora, nejde otevřít dvakrát."""

import tkinter as tk

import pytest

import about
import gui
import i18n
from version import AUTHOR, REPO_URL, __version__


class Stats:
    def sample(self):
        return {}

    def recently_active(self, within):
        return set()


class Engine:
    def get_limits(self):
        return {}


class Mapper:
    def pids_with_connections(self):
        return set()


class NoTray:
    available = False

    def __init__(self, commands):
        pass

    def start(self):
        pass

    def set_tooltip(self, text):
        pass

    def refresh_menu(self):
        pass

    def stop(self):
        pass


def texts(widget):
    out = []
    for child in widget.winfo_children():
        try:
            out.append(str(child.cget("text")))
        except tk.TclError:
            pass
        out.extend(texts(child))
    return out


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(gui.tray, "Tray", NoTray)
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display for Tk")
    root.withdraw()
    application = gui.NetReinsApp(root, Engine(), Mapper(), Stats())
    yield application
    application.stop_updates()
    root.destroy()
    i18n.set_language("en")


def test_about_shows_version_author_and_link(app):
    app.show_about()
    shown = texts(app._about.win)
    assert any(__version__ in s for s in shown)
    assert any(AUTHOR in s for s in shown)
    assert "Source code on GitHub" in shown
    assert REPO_URL.startswith("https://github.com/")


def test_about_opens_only_once(app):
    app.show_about()
    first = app._about.win
    app.show_about()
    assert app._about.win is first
    assert sum(isinstance(w, tk.Toplevel) for w in app.root.winfo_children()) == 1


def test_about_closes_and_reopens(app):
    app.show_about()
    app._about.close()
    assert not app._about.exists()
    app.show_about()
    assert app._about.exists()


def test_language_switch_with_about_open(app):
    app.show_about()
    app.set_language("cs")
    assert not app._about.exists()  # okno zmizí spolu se starým rozložením
    app.show_about()
    assert "Zdrojový kód na GitHubu" in texts(app._about.win)


def test_third_party_list_matches_notices():
    notices = open("THIRD_PARTY_NOTICES.md", encoding="utf-8").read()
    for name, _license in about.THIRD_PARTY:
        assert name.split(",")[0] in notices


def test_tray_menu_command_opens_about_with_hidden_window(app):
    import tray

    assert app.root.state() == "withdrawn"  # okno skryté v trayi
    app._tray_commands.put(tray.ABOUT)
    app._poll_tray()
    assert app._about.exists()
    assert app._about.win.state() == "normal"
    assert app._about._modal is False
    assert app.root.grab_current() is None  # neblokuje hlavní okno


def test_about_is_modal_over_visible_window(app):
    app.root.deiconify()
    app.root.update()
    app.show_about()
    assert app._about._modal is True


def test_header_has_no_info_button(app):
    assert "ⓘ" not in texts(app.root)
