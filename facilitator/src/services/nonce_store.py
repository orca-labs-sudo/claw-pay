"""
In-Memory Nonce Store — Replay-Schutz.

Speichert verwendete (from_address, nonce) Paare.
Nach Neustart des Servers werden die Nonces zurückgesetzt — das ist für
den Hobby-Betrieb akzeptabel, da x402-Payments ein kurzes validBefore haben.

Für Produktion: Redis oder Postgres verwenden.
"""

from threading import Lock

_used: set[tuple[str, str]] = set()
_lock = Lock()


def is_nonce_used(from_address: str, nonce: str) -> bool:
    key = (from_address.lower(), nonce.lower())
    with _lock:
        return key in _used


def mark_nonce_used(from_address: str, nonce: str) -> None:
    key = (from_address.lower(), nonce.lower())
    with _lock:
        _used.add(key)
