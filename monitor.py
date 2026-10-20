"""Statistiky provozu a mapování lokálních portů na PID.

- PortMapper: cache (protokol, lokální port) -> PID z psutil, obnovovaná
  v samostatném vlákně každé ~2 s (při neznámém portu i dřív).
- TrafficStats: thread-safe počítadla bajtů per PID a směr, ze kterých GUI
  jednou za sekundu spočítá rychlost.
"""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass

import psutil

DOWN = "down"
UP = "up"

UNKNOWN_PID = -1  # provoz, který se nepodařilo přiřadit žádnému procesu


class PortMapper:
    """Mapuje (proto, lokální port) -> PID pomocí psutil.net_connections()."""

    def __init__(self, refresh_interval: float = 2.0, min_interval: float = 0.25):
        self._refresh_interval = refresh_interval
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._ports: dict[tuple[str, int], int] = {}
        self._pids_with_conns: set[int] = set()
        self._names: dict[int, str] = {}
        self._wakeup = threading.Event()
        self._stop = threading.Event()
        self._last_refresh = 0.0
        self._thread = threading.Thread(target=self._run, name="port-mapper", daemon=True)

    def start(self) -> None:
        self.refresh()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wakeup.set()
        if self._thread.is_alive():
            self._thread.join(timeout=3)

    def lookup(self, proto: str, port: int) -> int | None:
        # dict.get je atomické díky GIL, ale zámek je levný a explicitní
        with self._lock:
            pid = self._ports.get((proto, port))
        if pid is None:
            self._wakeup.set()  # nové spojení -> obnov cache dřív než za 2 s
        return pid

    def pids_with_connections(self) -> set[int]:
        with self._lock:
            return set(self._pids_with_conns)

    def process_name(self, pid: int) -> str:
        if pid == UNKNOWN_PID:
            return "(nepřiřazeno)"
        with self._lock:
            name = self._names.get(pid)
        if name is None:
            try:
                name = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                name = "?" if pid else "System Idle"
            with self._lock:
                self._names[pid] = name
        return name

    def refresh(self) -> None:
        ports: dict[tuple[str, int], int] = {}
        pids: set[int] = set()
        try:
            conns = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, OSError):
            conns = []
        for c in conns:
            if not c.laddr or not c.pid:
                continue
            proto = "tcp" if c.type == socket.SOCK_STREAM else "udp"
            ports[(proto, c.laddr.port)] = c.pid
            pids.add(c.pid)
        with self._lock:
            self._ports = ports
            self._pids_with_conns = pids
            # jména ukončených procesů zahodíme, PID se může recyklovat
            self._names = {p: n for p, n in self._names.items() if p in pids}
        self._last_refresh = time.monotonic()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wakeup.wait(self._refresh_interval)
            if self._stop.is_set():
                break
            self._wakeup.clear()
            # omez frekvenci mimořádných obnovení (net_connections je drahé)
            delay = self._min_interval - (time.monotonic() - self._last_refresh)
            if delay > 0:
                self._stop.wait(delay)
            self.refresh()


@dataclass
class Rate:
    down: float = 0.0  # B/s
    up: float = 0.0  # B/s
    dropped: int = 0  # celkem zahozených paketů


class TrafficStats:
    """Thread-safe počítadla. Volá je zachytávací vlákno při skutečném odeslání
    (reinjekci) paketu, takže měření odpovídá i omezenému provozu."""

    def __init__(self):
        self._lock = threading.Lock()
        self._bytes: dict[int, list[int]] = {}  # pid -> [down, up] od posledního sample()
        self._dropped: dict[int, int] = {}
        self._last_sample = time.monotonic()
        self._last_seen: dict[int, float] = {}

    def add(self, pid: int, direction: str, nbytes: int) -> None:
        with self._lock:
            b = self._bytes.get(pid)
            if b is None:
                b = self._bytes[pid] = [0, 0]
            b[0 if direction == DOWN else 1] += nbytes

    def add_drop(self, pid: int) -> None:
        with self._lock:
            self._dropped[pid] = self._dropped.get(pid, 0) + 1

    def sample(self) -> dict[int, Rate]:
        """Vrátí rychlosti od posledního volání a vynuluje počítadla."""
        now = time.monotonic()
        with self._lock:
            elapsed = max(now - self._last_sample, 1e-3)
            data, self._bytes = self._bytes, {}
            dropped = dict(self._dropped)
            self._last_sample = now
        rates: dict[int, Rate] = {}
        for pid, (down, up) in data.items():
            rates[pid] = Rate(down / elapsed, up / elapsed, dropped.get(pid, 0))
            if down or up:
                self._last_seen[pid] = now
        for pid, n in dropped.items():
            rates.setdefault(pid, Rate(dropped=n))
        return rates

    def recently_active(self, within: float) -> set[int]:
        """PID s provozem za posledních `within` sekund (volat z vlákna GUI)."""
        limit = time.monotonic() - within
        return {pid for pid, t in self._last_seen.items() if t >= limit}
