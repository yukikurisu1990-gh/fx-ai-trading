"""Network guard tripwire tests (plan §10)."""

from __future__ import annotations

import http.client
import socket
import urllib.request

import pytest

from scripts._gate_p1_inspector.guards import GuardViolationError
from scripts._gate_p1_inspector.guards import network as network_guard


def test_socket_blocked():
    with network_guard.activate(), pytest.raises(GuardViolationError):
        socket.socket()


def test_create_connection_blocked():
    with network_guard.activate(), pytest.raises(GuardViolationError):
        socket.create_connection(("127.0.0.1", 9))


def test_urlopen_blocked():
    with network_guard.activate(), pytest.raises(GuardViolationError):
        urllib.request.urlopen("http://127.0.0.1:9/")


def test_httpconnection_blocked():
    with network_guard.activate(), pytest.raises(GuardViolationError):
        http.client.HTTPConnection("127.0.0.1")


def test_network_restored_after_context():
    with network_guard.activate():
        pass
    # The original socket type is restored (constructing does not raise our guard).
    s = socket.socket()
    s.close()
