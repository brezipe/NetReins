"""Škrcení s falešným WinDivertem (bez ovladače a bez práv správce)."""

import threading
import time

import pytest

import capture
from monitor import DOWN, UP, TrafficStats

PID = 1234
PORT = 5555
PACKET = 1460


class FakePacket:
    def __init__(self, outbound=False):
        self.raw = bytearray(PACKET)
        self.is_outbound = outbound
        self.src_port = PORT if outbound else 443
        self.dst_port = 443 if outbound else PORT
        self.tcp = object()


class FakeDivert:
    """Nabízí ~2,9 MB/s příchozích paketů a počítá odeslané bajty."""

    is_open = True

    def __init__(self):
        self.sent_bytes = 0
        self.lock = threading.Lock()

    def recv(self, timeout=None):
        time.sleep(0.0005)
        return FakePacket()

    def send(self, packet):
        with self.lock:
            self.sent_bytes += len(packet.raw)

    def close(self):
        self.is_open = False


class FakeMapper:
    def lookup(self, proto, port):
        return PID if port == PORT else None


@pytest.fixture
def engine():
    stats = TrafficStats()
    eng = capture.CaptureEngine(FakeMapper(), stats)
    eng._divert = FakeDivert()
    eng._capture_thread.start()
    eng._sched_thread.start()
    yield eng, stats
    eng.stop()


def measure(stats, seconds):
    stats.sample()
    time.sleep(seconds)
    return stats.sample()[PID].down


def test_unlimited_traffic_passes(engine):
    _eng, stats = engine
    assert measure(stats, 1.0) > 1_000_000


def test_download_limit_is_respected(engine):
    eng, stats = engine
    eng.set_limit(PID, 200_000, None)
    time.sleep(1.0)  # vyprázdnit počáteční "kbelík"
    rate = measure(stats, 2.0)
    assert 180_000 < rate < 220_000


def test_limits_are_reported_in_bytes_per_second(engine):
    eng, _stats = engine
    eng.set_limit(PID, 1_000_000, 62_500)
    assert eng.get_limits() == {PID: {DOWN: 1_000_000, UP: 62_500}}
    eng.set_limit(PID, None, 62_500)  # zrušit jen download
    assert eng.get_limits() == {PID: {UP: 62_500}}
    eng.clear_limit(PID)
    assert eng.get_limits() == {}


def test_full_queue_drops_packets(engine):
    eng, stats = engine
    eng.set_limit(PID, 50_000, None)
    time.sleep(1.5)
    assert stats.sample()[PID].dropped > 0


def test_stop_flushes_queue_and_closes_handle(engine):
    eng, _stats = engine
    eng.set_limit(PID, 50_000, None)
    time.sleep(1.0)
    assert sum(eng.queue_sizes().values()) > 0
    eng.stop()
    assert eng._divert.is_open is False
    assert eng.get_limits() == {}
    assert not eng._capture_thread.is_alive()
    assert not eng._sched_thread.is_alive()


def test_token_bucket_allows_debt_for_large_packets():
    bucket = capture.TokenBucket(10_000)
    bucket.tokens -= 64_000  # paket větší než kbelík (LSO)
    assert bucket.time_until_positive() == pytest.approx((64_000 - bucket.capacity) / 10_000, rel=0.01)
