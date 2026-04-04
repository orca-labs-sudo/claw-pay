"""
Unit Tests für POST /verify

Testet alle 8 Validierungsschritte ohne CDP-Aufrufe.
"""

import time
import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from src.services import nonce_store


@pytest.fixture(autouse=True)
def clear_nonce_store():
    """Nonce-Store vor jedem Test leeren — verhindert Test-Interferenz."""
    nonce_store._used.clear()
    yield
    nonce_store._used.clear()
from eth_account.messages import encode_typed_data

from src.main import app

client = TestClient(app)

# --- Test-Wallet (nur für Tests, niemals echtes Geld!) ---
TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
TEST_ACCOUNT = Account.from_key(TEST_PRIVATE_KEY)
BUYER_ADDRESS = TEST_ACCOUNT.address.lower()

FACILITATOR_ADDRESS = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"

USDC_SEPOLIA = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
CHAIN_ID_SEPOLIA = 84532


def _sign_authorization(
    from_addr: str,
    to_addr: str,
    value: int,
    valid_after: int,
    valid_before: int,
    nonce: bytes,
    private_key: str,
) -> str:
    """EIP-712 Signatur für ERC-3009 transferWithAuthorization erstellen."""
    structured_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name",              "type": "string"},
                {"name": "version",           "type": "string"},
                {"name": "chainId",           "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from",        "type": "address"},
                {"name": "to",          "type": "address"},
                {"name": "value",       "type": "uint256"},
                {"name": "validAfter",  "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce",       "type": "bytes32"},
            ],
        },
        "domain": {
            "name":              "USD Coin",
            "version":           "2",
            "chainId":           CHAIN_ID_SEPOLIA,
            "verifyingContract": USDC_SEPOLIA,
        },
        "primaryType": "TransferWithAuthorization",
        "message": {
            "from":        from_addr,
            "to":          to_addr,
            "value":       value,
            "validAfter":  valid_after,
            "validBefore": valid_before,
            "nonce":       nonce,
        },
    }
    encoded = encode_typed_data(full_message=structured_data)
    signed = Account.sign_message(encoded, private_key=private_key)
    return signed.signature.hex()


def _make_valid_payload(
    value: int = 1_000_000,  # 1 USDC
    nonce_hex: str | None = None,
    valid_after_offset: int = 0,
    valid_before_offset: int = 300,
    to: str = FACILITATOR_ADDRESS,
) -> dict:
    """Gültiges Testpayload bauen."""
    now = int(time.time())
    nonce = bytes.fromhex(nonce_hex or "abcd" * 8)  # 32 bytes
    signature = _sign_authorization(
        from_addr=BUYER_ADDRESS,
        to_addr=to,
        value=value,
        valid_after=now + valid_after_offset,
        valid_before=now + valid_before_offset,
        nonce=nonce,
        private_key=TEST_PRIVATE_KEY,
    )
    return {
        "payment": {
            "x402Version": 1,
            "scheme": "exact",
            "network": "base-sepolia",
            "payload": {
                "signature": signature if signature.startswith("0x") else "0x" + signature,
                "authorization": {
                    "from_":       BUYER_ADDRESS,
                    "to":          to,
                    "value":       hex(value),
                    "validAfter":  hex(now + valid_after_offset),
                    "validBefore": hex(now + valid_before_offset),
                    "nonce":       "0x" + nonce.hex(),
                },
            },
        },
        "paymentRequirements": {
            "scheme":             "exact",
            "network":            "base-sepolia",
            "maxAmountRequired":  hex(1_000_000),
            "resource":           "https://example.com/api/data",
            "payTo":              FACILITATOR_ADDRESS,
            "maxTimeoutSeconds":  300,
            "asset":              USDC_SEPOLIA,
        },
    }


# --- Tests ---

def test_verify_valid_payment(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    payload = _make_valid_payload()
    resp = client.post("/verify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["isValid"] is True
    assert data["payer"] == BUYER_ADDRESS


def test_verify_wrong_version(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    payload = _make_valid_payload()
    payload["payment"]["x402Version"] = 99
    resp = client.post("/verify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["isValid"] is False
    assert "x402Version" in data["invalidReason"]


def test_verify_expired_payment(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    payload = _make_valid_payload(valid_before_offset=-10)  # bereits abgelaufen
    resp = client.post("/verify", json=payload)
    assert resp.status_code == 200
    assert resp.json()["isValid"] is False
    assert "abgelaufen" in resp.json()["invalidReason"]


def test_verify_not_yet_active(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    payload = _make_valid_payload(valid_after_offset=9999)  # erst in der Zukunft
    resp = client.post("/verify", json=payload)
    assert resp.status_code == 200
    assert resp.json()["isValid"] is False
    assert "validAfter" in resp.json()["invalidReason"]


def test_verify_amount_too_low(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    payload = _make_valid_payload(value=500_000)  # 0.50 USDC < 1 USDC required
    resp = client.post("/verify", json=payload)
    assert resp.status_code == 200
    assert resp.json()["isValid"] is False
    assert "Betrag" in resp.json()["invalidReason"]


def test_verify_wrong_recipient(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    wrong_address = "0x" + "1" * 40
    payload = _make_valid_payload(to=wrong_address)
    resp = client.post("/verify", json=payload)
    assert resp.status_code == 200
    assert resp.json()["isValid"] is False
    assert "Zieladresse" in resp.json()["invalidReason"]


def test_verify_invalid_signature(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    payload = _make_valid_payload()
    # Signatur korrumpieren
    sig = payload["payment"]["payload"]["signature"]
    payload["payment"]["payload"]["signature"] = sig[:-4] + "dead"
    resp = client.post("/verify", json=payload)
    assert resp.status_code == 200
    assert resp.json()["isValid"] is False


def test_verify_replay_attack(monkeypatch):
    monkeypatch.setenv("FACILITATOR_ADDRESS", FACILITATOR_ADDRESS)
    nonce = "cafe" * 8
    payload = _make_valid_payload(nonce_hex=nonce)

    # Erste Anfrage — muss gültig sein
    resp1 = client.post("/verify", json=payload)
    assert resp1.json()["isValid"] is True

    # Nonce manuell als verwendet markieren (wie /settle es tut)
    from src.services.nonce_store import mark_nonce_used
    mark_nonce_used(BUYER_ADDRESS, "0x" + nonce)

    # Zweite Anfrage mit gleicher Nonce — muss abgelehnt werden
    resp2 = client.post("/verify", json=payload)
    assert resp2.json()["isValid"] is False
    assert "Nonce" in resp2.json()["invalidReason"]


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
