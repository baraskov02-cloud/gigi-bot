import aiohttp
import time
from config import CRYPTO_BOT_TOKEN

API_URL = "https://pay.crypt.bot/api"

async def create_invoice(user_id: int, amount: float, description: str = "Пополнение баланса Gigi"):
    url = f"{API_URL}/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    params = {
        "asset": "USDT",
        "amount": str(amount),
        "description": description,
        "paid_btn_name": "callback",
        "paid_btn_url": "https://t.me/market_gigs_bot",
        "payload": f"topup_{user_id}",
        "allow_comments": False,
        "allow_anonymous": False
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            if data.get("ok"):
                result = data["result"]
                return result["pay_url"], result["invoice_id"]
            else:
                raise Exception(f"CryptoBot error: {data}")

async def transfer_money(user_id: int, amount: float, spend_id: str = None):
    url = f"{API_URL}/transfer"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    if not spend_id:
        spend_id = f"payout_{user_id}_{int(time.time())}"
    params = {
        "user_id": str(user_id),
        "asset": "USDT",
        "amount": str(amount),
        "spend_id": spend_id
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            if data.get("ok"):
                return True
            else:
                raise Exception(f"Transfer error: {data}")

async def check_invoice(invoice_id):
    url = f"{API_URL}/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    params = {"invoice_ids": invoice_id}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            if data.get("ok"):
                items = data["result"]["items"]
                if items:
                    inv = items[0]
                    return inv["status"]
            return None