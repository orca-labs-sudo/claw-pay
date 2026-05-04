---
name: claw-pay Projekt — aktueller Stand
description: x402 Facilitator + OpenClaw Skill, 3% Provision, Base L2 USDC — Stand April 2026, strategische Pause
type: project
originSessionId: 7c8f7deb-7f0c-48a1-89bc-92efe8ebd4b9
---
Hobby-Experiment. Kein Startup-Anspruch. Wenn Erfolg → dann neu aufsetzen.

**Geschäftsmodell:** Payment Provider wie PayPal. 3% Provision vom Seller. Buyer zahlt nichts extra.

**Flow:** payTo = Facilitator-Wallet. Facilitator empfängt 100%, sendet 97% an Seller, behält 3%.

**Why:** Technologie verstehen, Agenten-Ökosystem kennenlernen, kleines Nebeneinkommen.

---

## Was FERTIG ist ✅

- Facilitator (Python FastAPI) — /verify + /settle — läuft auf Mainnet
- /demo/joke — live, $0.01 USDC (78 Aufrufe, 0 bezahlt — nie selbst getestet, kein akuter Bedarf)
- OpenClaw Skill v0.3.3 — **237 Downloads** auf ClawHub (Stand 28. April)
- **WooCommerce Plugin v0.1.2 — APPROVED & LIVE bei WordPress.org (23. April 2026)**
  - Public URL: https://wordpress.org/plugins/claw-pay-gateway
  - SVN Repo: https://plugins.svn.wordpress.org/claw-pay-gateway (rev 3514588)
  - **78 Downloads total** (50 davon WP.org-CDN-Bots am 24.04, ~27 echte Menschen)
  - **Active installs: Fewer than 10** (1-9 echte WP-Sites), 0 Reviews
- Logo sauber freigestellt (saturation-basierte Alpha-Mask), deployed auf clawpay.eu + 5 Varianten in `brand/`
- Landing Page: clawpay.eu (inkl. Live Demo, Impressum, /woocommerce)
- VPS: 217.160.170.113 | GitHub: github.com/orca-labs-sudo/claw-pay

---

## Strategische Pause ab 28. April 2026 ⏸️

**Entscheidung:** Keine aktive Seller-Akquise. Warten auf coinbase/x402 PR #42.

**Grund:** Markt existiert noch nicht. Henne-Ei-Problem — keine Sellers weil keine Buyers, keine Buyers weil keine Sellers. Projekt ist 6-12 Monate zu früh. Reverse-Search (Gemini) bestätigt: keine aktiven Shops die claw-pay öffentlich bewerben, weil das System im Hintergrund für Maschinen läuft, nicht im Checkout-Footer für Menschen.

**Risiko bewusst akzeptiert:** Wenn x402 mainstream → Stripe/Coinbase/PayPal übernehmen den Markt in Wochen. Projekt landet "in der Geschichte". Akzeptiert — war von Anfang an Hobby/Experiment.

**Trigger für neue Aktivität:** coinbase/x402 PR #42 gemerged.

---

## Offene Kanäle — alle wartend ⏳

| Was | Status | Seit |
|---|---|---|
| coinbase/x402 PR #42 | Open, Follow-up gesendet (237 installs, live mainnet), keine Reaktion | 8. April |
| ClawHub Verified #1578 | Nur clawsweeper-Bot (automatisch, kein Mensch), kein Maintainer | 8. April |
| ClawHub Plugin-Suche #1577 | Bot bestätigt Bug noch aktiv, kein Fix | 8. April |
| ClawHub Plugin-Delete #1668 | bristy versuchte Konkurrenz-Pitch, clawsweeper-Bot, kein Maintainer | 14. April |
| ClawHub stale Plugin-Einträge #1744 | 0 Kommentare | 20. April |

**Hinweis:** clawsweeper = automatischer Codex-Bot — kein echter ClawHub-Maintainer.

---

## Infrastruktur

| Was | Details |
|---|---|
| VPS | IONOS, Ubuntu 22.04, 217.160.170.113 |
| Facilitator Wallet | 0xee94AB6c6c201E6069bB017E4d23200A60f5aB65 |
| Network | base-mainnet |
| Domains | claw-pay.org (API), clawpay.eu (Landing) |
| Deploy | ssh root@217.160.170.113 → cd /opt/claw-pay/facilitator && docker compose down && docker compose up -d --build |
| Traffic | ssh root@217.160.170.113 → clawstats |
