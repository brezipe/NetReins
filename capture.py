"""Zachytávání paketů přes WinDivert a škrcení pomocí token bucketu.

Vlákna:
- capture: recv() z WinDivertu, přiřazení paketu k PID, buď okamžité
  odeslání, nebo zařazení do fronty omezeného procesu,
- scheduler: postupně pouští pakety z front podle tokenů.

Měření rychlosti (TrafficStats.add) se dělá v okamžiku, kdy paket skutečně
odchází zpět do síťového stacku, takže se nic nepočítá dvakrát a čísla
odpovídají i omezenému provozu.
"""

from __future__ import annotations

import collections
import logging
import threading
import time

import pydivert

from monitor import DOWN, UNKNOWN_PID, UP, PortMapper, TrafficStats

log = logging.getLogger(__name__)

# Jen TCP a UDP, loopback (127.0.0.1, ::1, komunikace v rámci stroje) ignorujeme.
WINDIVERT_FILTER = "(tcp or udp) and not loopback"

KB = 1024

RECV_TIMEOUT = 0.25  # s – jak rychle si capture vlákno všimne požadavku na ukončení
MAX_QUEUE_TIME = 1.0  # s – fronta pojme nanejvýš ~1 s provozu při daném limitu
MIN_QUEUE_BYTES = 64 * KB
MAX_QUEUE_PACKETS = 4000
BURST_TIME = 0.1  # s – velikost "kbelíku" (povolený krátký nárůst)
MIN_BURST = 6000  # B – aspoň pár paketů o velikosti MTU


class TokenBucket:
    """Klasický token bucket. Tokeny smí jít do mínusu (dluh), takže i paket
    větší než kbelík (LSO/GRO) projde a průměrná rychlost zůstane přesná."""

    def __init__(self, rate: float):
        self.rate = 0.0
        self.capacity = 0.0
        self.set_rate(rate)
        self.tokens = self.capacity
        self.last = time.monotonic()

    def set_rate(self, rate: float) -> None:
        self.rate = float(rate)
        self.capacity = max(self.rate * BURST_TIME, MIN_BURST)

    def refill(self, now: float) -> None:
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now

    def time_until_positive(self) -> float:
        return 0.0 if self.tokens > 0 else (-self.tokens) / self.rate + 1e-4


class Throttle:
    """Limit + fronta pro jeden PID a jeden směr."""

    def __init__(self, rate: float):
        self.bucket = TokenBucket(rate)
        self.queue: collections.deque = collections.deque()
        self.queued_bytes = 0

    @property
    def max_queue_bytes(self) -> float:
        return max(self.bucket.rate * MAX_QUEUE_TIME, MIN_QUEUE_BYTES)


