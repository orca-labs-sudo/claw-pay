# x402 Wallet Skill for OpenClaw
### Project Brief | Vadim K. | v0.1

---

## Was bauen wir / Что строим

Einen kostenlosen OpenClaw-Skill, der jedem Agenten eine x402-kompatible Wallet gibt.
Der Nutzer installiert den Skill einmalig — danach kann sein Agent autonom für x402-Dienste bezahlen.
Wir betreiben den Facilitator und nehmen eine kleine Provision auf jede Transaktion.

**Geschäftsmodell:** Skill = kostenlos (Traffic/Distribution). Geld = Facilitator-Provision (%).

---

## Architektur

```
[OpenClaw Agent] 
    → installiert Skill (kostenlos, ClawHub)
    → Agent will x402-Service bezahlen
        → POST /verify  (unser Facilitator, VPS)
        → POST /settle  (unser Facilitator, VPS)
            → 97% → Verkäufer-Wallet
            →  3% → unsere Wallet  ← automatisch, kein Aufwand
        → Blockchain (Base L2 oder Solana)
    → Agent bekommt Zugang zum Service
```

---

## Stack

| Komponente | Technologie |
|---|---|
| Facilitator API | Python FastAPI oder Node.js Express |
| Blockchain-Anbindung | Coinbase CDP SDK (kein eigener Node nötig) |
| Payment-Netzwerk | Base L2 (USDC) — Gas < $0.001 |
| Hosting | Bestehender Ubuntu VPS |
| Skill-Format | SKILL.md + claw.json (OpenClaw Standard) |
| Provision-Routing | x402 V2 dynamic `payTo` |

---

## Facilitator — zwei Endpunkte, das ist alles

```
POST /verify
    Input:  Payment Payload (vom Agenten signiert)
    Output: { isValid: true/false }

POST /settle  
    Input:  Payment Payload
    Output: { success: true, txHash: "0x...", fee: "3%" }
    Action: 
        1. Validiere Signatur
        2. Route 97% → payTo (Verkäufer)
        3. Route  3% → unsere Wallet
        4. Submit zu Base L2 via Coinbase CDP
        5. Warte auf Confirmation
        6. Return Receipt
```

**Wichtig:** Facilitator hält KEINE Gelder. Er ist nur Verifikations- und Settlement-Service.

---

## SKILL.md Struktur (OpenClaw)

```
x402-wallet/
├── SKILL.md          ← Anweisungen für den Agenten
├── claw.json         ← Manifest (Name, Version, Permissions)
├── src/
│   ├── wallet.js     ← Wallet-Logik (key management, signing)
│   └── pay.js        ← x402 Payment Flow
└── README.md         ← Für ClawHub-Nutzer
```

**SKILL.md Kerninhalt:**
- Wie Agent eine Wallet erstellt/lädt
- Wie Agent ein 402-Response erkennt
- Wie Agent Payment Payload signiert
- Wie Agent über unseren Facilitator bezahlt
- Wie Agent Balance checkt

---

## Wirtschaftlichkeit

### Kosten pro Transaktion
| Posten | Kosten |
|---|---|
| Base L2 Gas | ~$0.0003 (zahlt Käufer) |
| Coinbase CDP | $0.001 nach 1000 Free/Monat |
| Server (anteilig) | ~$0.0001 |
| **Gesamt** | **~$0.001** |

### Provision-Szenarien
| Transaktionsvolumen/Monat | Provision 3% | Nettogewinn |
|---|---|---|
| $500 | $15 | ~$14 |
| $5,000 | $150 | ~$148 |
| $50,000 | $1,500 | ~$1,498 |

**Breakeven:** Praktisch sofort — Fixkosten = VPS der sowieso läuft.

### Token-Kosten Analyse (wichtig!)
- Unser Facilitator verbraucht KEINE LLM-Tokens
- Tokens verbraucht der Agent des Nutzers — ist sein Problem
- Wir sind reiner Payment-Middleware — kein AI-Call auf unserer Seite

---

## Offene Fragen (vor Implementierung klären)

1. **Provision-Höhe:** 3% realistisch oder zu viel für Mikrozahlungen?
2. **Wallet-Sicherheit:** Wie speichert der Agent seinen Private Key sicher? (lokale Verschlüsselung?)
3. **Minimum-Betrag:** x402 erlaubt $0.001 — macht 3% Provision da noch Sinn?
4. **ClawHub Verified:** Zertifizierungsprozess prüfen (separater Task)
5. **MiCA/BaFin:** Brauchen wir eine Lizenz als Facilitator in der EU? (Grauzone — prüfen)

---

## Phasen

### Phase 1 — Facilitator (2-3 Wochen)
- [ ] Coinbase CDP Account + API Keys
- [ ] FastAPI Server: `/verify` + `/settle` Endpunkte
- [ ] Provisions-Routing via dynamic `payTo`
- [ ] Testnet (Base Sepolia) — alles testen
- [ ] Deploy auf VPS

### Phase 2 — OpenClaw Skill (1 Woche)
- [ ] SKILL.md schreiben
- [ ] claw.json Manifest
- [ ] Wallet-Logik (erstellen, laden, signieren)
- [ ] Lokal testen mit eigenem OpenClaw
- [ ] ClawHub Verified Zertifizierung (separater Task)

### Phase 3 — Launch
- [ ] ClawHub publizieren
- [ ] Kurze README + Demo-Video (optional aber hilft)
- [ ] x402 Bazaar registrieren

---

## Nicht in Scope (bewusst weggelassen)

- Eigene Fiat-Onramp — Nutzer kauft USDC selbst (Coinbase, Kraken, etc.)
- Mobile App — reiner CLI/Messaging-Skill
- Dashboard für Nutzer — kommt später wenn Bedarf da
- Eigene Blockchain — Base L2 reicht komplett

---

## Referenzen

- x402 Docs: https://docs.x402.org
- x402 GitHub: https://github.com/coinbase/x402
- Coinbase CDP: https://docs.cdp.coinbase.com/x402
- OpenClaw Skills: https://github.com/openclaw/openclaw
- ClawHub: https://clawhub.ai

---

*Dieses Dokument ist der Startpunkt. Claude Code bekommt dieses CLAUDE.md und implementiert Phase 1.*
