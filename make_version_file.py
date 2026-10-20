"""Vygeneruje build/version_info.txt pro PyInstaller (--version-file).

Údaje se pak zobrazí ve Vlastnostech exe → Podrobnosti.
Použití:  python make_version_file.py
"""

from __future__ import annotations

from pathlib import Path

from version import APP_NAME, __version__

TEMPLATE = """\
VSVersionInfo(
  ffi=FixedFileInfo(filevers={v4}, prodvers={v4}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Petr Březina'),
      StringStruct('FileDescription', '{name} – per-process network monitor and limiter'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', 'NetReins'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 Petr Březina, MIT License'),
      StringStruct('OriginalFilename', 'NetReins.exe'),
      StringStruct('ProductName', '{name}'),
      StringStruct('ProductVersion', '{ver}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    parts = [int(p) for p in __version__.split(".")]
    v4 = tuple((parts + [0, 0, 0, 0])[:4])
    out = Path(__file__).resolve().parent / "build" / "version_info.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(TEMPLATE.format(v4=v4, ver=__version__, name=APP_NAME), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
