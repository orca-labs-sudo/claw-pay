"""
Testclient — simuliert einen Buyer-Agenten der per x402 bezahlt.

Verwendung:
    python scripts/testclient.py

Voraussetzungen:
    - Facilitator läuft auf FACILITATOR_URL (default: http://localhost:8000)
    - BUYER_PRIVATE_KEY: Wallet mit USDC auf Base Sepolia
    - FACILITATOR_ADDRESS: Adresse des Facilitator-Wallets

Sepolia Faucets:
    USDC: https://faucet.circle.com  (Testnet USDC)
    ETH:  https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet
"""

import os
import sys
import time
import json
import secrets
import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# --- Konfiguration ---
FACILITATOR_URL    = os.getenv("FACILITATOR_URL", "http://localhost:8000")
BUYER_PRIVATE_KEY  = os.getenv("BUYER_PRIVATE_KEY")
FACILITATOR_ADDR   = os.getenv("FACILITATOR_ADDRESS")
SELLER_ADDR        = os.getenv("TEST_SELLER_ADDRESS")  # wohin 97% gehen sollen
NETWORK            = "base-sepolia"
CHAIN_ID           = 84532
USDC_SEPOLIA       = os.getenv("TEST_USDC_ADDRESS", "0x036cbd53842c5426634e7929541ec2318f3dcf7e")
AMOUNT_USDC        = 1_000_000  # 1.00 USDC (6 Dezimalstellen)


def _get_token_name(usdc_address: str) -> str:
    """Token-Namen vom Contract lesen."""
    try:
        w3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))
        abi = [{"name": "name", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "string"}], "stateMutability": "view"}]
        c = w3.eth.contract(address=Web3.to_checksum_address(usdc_address), abi=abi)
        return c.functions.name().call()
    except Exception:
        return "USD Coin"


def sign_transfer_authorization(
    from_addr: str,
    to_addr: str,
    value: int,
    valid_after: int,
    valid_before: int,
    nonce: bytes,
    private_key: str,
) -> str:
    token_name = _get_token_name(USDC_SEPOLIA)
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
            "name":              token_name,
            "version":           "2",
            "chainId":           CHAIN_ID,
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
    sig = signed.signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


def build_payment_payload(buyer_address: str, signature: str, nonce: bytes, now: int) -> dict:
    return {
        "x402Version": 1,
        "scheme": "exact",
        "network": NETWORK,
        "payload": {
            "signature": signature,
            "authorization": {
                "from_":       buyer_address,
                "to":          FACILITATOR_ADDR,
                "value":       hex(AMOUNT_USDC),
                "validAfter":  hex(0),
                "validBefore": hex(now + 300),
                "nonce":       "0x" + nonce.hex(),
            },
        },
    }


def build_payment_requirements() -> dict:
    return {
        "scheme":            "exact",
        "network":           NETWORK,
        "maxAmountRequired": hex(AMOUNT_USDC),
        "resource":          "https://example.com/api/testresource",
        "description":       "x402 Testclient Payment",
        "payTo":             FACILITATOR_ADDR,
        "maxTimeoutSeconds": 300,
        "asset":             USDC_SEPOLIA,
    }


def main():
    # Vorbedingungen prüfen
    missing = [k for k, v in {
        "BUYER_PRIVATE_KEY":  BUYER_PRIVATE_KEY,
        "FACILITATOR_ADDRESS": FACILITATOR_ADDR,
        "TEST_SELLER_ADDRESS": SELLER_ADDR,
    }.items() if not v]
    if missing:
        print(f"Fehler: fehlende Umgebungsvariablen: {', '.join(missing)}")
        print("Bitte in .env eintragen.")
        sys.exit(1)

    buyer = Account.from_key(BUYER_PRIVATE_KEY)
    buyer_address = buyer.address.lower()
    print(f"Buyer:       {buyer_address}")
    print(f"Facilitator: {FACILITATOR_ADDR}")
    print(f"Seller:      {SELLER_ADDR}")
    print(f"Betrag:      {AMOUNT_USDC / 1_000_000:.6f} USDC")
    print()

    now = int(time.time())
    nonce = secrets.token_bytes(32)

    # Signatur erstellen
    print("Signiere Zahlung...")
    signature = sign_transfer_authorization(
        from_addr=buyer_address,
        to_addr=FACILITATOR_ADDR,
        value=AMOUNT_USDC,
        valid_after=0,
        valid_before=now + 300,
        nonce=nonce,
        private_key=BUYER_PRIVATE_KEY,
    )
    print(f"Signatur: {signature[:20]}...{signature[-10:]}")
    print()

    payment = build_payment_payload(buyer_address, signature, nonce, now)
    requirements = build_payment_requirements()

    with httpx.Client(base_url=FACILITATOR_URL, timeout=30) as http:

        # --- /verify ---
        print("POST /verify ...")
        verify_resp = http.post("/verify", json={
            "payment": payment,
            "paymentRequirements": requirements,
        })
        verify_resp.raise_for_status()
        verify_data = verify_resp.json()
        print(f"Ergebnis: {json.dumps(verify_data, indent=2)}")
        print()

        if not verify_data["isValid"]:
            print(f"Verifikation fehlgeschlagen: {verify_data['invalidReason']}")
            sys.exit(1)

        # --- /settle ---
        print("POST /settle ...")
        settle_resp = http.post("/settle", json={
            "payment": payment,
            "paymentRequirements": requirements,
            "sellerAddress": SELLER_ADDR,
        })
        settle_resp.raise_for_status()
        settle_data = settle_resp.json()
        print(f"Ergebnis: {json.dumps(settle_data, indent=2)}")
        print()

        if settle_data["success"]:
            print("✓ Settlement erfolgreich!")
            print(f"  Intake Tx:   {settle_data.get('txHash')}")
            print(f"  Transfer Tx: {settle_data.get('transferTxHash')}")
            print(f"  Seller erhält: {settle_data.get('sellerAmount')} USDC")
            print(f"  Provision:     {settle_data.get('feeAmount')} USDC")
        else:
            print(f"✗ Settlement fehlgeschlagen: {settle_data.get('error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
