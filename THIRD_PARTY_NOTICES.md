# Third-party notices

The NetReins source code is MIT licensed (see [LICENSE](LICENSE)).
The released `NetReins.exe` bundles the following components, each under its
own license. Their source code is available at the linked projects; NetReins
uses them unmodified.

| Component | License | Source |
|---|---|---|
| WinDivert 2.2 (driver `WinDivert64.sys`, `WinDivert64.dll`) | LGPL-3.0-or-later or GPL-2.0-or-later | https://github.com/basil00/WinDivert |
| pydivert | LGPL-3.0-or-later or GPL-2.0-or-later | https://github.com/ffalcinelli/pydivert |
| psutil | BSD-3-Clause | https://github.com/giampaolo/psutil |
| pystray | LGPL-3.0 | https://github.com/moses-palmer/pystray |
| Pillow | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |
| Python and its standard library, including tkinter / Tcl/Tk | PSF License, Tcl/Tk License | https://www.python.org |
| PyInstaller bootloader | GPL-2.0 with bootloader exception | https://github.com/pyinstaller/pyinstaller |

## LGPL components

WinDivert, pydivert and pystray are used as libraries. To use NetReins with a
modified version of any of them, install that version and rebuild the exe from
this repository with `build_exe.bat`, or run NetReins from source
(`python main.py`).
