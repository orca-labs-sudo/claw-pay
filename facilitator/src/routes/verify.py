"""
POST /verify

Validiert ein x402 Payment Payload ohne es on-chain einzureichen.
Wird vom Seller-Server aufgerufen bevor er /settle triggert.

Prüfungen:
1. x402Version == 1
2. scheme == "exact", network bekannt
3. authorization.to == facilitator payTo-Adresse
4. authorization.value >= maxAmountRequired
5. validBefore > jetzt (nicht abgelaufen)
6. validAfter <= jetzt (bereits aktiv)
7. ERC-3009 / EIP-712 Signatur gültig
8. Nonce noch nicht verwendet (Replay-Schutz)
"""

import os
import time
import logging
from functools import lru_cache
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

from fastapi import APIRouter
from src.models.payment import VerifyRequest, VerifyResponse
from src.services.nonce_store import is_nonce_used

RPC_URLS = {
    "base-mainnet": "https://mainnet.base.org",
    "base-sepolia": "https://sepolia.base.org",
}

NAME_ABI = [{"name": "name", "type": "function", "inputs": [], "outputs": [{"name": "", "type": "string"}], "stateMutability": "view"}]


@lru_cache(maxsize=10)
def _get_token_name(network: str, contract_address: str) -> str:
    """Token-Namen direkt vom Contract lesen (gecacht)."""
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URLS[network]))
        c = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=NAME_ABI)
        return c.functions.name().call()
    except Exception:
        return "USD Coin"  # Fallback für Mainnet USDC

logger = logging.getLogger(__name__)
router = APIRouter()

# Chain IDs
CHAIN_IDS = {
    "base-mainnet": 8453,
    "base-sepolia": 84532,
}

# USDC Contract-Adressen (für EIP-712 Domain)
USDC_CONTRACTS = {
    "base-mainnet": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "base-sepolia": os.getenv("TEST_USDC_ADDRESS", "0x036cbd53842c5426634e7929541ec2318f3dcf7e"),
}

# EIP-712 Typen für ERC-3009
EIP712_TYPES = {
    "TransferWithAuthorization": [
        {"name": "from",        "type": "address"},
        {"name": "to",          "type": "address"},
        {"name": "value",       "type": "uint256"},
        {"name": "validAfter",  "type": "uint256"},
        {"name": "validBefore", "type": "uint256"},
        {"name": "nonce",       "type": "bytes32"},
    ]
}


def _verify_signature(payment, network: str) -> tuple[bool, str]:
    """
    EIP-712 Signatur gegen den angegebenen 'from'-Signer prüfen.
    Gibt (True, "") oder (False, Fehlermeldung) zurück.
    """
    auth = payment.payload.authorization
    chain_id = CHAIN_IDS[network]
    usdc_address = USDC_CONTRACTS[network]

    structured_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name",              "type": "string"},
                {"name": "version",           "type": "string"},
                {"name": "chainId",           "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            **EIP712_TYPES,
        },
        "domain": {
            "name":              _get_token_name(network, usdc_address),
            "version":           "2",
            "chainId":           chain_id,
            "verifyingContract": usdc_address,
        },
        "primaryType": "TransferWithAuthorization",
        "message": {
            "from":        auth.from_,
            "to":          auth.to,
            "value":       int(auth.value, 16),
            "validAfter":  int(auth.validAfter, 16),
            "validBefore": int(auth.validBefore, 16),
            "nonce":       bytes.fromhex(auth.nonce.removeprefix("0x")),
        },
    }

    try:
        encoded = encode_typed_data(full_message=structured_data)
        recovered = Account.recover_message(encoded, signature=payment.payload.signature)
        if recovered.lower() != auth.from_.lower():
            return False, f"Signatur-Mismatch: erwartet {auth.from_}, erhalten {recovered}"
        return True, ""
    except Exception as e:
        return False, f"Signatur-Verifikation fehlgeschlagen: {e}"


@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest) -> VerifyResponse:
    payment = req.payment
    requirements = req.paymentRequirements
    auth = payment.payload.authorization
    now = int(time.time())

    # 1. Version
    if payment.x402Version != 1:
        return VerifyResponse(isValid=False, invalidReason=f"Unbekannte x402Version: {payment.x402Version}")

    # 2. Netzwerk-Konsistenz
    if payment.network != requirements.network:
        return VerifyResponse(
            isValid=False,
            invalidReason=f"Netzwerk-Konflikt: Payment={payment.network}, Requirements={requirements.network}",
        )

    # 3. Facilitator-Adresse stimmt überein
    facilitator_address = os.environ.get("FACILITATOR_ADDRESS", "").lower()
    if facilitator_address and auth.to != facilitator_address:
        return VerifyResponse(
            isValid=False,
            invalidReason=f"Falsche Zieladresse: erwartet {facilitator_address}, erhalten {auth.to}",
        )

    # 4. Betrag ausreichend
    required = int(requirements.maxAmountRequired, 16)
    paid = int(auth.value, 16)
    if paid < required:
        return VerifyResponse(
            isValid=False,
            invalidReason=f"Betrag zu niedrig: {paid} < {required} (USDC base units)",
        )

    # 5. Zeitfenster: validBefore > jetzt
    valid_before = int(auth.validBefore, 16)
    if now >= valid_before:
        return VerifyResponse(isValid=False, invalidReason="Payment abgelaufen (validBefore überschritten)")

    # 6. Zeitfenster: validAfter <= jetzt
    valid_after = int(auth.validAfter, 16)
    if now < valid_after:
        return VerifyResponse(isValid=False, invalidReason="Payment noch nicht aktiv (validAfter nicht erreicht)")

    # 7. Replay-Schutz: Nonce noch nicht verwendet
    if is_nonce_used(auth.from_, auth.nonce):
        return VerifyResponse(isValid=False, invalidReason="Nonce bereits verwendet (Replay-Angriff)")

    # 8. EIP-712 Signatur prüfen
    sig_valid, sig_error = _verify_signature(payment, payment.network)
    if not sig_valid:
        return VerifyResponse(isValid=False, invalidReason=sig_error)

    logger.info("Payment verifiziert: payer=%s, amount=%d", auth.from_, paid)
    return VerifyResponse(isValid=True, payer=auth.from_)
