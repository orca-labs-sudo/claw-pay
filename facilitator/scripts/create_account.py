"""
Einmaliges Script: Facilitator EVM Account auf CDP anlegen.
Gibt die Wallet-Adresse aus → in .env als FACILITATOR_ADDRESS eintragen.

Ausführen:
    cd facilitator
    .venv/Scripts/python scripts/create_account.py
"""

import asyncio
from dotenv import load_dotenv
load_dotenv()

from cdp import CdpClient

async def main():
    async with CdpClient() as cdp:
        account = await cdp.evm.create_account(name="x402-facilitator")
        print(f"\nAccount erstellt!")
        print(f"FACILITATOR_ADDRESS={account.address}\n")
        print("→ Diesen Wert in .env eintragen!")

asyncio.run(main())
