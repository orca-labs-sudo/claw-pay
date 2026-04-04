"""
Deploy TestUSDC auf Base Sepolia via web3.py (Buyer-Key).

Ausführen:
    cd facilitator
    .venv/Scripts/python scripts/deploy_test_usdc.py
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from web3 import Web3
from eth_account import Account
from solcx import compile_source, install_solc


RPC = "https://sepolia.base.org"
BUYER_KEY = os.environ["BUYER_PRIVATE_KEY"]


def compile_contract() -> tuple[str, list]:
    print("Installiere solc 0.8.20...")
    install_solc("0.8.20", show_progress=False)
    source = Path("contracts/TestUSDC.sol").read_text()
    compiled = compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version="0.8.20",
        optimize=True,
        optimize_runs=200,
    )
    data = compiled["<stdin>:TestUSDC"]
    return data["bin"], data["abi"]


def deploy():
    w3 = Web3(Web3.HTTPProvider(RPC))
    deployer = Account.from_key(BUYER_KEY)

    print(f"Deployer: {deployer.address}")
    eth_balance = w3.eth.get_balance(deployer.address)
    print(f"ETH Balance: {w3.from_wei(eth_balance, 'ether'):.6f} ETH")

    if eth_balance == 0:
        print("FEHLER: Deployer hat kein ETH. Bitte zuerst ETH vom Faucet holen.")
        return

    print("Kompiliere TestUSDC.sol...")
    bytecode, abi = compile_contract()
    print(f"Bytecode: {len(bytecode)//2} Bytes")

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = w3.eth.get_transaction_count(deployer.address)
    gas_price = w3.eth.gas_price

    tx = contract.constructor().build_transaction({
        "from":     deployer.address,
        "nonce":    nonce,
        "gasPrice": gas_price,
        "chainId":  84532,
    })

    signed = deployer.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Deploy Tx: {tx_hash.hex()}")
    print("Warte auf Bestätigung...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    contract_address = receipt["contractAddress"]

    print(f"\nTestUSDC deployed!")
    print(f"TEST_USDC_ADDRESS={contract_address}")
    print(f"BaseScan: https://sepolia.basescan.org/address/{contract_address}")
    print(f"\n→ In .env als TEST_USDC_ADDRESS eintragen!")

    # Buyer hat jetzt 1,000,000 tUSDC — nochmal prüfen
    deployed = w3.eth.contract(address=contract_address, abi=abi)
    balance = deployed.functions.balanceOf(deployer.address).call()
    print(f"Buyer tUSDC Balance: {balance / 1e6:.2f} tUSDC ✓")


deploy()
