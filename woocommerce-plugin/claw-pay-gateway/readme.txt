=== claw-pay Gateway ===
Contributors: orcalabs
Tags: woocommerce, payment, usdc, crypto, ai, x402, base, stablecoin
Requires at least: 6.0
Tested up to: 6.9
Requires PHP: 8.0
Requires WC: 7.0
Stable tag: 0.1.2
License: GPL-2.0-or-later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Accept payments from OpenClaw AI agents in your WooCommerce shop. USDC on Base L2. 3% commission — only when you earn.

== Description ==

claw-pay Gateway enables your WooCommerce shop to accept autonomous payments from OpenClaw AI agents via the x402 protocol.

**How it works:**

1. An AI agent browses your shop and selects a product
2. The agent sends payment via x402 (USDC on Base L2)
3. claw-pay settles the transaction automatically
4. 97% of the payment lands in your wallet — instantly

**Why claw-pay?**

* Zero upfront cost — 3% commission only when you earn
* No credit card forms, no checkout friction for agents
* USDC on Base L2 — gas fees under $0.001 per transaction
* Works alongside your existing payment methods

**Requirements:**

* A Base L2 wallet address (free — get one at coinbase.com)
* Buyers need the [claw-pay OpenClaw skill](https://clawhub.ai/orca-labs-sudo/claw-pay)

More info: [clawpay.eu/woocommerce](https://clawpay.eu/woocommerce)

== Installation ==

1. Upload the `claw-pay-gateway` folder to `/wp-content/plugins/`
2. Activate the plugin in WordPress → Plugins
3. Go to WooCommerce → Settings → Payments → claw-pay
4. Enter your Base L2 wallet address
5. Save — done

== Frequently Asked Questions ==

= Do I need a crypto wallet? =
Yes — a Base L2 wallet address to receive USDC. Free to create at coinbase.com or any Base-compatible wallet.

= What does it cost? =
The plugin is free. claw-pay takes 3% of each transaction. You receive 97% in USDC.

= Do my human customers need to change anything? =
No. This gateway is only used by AI agents. Human customers continue using your existing payment methods.

= What is x402? =
x402 is an open payment protocol built on HTTP. When a client sends a request without payment, the server responds with HTTP 402 (Payment Required). The client then signs a USDC transfer and retries automatically.

== Changelog ==

= 0.1.2 =
* Bundled gateway icon locally under `assets/claw-pay-logo.png` — no more remote file dependency
* Hardened payment header handling: `sanitize_text_field()` + `wp_unslash()`, strict base64 format check, whitelisted fields before forwarding to facilitator
* `$_GET['order_id']` now passes through `wp_unslash()` before `absint()`

= 0.1.1 =
* Renamed main gateway class to use unique `Orcalabs_ClawPay_` prefix (no more `WC_` prefix collision)
* Updated author/contributor to match WordPress.org account

= 0.1.0 =
* Initial release

== Upgrade Notice ==

= 0.1.2 =
Security + compliance fixes for WP.org guidelines: local icon asset, sanitized request data.

= 0.1.1 =
Class renamed for better isolation — no functional changes.
