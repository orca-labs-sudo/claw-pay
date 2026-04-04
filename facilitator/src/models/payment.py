import re
from typing import Optional
from pydantic import BaseModel, field_validator


HEX_RE = re.compile(r"^0x[0-9a-fA-F]+$")
ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


class ERC3009Authorization(BaseModel):
    """ERC-3009 transferWithAuthorization Parameter — vom Buyer signiert."""

    from_: str        # 'from' ist Python-Keyword
    to: str           # Facilitator-Adresse
    value: str        # hex, USDC base units (1 USDC = 1_000_000)
    validAfter: str   # hex Unix timestamp — gültig ab
    validBefore: str  # hex Unix timestamp — gültig bis
    nonce: str        # hex bytes32 — Replay-Schutz

    @field_validator("from_", "to", mode="before")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not ADDR_RE.match(v):
            raise ValueError(f"Ungültige Ethereum-Adresse: {v}")
        return v.lower()

    @field_validator("value", "validAfter", "validBefore", "nonce", mode="before")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        if not HEX_RE.match(v):
            raise ValueError(f"Erwartet Hex-Wert, erhalten: {v}")
        return v


class ExactPayload(BaseModel):
    """Inneres Payload für scheme='exact'."""

    signature: str
    authorization: ERC3009Authorization

    @field_validator("signature", mode="before")
    @classmethod
    def validate_signature(cls, v: str) -> str:
        # 0x + 65 Bytes = 132 Zeichen
        if not HEX_RE.match(v) or len(v) != 132:
            raise ValueError("Ungültige ECDSA-Signatur (65-Byte hex erwartet)")
        return v


class PaymentPayload(BaseModel):
    """x402 Payment Payload — wird base64-kodiert im X-PAYMENT Header übertragen."""

    x402Version: int = 1
    scheme: str       # "exact"
    network: str      # "base-mainnet" | "base-sepolia"
    payload: ExactPayload

    @field_validator("scheme")
    @classmethod
    def validate_scheme(cls, v: str) -> str:
        if v != "exact":
            raise ValueError(f"Unbekanntes Scheme '{v}' — nur 'exact' unterstützt")
        return v

    @field_validator("network")
    @classmethod
    def validate_network(cls, v: str) -> str:
        if v not in {"base-mainnet", "base-sepolia"}:
            raise ValueError(f"Unbekanntes Netzwerk: {v}")
        return v


class PaymentRequirements(BaseModel):
    """Payment Requirements aus der 402-Response des Sellers."""

    scheme: str = "exact"
    network: str
    maxAmountRequired: str  # hex, USDC base units
    resource: str           # URL des geschützten Endpunkts
    description: str = ""
    mimeType: str = ""
    payTo: str              # Facilitator-Wallet-Adresse
    maxTimeoutSeconds: int = 300
    asset: str              # USDC Contract-Adresse auf dem jeweiligen Netzwerk

    @field_validator("payTo", "asset", mode="before")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not ADDR_RE.match(v):
            raise ValueError(f"Ungültige Adresse: {v}")
        return v.lower()


# --- Request / Response Modelle ---

class VerifyRequest(BaseModel):
    payment: PaymentPayload
    paymentRequirements: PaymentRequirements


class VerifyResponse(BaseModel):
    isValid: bool
    invalidReason: Optional[str] = None
    payer: Optional[str] = None  # Buyer-Adresse (für Logging)


class SettleRequest(BaseModel):
    payment: PaymentPayload
    paymentRequirements: PaymentRequirements
    sellerAddress: str  # 97% gehen hierher

    @field_validator("sellerAddress", mode="before")
    @classmethod
    def validate_seller(cls, v: str) -> str:
        if not ADDR_RE.match(v):
            raise ValueError(f"Ungültige Seller-Adresse: {v}")
        return v.lower()


class SettleResponse(BaseModel):
    success: bool
    txHash: Optional[str] = None          # transferWithAuthorization Tx (Buyer→Facilitator)
    transferTxHash: Optional[str] = None  # Weiterleitung 97% Facilitator→Seller
    network: Optional[str] = None
    payer: Optional[str] = None
    seller: Optional[str] = None
    grossAmount: Optional[str] = None  # Gesamtbetrag in USDC
    sellerAmount: Optional[str] = None  # 97% in USDC
    feeAmount: Optional[str] = None     # 3% Provision in USDC
    error: Optional[str] = None
