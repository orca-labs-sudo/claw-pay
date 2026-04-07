"""
GET /admin        — HTML-Dashboard
POST /admin/reset — Testdaten löschen
Passwortgeschützt via HTTP Basic Auth.
"""

import os
import secrets
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from web3 import Web3

from src.services.transaction_log import get_stats, get_recent, clear_all

router = APIRouter()
security = HTTPBasic()

ADMIN_USER        = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS        = os.getenv("ADMIN_PASS", "changeme")
FACILITATOR_ADDR  = os.getenv("FACILITATOR_ADDRESS", "")
NETWORK_ID        = os.getenv("NETWORK_ID", "base-mainnet")

RPC = {
    "base-mainnet": "https://mainnet.base.org",
    "base-sepolia": "https://sepolia.base.org",
}

GAS_WARN_ETH  = 0.002   # gelbe Warnung
GAS_CRIT_ETH  = 0.0005  # rote Warnung


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username.encode(), ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), ADMIN_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


def get_eth_balance() -> float:
    try:
        w3 = Web3(Web3.HTTPProvider(RPC.get(NETWORK_ID, RPC["base-mainnet"])))
        bal = w3.eth.get_balance(Web3.to_checksum_address(FACILITATOR_ADDR))
        return float(Web3.from_wei(bal, "ether"))
    except Exception:
        return -1.0


