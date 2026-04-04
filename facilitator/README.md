# x402 Facilitator

Payment Facilitator für das x402-Protokoll. Agiert als Payment Provider (ähnlich PayPal) auf Base L2 mit USDC.

**Provision:** 3% vom Seller. Seller erhält 97%, Facilitator behält 3%.

---

## Setup

### 1. Coinbase CDP Account

1. Gehe zu [cdp.coinbase.com](https://cdp.coinbase.com) → Account erstellen
2. **API Keys** → "Create API Key"
   - Key Name notieren → `CDP_API_KEY_NAME`
   - Private Key (PEM) notieren → `CDP_API_KEY_PRIVATE_KEY`

### 2. Facilitator Wallet erstellen

Im CDP Dashboard → **Wallets** → "Create Wallet":
- Network: **Base Sepolia** (für Tests) oder **Base Mainnet**
- Wallet ID notieren → `FACILITATOR_WALLET_ID`
- Wallet Adresse notieren → `FACILITATOR_ADDRESS`

Seed exportieren und als `wallet.seed` im Projektordner speichern.

**Wichtig:** `wallet.seed` niemals committen! Steht in `.gitignore`.

### 3. Wallet aufladen

Für **Base Sepolia** (Testnet):
- ETH (für Gas): [Coinbase Sepolia Faucet](https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet)
- USDC (Testnet): [Circle Faucet](https://faucet.circle.com) → Network: "Base Sepolia"

Für **Base Mainnet**:
- ETH für Gas: ~$0.10 reichen für hunderte Transaktionen
- USDC: Kauf über Coinbase/Kraken, dann auf Base L2 bridgen

### 4. .env befüllen

```bash
cp .env.example .env
```

```env
CDP_API_KEY_NAME=organizations/xxx/apiKeys/yyy
CDP_API_KEY_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----\n"

FACILITATOR_WALLET_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
FACILITATOR_ADDRESS=0x...

PROVISION_PERCENT=3
ESCROW_TIMEOUT_HOURS=48

NETWORK_ID=base-sepolia
PORT=8000
```

### 5. Starten

**Lokal (Entwicklung):**
```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

**Docker (VPS):**
```bash
docker compose up -d
```

**Nginx** (SSL auf VPS):
```bash
cp nginx.conf /etc/nginx/sites-available/x402
# YOUR_DOMAIN in nginx.conf ersetzen
certbot --nginx -d YOUR_DOMAIN
nginx -s reload
```

---

## Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## Testclient (End-to-End auf Sepolia)

Testet den kompletten Flow: Signatur → `/verify` → `/settle`

```bash
# Zusätzliche Variablen in .env:
# BUYER_PRIVATE_KEY=0x...      (Test-Wallet mit Sepolia USDC)
# TEST_SELLER_ADDRESS=0x...    (Empfänger der 97%)
# FACILITATOR_URL=http://localhost:8000

python scripts/testclient.py
```

---

## API

### `POST /verify`

Validiert ein Payment Payload ohne on-chain Settlement.

```json
{
  "payment": { "x402Version": 1, "scheme": "exact", "network": "base-sepolia", "payload": { ... } },
  "paymentRequirements": { "maxAmountRequired": "0xf4240", "payTo": "0x...", ... }
}
```

Response:
```json
{ "isValid": true, "payer": "0x..." }
```

### `POST /settle`

Verifiziert + settelt on-chain. 97% → Seller, 3% → Facilitator.

```json
{
  "payment": { ... },
  "paymentRequirements": { ... },
  "sellerAddress": "0x..."
}
```

Response:
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

### `GET /health`

```json
{ "status": "ok" }
```

---

## Projektstruktur

```
facilitator/
├── src/
│   ├── main.py              FastAPI App
│   ├── models/payment.py    Datenmodelle
│   ├── routes/verify.py     POST /verify
│   ├── routes/settle.py     POST /settle
│   └── services/
│       ├── cdp.py           Coinbase CDP Wrapper
│       └── nonce_store.py   Replay-Schutz
├── tests/
│   ├── test_verify.py
│   └── test_settle.py
├── scripts/testclient.py    End-to-End Testclient
├── docker-compose.yml
├── nginx.conf
├── Dockerfile
└── requirements.txt
```
