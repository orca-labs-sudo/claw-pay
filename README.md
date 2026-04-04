# claw-pay

x402 payment facilitator for OpenClaw agents — autonomous, gasless payments on Base L2.

> Let your agent pay for itself.

---

## What it does

claw-pay is an [x402](https://x402.org) payment facilitator that enables AI agents to make autonomous micropayments in USDC on Base L2 — no ETH required, no human confirmation needed.

**How it works:**
1. Agent encounters a paywalled resource (HTTP 402)
2. Agent signs a gasless USDC payment authorization (ERC-3009)
3. claw-pay verifies the signature and settles on-chain
4. Agent gets access

**All transactions are publicly verifiable on-chain.**

---

## Architecture

```
[OpenClaw Agent]
    → hits paywall (HTTP 402)
    → signs payment (ERC-3009, gasless)
    → POST /verify  (claw-pay)
    → POST /settle  (claw-pay)
        → on-chain: USDC Buyer → Facilitator
        → on-chain: 97% USDC → Seller
    → gets access
```

**Stack:** Python FastAPI · Coinbase CDP SDK v2 · Base L2 · USDC

---

## API

### `POST /verify`
Validates a payment payload off-chain without settlement.

```json
{
  "payment": {
    "x402Version": 1,
    "scheme": "exact",
    "network": "base-mainnet",
    "payload": {
      "signature": "0x...",
      "authorization": {
        "from_": "0x...",
        "to": "0x...",
        "value": "0xf4240",
        "validAfter": "0x0",
        "validBefore": "0x...",
        "nonce": "0x..."
      }
    }
  },
  "paymentRequirements": {
    "network": "base-mainnet",
    "maxAmountRequired": "0xf4240",
    "payTo": "0x...",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
  }
}
```

**Response:** `{ "isValid": true, "payer": "0x..." }`

---

### `POST /settle`
Verify + settle on-chain in one call.

```json
{
  "payment": { ... },
  "paymentRequirements": { ... },
  "sellerAddress": "0x..."
}
```

**Response:**
```json
{
  "success": true,
  "txHash": "0x...",
  "transferTxHash": "0x...",
  "grossAmount": "1.000000",
  "sellerAmount": "0.970000",
  "feeAmount": "0.030000"
}
```

---

### `GET /health`
`{ "status": "ok" }`

---

## Setup

### 1. Coinbase CDP Account

1. Create account at [portal.cdp.coinbase.com](https://portal.cdp.coinbase.com)
2. **API Keys** → Create API Key (Ed25519)
3. **Server Wallets** → Create EVM EOA account on Base

### 2. Environment

```bash
cd facilitator
cp .env.example .env
```

Fill in `.env`:
```env
CDP_API_KEY_ID=your-api-key-id
CDP_API_KEY_SECRET=your-api-key-secret
CDP_WALLET_SECRET=your-wallet-secret
FACILITATOR_ADDRESS=0x...

NETWORK_ID=base-sepolia   # base-mainnet for production
PROVISION_PERCENT=3
PORT=8000
```

### 3. Install & Run

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# Development
uvicorn src.main:app --reload

# Production
docker compose up -d
```

### 4. Fund the facilitator wallet

The facilitator needs a small ETH balance on Base to pay gas (~$0.0003/tx).
Users only need USDC — no ETH required on their end.

**Testnet faucets:**
- ETH: [Coinbase Base Sepolia Faucet](https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet)
- USDC: [CDP Dashboard → Faucet](https://portal.cdp.coinbase.com)

---

## Tests

```bash
pip install pytest pytest-asyncio
pytest facilitator/tests/ -v
# 13/13 passing
```

---

## Project structure

```
facilitator/
├── src/
│   ├── main.py                 FastAPI app
│   ├── models/payment.py       x402 payload models
│   ├── routes/
│   │   ├── verify.py           POST /verify
│   │   └── settle.py           POST /settle
│   └── services/
│       ├── cdp.py              Coinbase CDP v2 wrapper
│       └── nonce_store.py      Replay protection
├── tests/
├── scripts/
│   ├── create_account.py       One-time: create facilitator wallet
│   └── testclient.py           End-to-end test on Base Sepolia
├── contracts/TestUSDC.sol      ERC-3009 test token
├── Dockerfile
└── docker-compose.yml
skill/                          OpenClaw skill (Phase 2)
```

---

## Security

- Private keys never leave Coinbase CDP's TEE (AWS Nitro Enclave)
- Every payment is a unique ERC-3009 authorization — replay attacks blocked
- All transactions publicly verifiable on [BaseScan](https://basescan.org)

---

## License

MIT
