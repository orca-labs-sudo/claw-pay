"""
GET /demo/joke

A live x402-gated endpoint — costs $0.01 USDC per joke.
Demonstrates claw-pay end-to-end: 402 → payment → settle → content.
"""

import base64
import json
import logging
import os
import random
import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

FACILITATOR_ADDRESS = os.environ.get("FACILITATOR_ADDRESS", "")
NETWORK = os.environ.get("NETWORK_ID", "base-mainnet")
PRICE_USDC = 10_000  # $0.01 in USDC base units (6 decimals)

USDC_CONTRACTS = {
    "base-mainnet": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "base-sepolia": "0x036cbd53842c5426634e7929541ec2318f3dcf7e",
}

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
    "Why did the AI go to therapy? It had too many unresolved dependencies.",
    "How many programmers does it take to change a light bulb? None — that's a hardware problem.",
    "Why do Java developers wear glasses? Because they don't C#.",
    "An AI walks into a bar. The bartender asks: 'What'll it be?' The AI says: 'I'll have what the training data had.'",
    "Why did the neural network break up with the decision tree? It said: 'You never go deep enough.'",
    "What's a blockchain developer's favourite music? Crypto-funk.",
    "Why did the developer quit his job? He didn't get arrays.",
    "I told my AI assistant to 'think outside the box'. Now it won't stop hallucinating furniture.",
    "Why do agents never get lost? They always have a clear objective function.",
    "What did the USDC say to the ETH? 'Stop being so volatile.'",
    "A Base L2 transaction walks into a bar. Bartender: 'That'll be $0.0003.' Transaction: 'Keep the change.'",
    "Why did the x402 agent pay automatically? Because asking for permission defeats the purpose.",
    "What's an AI agent's favourite payment method? x402 — no questions asked, within limits.",
]


def _build_payment_required(resource_url: str) -> dict:
    return {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": NETWORK,
                "maxAmountRequired": hex(PRICE_USDC),
                "resource": resource_url,
                "description": "One premium AI joke — worth every cent.",
                "mimeType": "application/json",
                "payTo": FACILITATOR_ADDRESS,
                "maxTimeoutSeconds": 300,
                "asset": USDC_CONTRACTS.get(NETWORK, USDC_CONTRACTS["base-mainnet"]),
                "extra": {"name": "USD Coin", "version": "2"},
            }
        ],
        "error": "X402PaymentRequired",
    }


@router.get("/demo/joke")
async def demo_joke(request: Request):
    payment_header = request.headers.get("X-PAYMENT") or request.headers.get("PAYMENT-SIGNATURE")

    # No payment → return 402
    if not payment_header:
        resource_url = str(request.url)
        payload = _build_payment_required(resource_url)
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        return JSONResponse(
            status_code=402,
            content=payload,
            headers={"PAYMENT-REQUIRED": encoded},
        )

    # Payment present → verify + settle via our own facilitator
    try:
        payment_data = json.loads(base64.b64decode(payment_header).decode())
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid payment header encoding"})

    settle_url = "http://127.0.0.1:8000/settle"
    settle_body = {
        "payment": payment_data,
        "paymentRequirements": {
            "scheme": "exact",
            "network": NETWORK,
            "maxAmountRequired": hex(PRICE_USDC),
            "resource": str(request.url),
            "description": "One premium AI joke",
            "mimeType": "application/json",
            "payTo": FACILITATOR_ADDRESS,
            "maxTimeoutSeconds": 300,
            "asset": USDC_CONTRACTS.get(NETWORK, USDC_CONTRACTS["base-mainnet"]),
            "extra": {"name": "USD Coin", "version": "2"},
        },
        "sellerAddress": FACILITATOR_ADDRESS,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            settle_resp = await client.post(settle_url, json=settle_body)
            result = settle_resp.json()
    except Exception as e:
        logger.error("Settlement error: %s", e)
        return JSONResponse(status_code=502, content={"error": "Settlement failed"})

    if not result.get("success"):
        return JSONResponse(
            status_code=402,
            content={"error": "Payment settlement failed", "detail": result},
        )

    joke = random.choice(JOKES)
    logger.info("Demo joke sold — tx: %s", result.get("txHash", "?"))

    return JSONResponse(
        status_code=200,
        content={
            "joke": joke,
            "paid": f"${PRICE_USDC / 1_000_000:.4f} USDC",
            "txHash": result.get("txHash"),
            "network": NETWORK,
            "poweredBy": "claw-pay · https://clawpay.eu",
        },
        headers={
            "PAYMENT-RESPONSE": base64.b64encode(
                json.dumps({"success": True, "txHash": result.get("txHash", "")}).encode()
            ).decode()
        },
    )
