"""
POST /settle

Verifikation + On-Chain Settlement in einem Schritt:
1. Alle /verify Prüfungen (ohne erneuten HTTP-Call)
2. Nonce als verwendet markieren (Replay-Schutz vor On-Chain)
3. transferWithAuthorization via CDP (Buyer → Facilitator)
4. 97% an Seller weiterleiten (Facilitator → Seller)
5. Receipt zurückgeben
"""

import logging

from fastapi import APIRouter, HTTPException

from src.models.payment import SettleRequest, SettleResponse
from src.routes.verify import verify
from src.models.payment import VerifyRequest
from src.services.nonce_store import mark_nonce_used
from src.services.cdp import settle_payment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/settle", response_model=SettleResponse)
async def settle(req: SettleRequest) -> SettleResponse:
    auth = req.payment.payload.authorization

    # --- Schritt 1: Vollständige Verifikation ---
    verify_result = await verify(
        VerifyRequest(
            payment=req.payment,
            paymentRequirements=req.paymentRequirements,
        )
    )

    if not verify_result.isValid:
        return SettleResponse(
            success=False,
            error=verify_result.invalidReason,
        )

    # --- Schritt 2: Nonce sofort sperren (vor On-Chain, verhindert Race Conditions) ---
    mark_nonce_used(auth.from_, auth.nonce)

    # --- Schritt 3 & 4: On-Chain Settlement via CDP ---
    try:
        result = await settle_payment(
            authorization={
                "from_":       auth.from_,
                "to":          auth.to,
                "value":       auth.value,
                "validAfter":  auth.validAfter,
                "validBefore": auth.validBefore,
                "nonce":       auth.nonce,
                "signature":   req.payment.payload.signature,
            },
            seller_address=req.sellerAddress,
            network=req.payment.network,
        )
    except Exception as e:
        logger.exception("Settlement fehlgeschlagen für payer=%s", auth.from_)
        # Nonce bleibt gesperrt — bei echtem Fehler manuell prüfen
        return SettleResponse(
            success=False,
            error=f"On-Chain Settlement fehlgeschlagen: {e}",
        )

    logger.info(
        "Settlement erfolgreich: payer=%s, seller=%s, gross=%.6f USDC, fee=%.6f USDC",
        auth.from_,
        req.sellerAddress,
        result.gross_amount,
        result.fee_amount,
    )

    return SettleResponse(
        success=True,
        txHash=result.intake_tx_hash,
        transferTxHash=result.transfer_tx_hash,
        network=req.payment.network,
        payer=auth.from_,
        seller=req.sellerAddress,
        grossAmount=str(result.gross_amount),
        sellerAmount=str(result.seller_amount),
        feeAmount=str(result.fee_amount),
    )
