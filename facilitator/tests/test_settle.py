"""
Unit Tests für POST /settle

CDP-Aufrufe werden gemockt — kein echtes Testnet nötig.
"""

import time
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from eth_account import Account

from src.main import app
from tests.test_verify import (
    _make_valid_payload,
    _sign_authorization,
    BUYER_ADDRESS,
    FACILITATOR_ADDRESS,
    TEST_PRIVATE_KEY,
)

client = TestClient(app)

SELLER_ADDRESS = "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc"


def _make_settle_payload(**kwargs) -> dict:
    base = _make_valid_payload(**kwargs)
    base["sellerAddress"] = SELLER_ADDRESS
    return base


def _mock_settlement_result():
    from src.services.cdp import SettlementResult
    return SettlementResult(
        intake_tx_hash="0xabc123" + "0" * 58,
        transfer_tx_hash="0xdef456" + "0" * 58,
        gross_amount=Decimal("1.000000"),
        seller_amount=Decimal("0.970000"),
        fee_amount=Decimal("0.030000"),
    )


def test_settle_success(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)

    with patch("src.routes.settle.settle_payment", new_callable=AsyncMock) as mock_cdp:
        mock_cdp.return_value = _mock_settlement_result()
        payload = _make_settle_payload()
        resp = client.post("/settle", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["txHash"] is not None
    assert data["transferTxHash"] is not None
    assert data["seller"] == SELLER_ADDRESS
    assert data["feeAmount"] == "0.030000"
    assert data["sellerAmount"] == "0.970000"


def test_settle_invalid_payment_rejected(monkeypatch):
    """Settle muss abbrechen wenn Verifikation fehlschlägt."""
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)

    with patch("src.routes.settle.settle_payment", new_callable=AsyncMock) as mock_cdp:
        payload = _make_settle_payload(valid_before_offset=-10)  # abgelaufen
        resp = client.post("/settle", json=payload)
        mock_cdp.assert_not_called()  # CDP darf nicht aufgerufen werden

    assert resp.status_code == 200
    assert resp.json()["success"] is False


def test_settle_cdp_error_returns_failure(monkeypatch):
    """Bei CDP-Fehler gibt /settle success=False zurück (kein 500)."""
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)

    with patch("src.routes.settle.settle_payment", new_callable=AsyncMock) as mock_cdp:
        mock_cdp.side_effect = Exception("CDP nicht erreichbar")
        payload = _make_settle_payload(nonce_hex="1234" * 8)
        resp = client.post("/settle", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "CDP" in data["error"]


def test_settle_nonce_locked_after_failure(monkeypatch):
    """
    Nonce wird VOR CDP-Aufruf gesperrt.
    Nach Fehler: Replay mit gleicher Nonce muss abgelehnt werden.
    """
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    nonce = "feed" * 8

    with patch("src.routes.settle.settle_payment", new_callable=AsyncMock) as mock_cdp:
        mock_cdp.side_effect = Exception("Netzwerkfehler")
        payload = _make_settle_payload(nonce_hex=nonce)
        client.post("/settle", json=payload)

    # Nonce ist jetzt gesperrt — erneuter Versuch muss scheitern
    with patch("src.routes.settle.settle_payment", new_callable=AsyncMock) as mock_cdp2:
        payload2 = _make_settle_payload(nonce_hex=nonce)
        resp = client.post("/settle", json=payload2)
        mock_cdp2.assert_not_called()

    assert resp.json()["success"] is False
    assert "Nonce" in resp.json()["error"]