@router.post("/admin/reset", include_in_schema=False)
async def admin_reset(_=Depends(require_auth)):
    clear_all()
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard(_=Depends(require_auth)):
    stats   = get_stats()
    rows    = get_recent(50)
    eth_bal = get_eth_balance()

    # Gas-Status
    if eth_bal < 0:
        gas_color = "#888"
        gas_icon  = "⚠️"
        gas_label = "Nicht abrufbar"
    elif eth_bal < GAS_CRIT_ETH:
        gas_color = "#e74c3c"
        gas_icon  = "🔴"
        gas_label = "KRITISCH — Bitte aufladen!"
    elif eth_bal < GAS_WARN_ETH:
        gas_color = "#f39c12"
        gas_icon  = "🟡"
        gas_label = "Niedrig — bald aufladen"
    else:
        gas_color = "#2ecc71"
        gas_icon  = "🟢"
        gas_label = "OK"

    eth_display = f"{eth_bal:.6f} ETH" if eth_bal >= 0 else "—"
    basescan_url = f"https://basescan.org/address/{FACILITATOR_ADDR}"

    rows_html = ""
    for r in rows:
        status  = "✅" if r["success"] else "❌"
        ts      = r["ts"][:19].replace("T", " ")
        payer   = (r["payer"] or "")[:10] + "…" if r["payer"] else "—"
        seller  = (r["seller"] or "")[:10] + "…" if r["seller"] else "—"
        gross   = r["gross"] or "—"
        fee     = r["fee"] or "—"
        network = r["network"] or "—"
        error   = f'<span style="color:#e74c3c;font-size:11px">{r["error"]}</span>' if r["error"] else ""
        tx      = f'<a href="https://basescan.org/tx/{r["intake_tx"]}" target="_blank">🔗</a>' if r["intake_tx"] else "—"

        rows_html += f"""
        <tr>
            <td>{status}</td>
            <td style="color:#888">{ts}</td>
            <td><code>{payer}</code></td>
            <td><code>{seller}</code></td>
            <td>{gross}</td>
            <td>{fee}</td>
            <td style="font-size:11px">{network}</td>
            <td>{tx}</td>
            <td>{error}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>claw-pay Admin</title>
<link rel="icon" type="image/png" href="https://clawpay.eu/claw-pay-logo.png">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f0f0f; color: #e0e0e0; padding: 24px; }}
  h1   {{ font-size: 22px; margin-bottom: 8px; color: #fff; }}
  h1 span {{ color: #3498db; }}
  .network {{ font-size: 12px; color: #555; margin-bottom: 24px; }}

  .stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
  .card  {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px;
            padding: 20px 28px; min-width: 140px; }}
  .card .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
  .card .value {{ font-size: 28px; font-weight: 700; margin-top: 6px; }}
  .card .sub   {{ font-size: 11px; color: #555; margin-top: 4px; }}
  .green {{ color: #2ecc71; }}
  .red   {{ color: #e74c3c; }}
  .blue  {{ color: #3498db; }}
  .gold  {{ color: #f39c12; }}

  .gas-card {{ border-color: {gas_color}44; }}

  .wallet-box {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px;
                 padding: 16px 20px; margin-bottom: 24px; font-size: 13px; }}
  .wallet-box a {{ color: #3498db; text-decoration: none; font-size: 12px; }}

  table  {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th     {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #2a2a2a;
            color: #888; font-weight: 500; font-size: 11px; text-transform: uppercase; }}
  td     {{ padding: 10px 12px; border-bottom: 1px solid #1a1a1a; vertical-align: top; }}
  tr:hover td {{ background: #1a1a1a; }}
  code   {{ font-size: 12px; color: #aaa; }}
  a      {{ color: #3498db; text-decoration: none; }}

  .toolbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
  .toolbar-right {{ display: flex; gap: 12px; align-items: center; }}
  .btn-reset {{ background: #2a1a1a; border: 1px solid #e74c3c44; color: #e74c3c;
                padding: 6px 14px; border-radius: 6px; font-size: 12px; cursor: pointer; }}
  .btn-reset:hover {{ background: #e74c3c22; }}
</style>
</head>
<body>

<h1><img src="https://clawpay.eu/claw-pay-logo.png" style="height:28px;vertical-align:middle;margin-right:8px;"><span>claw-pay</span> Admin</h1>
<div class="network">Netzwerk: <strong>{NETWORK_ID}</strong></div>

<div class="wallet-box">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div>
      <div style="color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Facilitator Wallet</div>
      <code style="font-size:12px;color:#ccc">{FACILITATOR_ADDR}</code>
    </div>
    <a href="{basescan_url}" target="_blank">BaseScan 🔗</a>
  </div>
</div>

<div class="stats">
  <div class="card gas-card">
    <div class="label">Gas (ETH) {gas_icon}</div>
    <div class="value" style="color:{gas_color};font-size:22px">{eth_display}</div>
    <div class="sub" style="color:{gas_color}">{gas_label}</div>
  </div>
  <div class="card">
    <div class="label">Transaktionen</div>
    <div class="value blue">{stats['total']}</div>
  </div>
  <div class="card">
    <div class="label">Erfolgreich</div>
    <div class="value green">{stats['success']}</div>
  </div>
  <div class="card">
    <div class="label">Fehler</div>
    <div class="value red">{stats['errors']}</div>
  </div>
  <div class="card">
    <div class="label">Volumen (USDC)</div>
    <div class="value blue">$ {stats['volume_usd']:.4f}</div>
  </div>
  <div class="card">
    <div class="label">Provision (3%)</div>
    <div class="value gold">$ {stats['fees_usd']:.4f}</div>
  </div>
</div>

<div class="toolbar">
  <span style="font-size:12px;color:#555">Letzte 50 Transaktionen</span>
  <div class="toolbar-right">
    <a href="/admin">↻ Reload</a>
    <form method="post" action="/admin/reset" onsubmit="return confirm('Alle Transaktionen löschen?')">
      <button class="btn-reset" type="submit">🗑 Testdaten löschen</button>
    </form>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th></th>
      <th>Zeit (UTC)</th>
      <th>Käufer</th>
      <th>Verkäufer</th>
      <th>Betrag</th>
      <th>Provision</th>
      <th>Netzwerk</th>
      <th>TX</th>
      <th>Fehler</th>
    </tr>
  </thead>
  <tbody>
    {rows_html if rows_html else '<tr><td colspan="9" style="text-align:center;color:#555;padding:40px">Noch keine Transaktionen</td></tr>'}
  </tbody>
</table>

</body>
</html>"""
    return html
