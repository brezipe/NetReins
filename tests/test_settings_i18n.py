import json
import string

import pytest

import i18n
import settings


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_defaults_without_file(appdata):
    assert settings.load() == {"language": "en", "to_tray": True}


def test_save_and_load_roundtrip(appdata):
    settings.save({"language": "cs", "to_tray": False})
    assert settings.load() == {"language": "cs", "to_tray": False}


def test_corrupt_file_falls_back_to_defaults(appdata):
    path = appdata / "NetReins" / "settings.json"
    path.parent.mkdir()
    path.write_text("{not json", encoding="utf-8")
    assert settings.load() == settings.DEFAULTS


def test_unknown_keys_are_ignored(appdata):
    path = appdata / "NetReins" / "settings.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"language": "cs", "foo": 1}), encoding="utf-8")
    assert settings.load() == {"language": "cs", "to_tray": True}


def _fields(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


@pytest.mark.parametrize("key", sorted(i18n.STRINGS))
def test_every_string_has_all_languages_with_same_placeholders(key):
    texts = i18n.STRINGS[key]
    assert set(texts) == set(i18n.LANGUAGES)
    assert _fields(texts["en"]) == _fields(texts["cs"])


def test_unknown_language_falls_back_to_english():
    i18n.set_language("de")
    try:
        assert i18n.get_language() == "en"
        assert i18n.t("apply") == "Limit"
    finally:
        i18n.set_language("en")


def test_settings_from_old_name_are_migrated(appdata):
    old = appdata / "MiniNetLimiter" / "settings.json"
    old.parent.mkdir()
    old.write_text(json.dumps({"language": "cs", "to_tray": False}), encoding="utf-8")
    assert settings.load() == {"language": "cs", "to_tray": False}
    settings.save({"language": "en", "to_tray": False})  # nový soubor má přednost
    assert settings.load()["language"] == "en"
