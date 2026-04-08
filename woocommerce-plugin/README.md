# claw-pay Gateway for WooCommerce

Accept payments from OpenClaw AI agents in your WooCommerce shop.  
**You pay 3% only when you earn. Zero upfront cost.**

## How it works

1. AI agent browses your shop, adds item to cart
2. Agent sends payment via x402 protocol (USDC on Base L2)
3. claw-pay settles automatically — 97% lands in your wallet
4. Order is marked as paid, agent receives confirmation

No human checkout. No credit card forms. Fully automatic.

## Requirements

- WordPress 6.0+
- WooCommerce 7.0+
- A Base L2 wallet address (free — [get one at Coinbase](https://coinbase.com))
- Buyers need the [claw-pay OpenClaw skill](https://clawhub.ai/orca-labs-sudo/claw-pay)

## Installation

1. Download `claw-pay-gateway.php`
2. Upload to `/wp-content/plugins/claw-pay-gateway/`
3. Activate in WordPress → Plugins
4. Go to WooCommerce → Settings → Payments → claw-pay
5. Enter your Base L2 wallet address
6. Done

## Settings

| Setting | Description |
|---|---|
| Seller Wallet | Your Base L2 address — receives 97% of each payment |
| Facilitator URL | Default: `https://claw-pay.org` — leave as is |

## How agents pay

Agents with the [claw-pay skill](https://clawhub.ai/orca-labs-sudo/claw-pay) installed call:

```
GET /wc-api/claw_pay?order_id=123
→ 402 Payment Required (no payment header)
→ Agent signs USDC transfer, retries with X-PAYMENT header
→ 200 OK — order complete
```

## Fees

| | |
|---|---|
| Plugin | Free |
| Per transaction | 3% to claw-pay facilitator |
| You receive | 97% of order total in USDC |
| Gas fees | ~$0.0003 (paid by buyer) |

## Links

- Facilitator: https://claw-pay.org
- Landing page: https://clawpay.eu
- OpenClaw Skill: https://clawhub.ai/orca-labs-sudo/claw-pay
- License: BSL-1.1
