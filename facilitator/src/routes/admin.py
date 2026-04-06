"""
GET /admin  — einfaches HTML-Dashboard
Passwortgeschützt via HTTP Basic Auth.
"""

import os
import secrets
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.services.transaction_log import get_stats, get_recent

router = APIRouter()
security = HTTPBasic()

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username.encode(), ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), ADMIN_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard(_=Depends(require_auth)):
    stats = get_stats()
    rows  = get_recent(50)

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
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f0f0f; color: #e0e0e0; padding: 24px; }}
  h1   {{ font-size: 22px; margin-bottom: 24px; color: #fff; }}
  h1 span {{ color: #3498db; }}

  .stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 32px; }}
  .card  {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px;
            padding: 20px 28px; min-width: 140px; }}
  .card .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
  .card .value {{ font-size: 28px; font-weight: 700; margin-top: 6px; }}
  .green {{ color: #2ecc71; }}
  .red   {{ color: #e74c3c; }}
  .blue  {{ color: #3498db; }}
  .gold  {{ color: #f39c12; }}

  table  {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th     {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #2a2a2a;
            color: #888; font-weight: 500; font-size: 11px; text-transform: uppercase; }}
  td     {{ padding: 10px 12px; border-bottom: 1px solid #1a1a1a; vertical-align: top; }}
  tr:hover td {{ background: #1a1a1a; }}
  code   {{ font-size: 12px; color: #aaa; }}
  a      {{ color: #3498db; text-decoration: none; }}

  .refresh {{ float: right; font-size: 12px; color: #555; margin-top: 4px; }}
</style>
</head>
<body>

<h1>🦞 <span>claw-pay</span> Admin</h1>

<div class="stats">
  <div class="card">
    <div class="label">Gesamt</div>
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

<span class="refresh">Letzte 50 Transaktionen — <a href="/admin">↻ Reload</a></span>
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
