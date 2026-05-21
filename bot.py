import asyncio
import requests
from telegram import Bot
import base64

# ========================================
# PON TUS VALORES AQUÍ
# ========================================
TELEGRAM_TOKEN = "8641134190:AAHH96wQ5H3_TJjYfKK1meCJ5Cu-hMl4EuI"
CHANNEL_ID = "@OfertasJG"
CLIENT_ID = "dg8lxe8FGITNeysxOWqjDmM9jLc6e0"        # De Admitad → API y aplicaciones
CLIENT_SECRET = "8zAdL5nKl0RtQ6EzjrunYiRZFZxxRf" # De Admitad → API y aplicaciones
WEBSITE_ID = "2943808"
# ========================================

# Genera el BASE64 automáticamente
ADMITAD_BASE64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

async def diagnostico():
    bot = Bot(token=TELEGRAM_TOKEN)
    print(f"🔑 BASE64 generado: {ADMITAD_BASE64[:20]}...")
    print("🔍 Iniciando diagnóstico...")
    try:
        url = "https://api.admitad.com/token/"
        headers = {
            "Authorization": f"Basic {ADMITAD_BASE64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "advcampaigns banners coupons feeds manage_adspace"
        }
        r = requests.post(url, headers=headers, data=data, timeout=15)
        respuesta = r.json()
        print(f"📡 Respuesta: {respuesta}")
        token = respuesta.get("access_token")
        if not token:
            await bot.send_message(chat_id=CHANNEL_ID, text=f"❌ Error token: {respuesta}")
            return
        print(f"✅ Token OK")
        await bot.send_message(chat_id=CHANNEL_ID, text="✅ Conexión con Admitad exitosa!")
        url2 = "https://api.admitad.com/feeds/"
        headers2 = {"Authorization": f"Bearer {token}"}
        params2 = {"website": WEBSITE_ID, "limit": 10}
        r2 = requests.get(url2, headers=headers2, params=params2, timeout=15)
        respuesta2 = r2.json()
        print(f"📦 Feeds: {respuesta2}")
        await bot.send_message(chat_id=CHANNEL_ID, text=f"📦 Feeds: {str(respuesta2)[:500]}")
    except Exception as e:
        print(f"❌ Error: {e}")
        await bot.send_message(chat_id=CHANNEL_ID, text=f"❌ Error: {e}")

async def main():
    print("🤖 Diagnóstico iniciado")
    await diagnostico()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
