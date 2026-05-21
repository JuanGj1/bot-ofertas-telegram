import asyncio
import requests
from telegram import Bot
import os
# ========================================
# CAMBIA SOLO ESTOS 3 VALORES
# ========================================

DESCUENTO_MINIMO = 5
# ========================================
async def diagnostico():
    bot = Bot(token=TELEGRAM_TOKEN)
    print("🔍 Iniciando diagnóstico...")

    # PASO 1: Probar token de Admitad
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
        print(f"📡 Respuesta Admitad token: {respuesta}")

        token = respuesta.get("access_token")
        if not token:
            print(f"❌ ERROR: No hay token. Respuesta completa: {respuesta}")
            await bot.send_message(chat_id=CHANNEL_ID, text=f"❌ Error token Admitad: {respuesta}")
            return
        print(f"✅ Token OK: {token[:15]}...")

    except Exception as e:
        print(f"❌ Error paso 1: {e}")
        await bot.send_message(chat_id=CHANNEL_ID, text=f"❌ Error conexión Admitad: {e}")
        return

    # PASO 2: Probar feeds
    try:
        url2 = "https://api.admitad.com/feeds/"
        headers2 = {"Authorization": f"Bearer {token}"}
        params2 = {"website": WEBSITE_ID, "limit": 10}
        r2 = requests.get(url2, headers=headers2, params=params2, timeout=15)
        respuesta2 = r2.json()
        print(f"📦 Respuesta feeds: {respuesta2}")
        await bot.send_message(chat_id=CHANNEL_ID, text=f"📦 Feeds: {str(respuesta2)[:500]}")

    except Exception as e:
        print(f"❌ Error paso 2: {e}")
        await bot.send_message(chat_id=CHANNEL_ID, text=f"❌ Error feeds: {e}")

async def main():
    print("🤖 Bot diagnóstico iniciado")
    await diagnostico()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