class CaptureEngine:
    def __init__(self, mapper: PortMapper, stats: TrafficStats):
        self.mapper = mapper
        self.stats = stats
        self._divert: pydivert.WinDivert | None = None
        # chrání _throttles a jejich fronty; scheduler na ní čeká
        self._cond = threading.Condition()
        self._throttles: dict[tuple[int, str], Throttle] = {}
        self._stop = threading.Event()
        self._stopped = False
        self._stop_lock = threading.Lock()
        self._capture_thread = threading.Thread(target=self._capture_loop, name="capture", daemon=True)
        self._sched_thread = threading.Thread(target=self._scheduler_loop, name="scheduler", daemon=True)

    # ------------------------------------------------------------ životní cyklus
    def start(self) -> None:
        self._divert = pydivert.WinDivert(WINDIVERT_FILTER)
        self._divert.open()
        self._capture_thread.start()
        self._sched_thread.start()

    def stop(self) -> None:
        """Idempotentní. Zastaví zachytávání, vypustí fronty a zavře handle."""
        with self._stop_lock:
            if self._stopped:
                return
            self._stopped = True
        self._stop.set()
        if self._capture_thread.is_alive() and threading.current_thread() is not self._capture_thread:
            self._capture_thread.join(timeout=2)
        # vše, co čeká ve frontách, pošleme dál – nic se nesmí ztratit/zaseknout
        with self._cond:
            flushed = 0
            for (pid, direction), thr in self._throttles.items():
                flushed += self._flush(pid, direction, thr)
            self._throttles.clear()
            self._cond.notify_all()
        if self._sched_thread.is_alive():
            self._sched_thread.join(timeout=2)
        if self._divert is not None and self._divert.is_open:
            try:
                self._divert.close()
            except Exception:  # pragma: no cover
                log.exception("Zavření WinDivert handle selhalo")
        log.info("WinDivert zavřen, z front vypuštěno %d paketů", flushed)

    # ------------------------------------------------------------------ limity
    def set_limit(self, pid: int, down_bps: float | None, up_bps: float | None) -> None:
        """Nastaví limity v bajtech za sekundu. None = daný směr neomezovat."""
        with self._cond:
            for direction, bps in ((DOWN, down_bps), (UP, up_bps)):
                key = (pid, direction)
                thr = self._throttles.get(key)
                if bps is None or bps <= 0:
                    if thr is not None:
                        self._flush(pid, direction, thr)
                        del self._throttles[key]
                elif thr is None:
                    self._throttles[key] = Throttle(bps)
                else:
                    thr.bucket.set_rate(bps)
            self._cond.notify_all()

    def clear_limit(self, pid: int) -> None:
        self.set_limit(pid, None, None)

    def get_limits(self) -> dict[int, dict[str, float]]:
        """{pid: {"down": B/s, "up": B/s}} – jen nastavené směry."""
        with self._cond:
            out: dict[int, dict[str, float]] = {}
            for (pid, direction), thr in self._throttles.items():
                out.setdefault(pid, {})[direction] = thr.bucket.rate
            return out

    def queue_sizes(self) -> dict[tuple[int, str], int]:
        with self._cond:
            return {k: t.queued_bytes for k, t in self._throttles.items()}

    # ----------------------------------------------------------------- vlákna
    def _send(self, packet, pid: int, direction: str) -> None:
        try:
            self._divert.send(packet)
        except Exception as e:  # handle zavřen / chybný paket – nesmí shodit vlákno
            log.debug("send selhal: %s", e)
            return
        self.stats.add(pid, direction, len(packet.raw))

    def _flush(self, pid: int, direction: str, thr: Throttle) -> int:
        """Pošle celou frontu hned (volat se zámkem _cond)."""
        n = len(thr.queue)
        while thr.queue:
            self._send(thr.queue.popleft(), pid, direction)
        thr.queued_bytes = 0
        return n

    def _classify(self, packet) -> tuple[int, str]:
        if packet.is_outbound:
            direction, port = UP, packet.src_port
        else:
            direction, port = DOWN, packet.dst_port
        proto = "tcp" if packet.tcp is not None else "udp"
        pid = self.mapper.lookup(proto, port) if port is not None else None
        return (pid if pid is not None else UNKNOWN_PID), direction

    def _capture_loop(self) -> None:
        divert = self._divert
        while not self._stop.is_set():
            try:
                packet = divert.recv(timeout=RECV_TIMEOUT)
            except TimeoutError:
                continue
            except Exception as e:
                if self._stop.is_set():
                    break
                log.warning("recv selhal: %s", e)
                time.sleep(0.01)
                continue

            pid, direction = self._classify(packet)
            size = len(packet.raw)
            key = (pid, direction)

            # rychlá cesta bez zámku: proces nemá limit
            if key not in self._throttles:
                self._send(packet, pid, direction)
                continue

            with self._cond:
                thr = self._throttles.get(key)
                if thr is None:  # limit mezitím zrušen
                    self._send(packet, pid, direction)
                    continue
                thr.bucket.refill(time.monotonic())
                if not thr.queue and thr.bucket.tokens > 0:
                    thr.bucket.tokens -= size
                    self._send(packet, pid, direction)
                elif (thr.queued_bytes + size > thr.max_queue_bytes
                      or len(thr.queue) >= MAX_QUEUE_PACKETS):
                    self.stats.add_drop(pid)  # fronta plná -> zahodit (TCP zpomalí)
                else:
                    thr.queue.append(packet)
                    thr.queued_bytes += size
                    self._cond.notify()

    def _scheduler_loop(self) -> None:
        with self._cond:
            while not self._stop.is_set():
                now = time.monotonic()
                wait: float | None = None
                for (pid, direction), thr in self._throttles.items():
                    if not thr.queue:
                        continue
                    b = thr.bucket
                    b.refill(now)
                    while thr.queue and b.tokens > 0:
                        pkt = thr.queue.popleft()
                        size = len(pkt.raw)
                        thr.queued_bytes -= size
                        b.tokens -= size
                        self._send(pkt, pid, direction)
                    if thr.queue:
                        t = b.time_until_positive()
                        wait = t if wait is None else min(wait, t)
                # bez front spíme, dokud nás capture vlákno nevzbudí
                self._cond.wait(timeout=None if wait is None else max(wait, 0.001))
