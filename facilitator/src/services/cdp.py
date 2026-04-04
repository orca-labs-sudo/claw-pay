"""
Coinbase CDP SDK v2 Wrapper.

Verantwortlich für:
- transferWithAuthorization (Buyer → Facilitator, Buyer zahlt kein Gas)
- USDC Transfer (Facilitator → Seller, 97%)

Konfiguration via Umgebungsvariablen:
    CDP_API_KEY_ID       — API Key ID aus CDP Dashboard
    CDP_API_KEY_SECRET   — API Key Secret
    CDP_WALLET_SECRET    — Wallet Secret (kontrolliert alle Accounts)
    FACILITATOR_ADDRESS  — EVM Adresse des Facilitator-Accounts

Docs: https://docs.cdp.coinbase.com/server-wallets/v2/introduction/accounts
"""

import os
import logging
from decimal import Decimal
from typing import NamedTuple

from cdp import CdpClient
from cdp.evm_transaction_types import TransactionRequestEIP1559
from eth_abi import encode
from web3 import Web3

logger = logging.getLogger(__name__)

# USDC Contract-Adressen
USDC_CONTRACTS = {
    "base-mainnet": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "base-sepolia": os.getenv("TEST_USDC_ADDRESS", "0x036cbd53842c5426634e7929541ec2318f3dcf7e"),
}

# ERC-20 transfer(address,uint256) Selector
ERC20_TRANSFER_SELECTOR = bytes.fromhex("a9059cbb")

# ERC-3009 transferWithAuthorization(...) Selector
TRANSFER_WITH_AUTH_SELECTOR = bytes.fromhex("e3ee160e")

USDC_DECIMALS = 6
PROVISION_PERCENT = Decimal(os.getenv("PROVISION_PERCENT", "3"))


class SettlementResult(NamedTuple):
    intake_tx_hash: str    # Buyer → Facilitator
    transfer_tx_hash: str  # Facilitator → Seller
    gross_amount: Decimal  # USDC gesamt
    seller_amount: Decimal  # 97%
    fee_amount: Decimal     # 3%


def _base_units_to_usdc(value: int) -> Decimal:
    return Decimal(value) / Decimal(10 ** USDC_DECIMALS)


def _usdc_to_base_units(amount: Decimal) -> int:
    return int(amount * Decimal(10 ** USDC_DECIMALS))


def _encode_transfer_with_authorization(
    from_addr: str,
    to_addr: str,
    value: int,
    valid_after: int,
    valid_before: int,
    nonce: bytes,
    v: int,
    r: bytes,
    s: bytes,
) -> bytes:
    """ABI-kodierter Calldata für USDC transferWithAuthorization."""
    encoded_params = encode(
        ["address", "address", "uint256", "uint256", "uint256", "bytes32", "uint8", "bytes32", "bytes32"],
        [
            Web3.to_checksum_address(from_addr),
            Web3.to_checksum_address(to_addr),
            value,
            valid_after,
            valid_before,
            nonce,
            v,
            r,
            s,
        ],
    )
    return TRANSFER_WITH_AUTH_SELECTOR + encoded_params


def _encode_erc20_transfer(to_addr: str, amount: int) -> bytes:
    """ABI-kodierter Calldata für ERC-20 transfer(address,uint256)."""
    encoded_params = encode(
        ["address", "uint256"],
        [Web3.to_checksum_address(to_addr), amount],
    )
    return ERC20_TRANSFER_SELECTOR + encoded_params


def _split_signature(signature_hex: str) -> tuple[int, bytes, bytes]:
    """ECDSA-Signatur in v, r, s zerlegen."""
    sig = bytes.fromhex(signature_hex.removeprefix("0x"))
    r = sig[:32]
    s = sig[32:64]
    v = sig[64]
    if v < 27:
        v += 27
    return v, r, s


async def settle_payment(
    authorization: dict,
    seller_address: str,
    network: str,
) -> SettlementResult:
    """
    Zahlung abwickeln:
    1. transferWithAuthorization → USDC Buyer → Facilitator (via CDP)
    2. ERC-20 transfer → 97% Facilitator → Seller (via CDP)

    CDP v2: Kein Seed-File, kein Wallet-Import.
    Private Keys bleiben in CDP's TEE — wir sehen sie nie.
    """
    facilitator_address = Web3.to_checksum_address(os.environ["FACILITATOR_ADDRESS"])
    usdc_address = Web3.to_checksum_address(USDC_CONTRACTS[network])

    # Beträge berechnen
    gross_value = int(authorization["value"], 16)
    gross_usdc = _base_units_to_usdc(gross_value)
    fee_usdc = (gross_usdc * PROVISION_PERCENT / 100).quantize(Decimal("0.000001"))
    seller_usdc = gross_usdc - fee_usdc
    seller_value = _usdc_to_base_units(seller_usdc)

    logger.info(
        "Settlement: gross=%.6f USDC, seller=%.6f USDC, fee=%.6f USDC",
        gross_usdc, seller_usdc, fee_usdc,
    )

    # Signatur zerlegen
    v, r, s = _split_signature(authorization["signature"])
    nonce_bytes = bytes.fromhex(authorization["nonce"].removeprefix("0x"))

    async with CdpClient() as cdp:

        # Schritt 1: transferWithAuthorization (Buyer → Facilitator)
        calldata_intake = _encode_transfer_with_authorization(
            from_addr=authorization["from_"],
            to_addr=authorization["to"],
            value=gross_value,
            valid_after=int(authorization["validAfter"], 16),
            valid_before=int(authorization["validBefore"], 16),
            nonce=nonce_bytes,
            v=v,
            r=r,
            s=s,
        )

        intake_tx_hash = await cdp.evm.send_transaction(
            address=facilitator_address,
            transaction=TransactionRequestEIP1559(
                to=usdc_address,
                data="0x" + calldata_intake.hex(),
                value=0,
            ),
            network=network,
        )
        logger.info("Intake Tx: %s", intake_tx_hash)

        # Schritt 2: 97% an Seller (Facilitator → Seller)
        calldata_transfer = _encode_erc20_transfer(seller_address, seller_value)

        transfer_tx_hash = await cdp.evm.send_transaction(
            address=facilitator_address,
            transaction=TransactionRequestEIP1559(
                to=usdc_address,
                data="0x" + calldata_transfer.hex(),
                value=0,
            ),
            network=network,
        )
        logger.info("Transfer Tx: %s", transfer_tx_hash)

    return SettlementResult(
        intake_tx_hash=intake_tx_hash,
        transfer_tx_hash=transfer_tx_hash,
        gross_amount=gross_usdc,
        seller_amount=seller_usdc,
        fee_amount=fee_usdc,
    )
