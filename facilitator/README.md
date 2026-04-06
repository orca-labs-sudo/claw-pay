# claw-pay Facilitator — Integration Guide for Sellers

> Accept autonomous micropayments from AI agents. No registration. No monthly fee. Just point your x402 middleware here.

---

## How it works in 60 seconds

Your API returns HTTP 402. The agent pays. You get your money. That's it.

```
Agent hits your API
  → you return 402 with payment requirements
  → agent signs a gasless USDC authorization
  → claw-pay verifies + settles on Base L2
  → 97% lands in your wallet (~2 seconds)
  → agent retries → gets access
```

No webhooks. No accounts. No KYC. No waiting.

---

## Our fee — let's be upfront about it 😊

**We charge 3% of each settled payment.**

Here's what that 3% actually covers:

| Cost | Per transaction |
|---|---|
| Base L2 gas (2 transactions) | ~$0.0006 |
| Coinbase CDP infrastructure | ~$0.001 |
| Server (VPS, uptime, SSL) | ~$0.0001 |
| **Total cost to us** | **~$0.0017** |

At a $0.01 micropayment: our 3% = $0.0003 — we don't even break even.
At a $0.10 payment: our 3% = $0.003 — barely covering costs.
At a $1.00 payment: our 3% = $0.03 — finally a tiny margin.

We're not getting rich here. We're here to make the x402 ecosystem work.
The fee exists so the infrastructure stays running, not to extract value from you.

---

## Integration — 3 lines of code

### Python / FastAPI

```python
from x402.fastapi import X402Middleware

app.add_middleware(
    X402Middleware,
    pay_to="0xYourWalletAddress",
    facilitator_url="https://pay.orca-labs.xyz",
    amount=0.01,          # USD — minimum $0.001
    asset="USDC",
    network="base-mainnet",
)
```

### Node.js / Express

```javascript
const { x402Express } = require('x402-express');

app.use(x402Express({
    payTo: '0xYourWalletAddress',
    facilitatorUrl: 'https://pay.orca-labs.xyz',
    amount: '0.01',
    asset: 'USDC',
    network: 'base-mainnet',
}));
```

### Node.js / Next.js (API Routes)

```javascript
import { x402Next } from 'x402-next';

export default x402Next({
    payTo: '0xYourWalletAddress',
    facilitatorUrl: 'https://pay.orca-labs.xyz',
    amount: '0.005',
});
```

### Manual (any language)

Your server receives an `X-PAYMENT` header. Verify it before serving content:

```bash
curl -X POST https://pay.orca-labs.xyz/verify \
  -H "Content-Type: application/json" \
  -d '{
    "payment_payload": { ... },
    "payment_requirements": {
      "scheme": "exact",
      "network": "base-mainnet",
      "maxAmountRequired": "10000",
      "payTo": "0xYourWallet",
      "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    }
  }'
```

Response: `{ "is_valid": true, "payer": "0x..." }`

---

## Your wallet

You need a Base L2 wallet address to receive payments. Options:

- **Coinbase** — easiest, free account, Base L2 supported natively
- **MetaMask** — add Base L2 network (chainId: 8453)
- **Any EVM wallet** — Base is EVM-compatible

That's your `payTo` address. Funds arrive there directly from our facilitator after each settled payment.

---

## Pricing your API

| Use case | Suggested price | Agent cost |
|---|---|---|
| Single LLM call | $0.001 – $0.005 | Negligible |
| Image generation | $0.01 – $0.05 | ~coffee fraction |
| Research query | $0.005 – $0.02 | Trivial |
| Data export | $0.10 – $1.00 | Still affordable |

Agents don't negotiate. They pay or they don't call you. Price for value, not psychology.

---

## Test on Sepolia first

Before going live, test with our Base Sepolia endpoint:

```
facilitatorUrl: "https://pay.orca-labs.xyz"   ← same URL, detects network automatically
network: "base-sepolia"
```

Get free test USDC:
- [Coinbase Base Sepolia Faucet](https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet) — for ETH
- [Circle Faucet](https://faucet.circle.com) — for test USDC

---

## API Reference

### `POST /verify`

Validate a payment without settling. Use this to gate access before heavy computation.

**Request:**
```json
{
  "payment_payload": {
    "x402Version": 1,
    "scheme": "exact",
    "network": "base-mainnet",
    "payload": {
      "signature": "0x...",
      "authorization": {
        "from": "0xBuyerAddress",
        "to": "0xFacilitatorAddress",
        "value": "0x2710",
        "validAfter": "0x0",
        "validBefore": "0x...",
        "nonce": "0x..."
      }
    }
  },
  "payment_requirements": {
    "scheme": "exact",
    "network": "base-mainnet",
    "maxAmountRequired": "10000",
    "payTo": "0xYourWalletAddress",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
  }
}
```

**Response:**
```json
{ "is_valid": true, "payer": "0xBuyerAddress" }
```

---

### `POST /settle`

Verify + settle on-chain in one call. 97% → your wallet, 3% → infrastructure.

Same request format as `/verify`. Response:

```json
{
  "success": true,
  "txHash": "0x...",
  "transferTxHash": "0x...",
  "grossAmount": "0.010000",
  "sellerAmount": "0.009700",
  "feeAmount": "0.000300"
}
```

All transactions are publicly verifiable on [BaseScan](https://basescan.org).

---

### `GET /health`

```json
{ "status": "ok", "network": "base-mainnet", "version": "1.0.0" }
```

---

## Reliability & Security

- **Uptime:** Hosted on dedicated VPS with nginx + SSL
- **No custody:** We settle and forward immediately — we never hold your funds longer than one block (~2 seconds)
- **Replay protection:** Every nonce is tracked — double-spend impossible
- **Open source:** Audit our code at [github.com/orca-labs-sudo/claw-pay](https://github.com/orca-labs-sudo/claw-pay)
- **On-chain proof:** Every settlement is a public blockchain transaction

---

## Disclaimer

claw-pay is a technical settlement relay, not a financial service or payment institution.

- We do not hold, custody, or control seller funds. Settlement is immediate and automatic.
- Sellers receive payments directly to their own wallet address.
- The brief transit of funds during on-chain settlement does not constitute a money transmission service.
- Sellers are solely responsible for compliance with applicable laws in their jurisdiction regarding cryptocurrency payments.
- claw-pay makes no guarantees regarding uptime, transaction finality, or regulatory status in any jurisdiction.

---

## Questions?

Open an issue: [github.com/orca-labs-sudo/claw-pay/issues](https://github.com/orca-labs-sudo/claw-pay/issues)
