# Changelog

## 1.0.0 – 2026-10-20

First public release.

- Live per-process download/upload speeds in Mb/s
- Download and/or upload limit per process (token bucket with a bounded queue)
- Remove one process's limits or all limits at once (tray menu)
- Tray icon with speed tooltip; closing the window can minimize to tray
- Sortable table, default order by process name A→Z
- Dark theme, English and Czech UI
- Settings (language, close behaviour) remembered in `%APPDATA%\NetReins`
- Single instance – starting it again brings the running window to the front
- Clean shutdown: queued packets are released and the WinDivert handle is closed
