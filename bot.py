import asyncio
import requests
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# ========================================
# CAMBIA SOLO ESTOS 3 VALORES
# ========================================
TELEGRAM_TOKEN = "8641134190:AAHH96wQ5H3_TJjYfKK1meCJ5Cu-hMl4EuI"
CHANNEL_ID = "@OfertasJG"
ADMITAD_BASE64 = "ZGc4bHhlOEZHSVROZXlzeE9XcWpEbU05akxjNmUwOjh6QWRMNW5LbDBSdFE2RXpqcnVuWWlSWkZaeHhSZg=="
WEBSITE_ID = "2943808"
# ========================================

def get_admitad_token():
    """Obtiene token de acceso de Admitad"""
    url = "https://api.admitad.com/token/"
    headers = {
        "Authorization": f"Basic {ADMITAD_BASE64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "advcampaigns banners coupons feeds manage_adspace"
    }
    r = requests.post(url, headers=headers, data=data)
    return r.json().get("access_token")

def get_ofertas(token):
    """Obtiene productos con descuento de AliExpress vía Admitad"""
    url = "https://api.admitad.com/products/list/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "website": WEBSITE_ID,
        "limit": 10,
        "order_by": "-discount"  # Ordena por mayor descuento
    }
    r = requests.get(url, headers=headers, params=params)
    productos = r.json().get("results", [])
    
    # Filtrar solo los que tienen descuento real
    return [p for p in productos if p.get("discount", 0) > 15][:3]

def generar_link_afiliado(token, url_producto):
    """Convierte un link normal en link de afiliado"""
    url = "https://api.admitad.com/deeplink/create/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "website": WEBSITE_ID,
        "url": url_producto
    }
    r = requests.get(url, headers=headers, params=params)
    return r.json().get("deeplink", url_producto)

async def publicar_ofertas():
    """Publica las mejores ofertas en el canal de Telegram"""
    print(f"[{datetime.now()}] Buscando ofertas...")
    
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        token = get_admitad_token()
        ofertas = get_ofertas(token)

        if not ofertas:
            print("Sin ofertas disponibles por ahora")
            return

        # Encabezado del bloque de ofertas
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🔥 *OFERTAS DEL DÍA* 🔥\n📅 _{datetime.now().strftime('%d de %B, %Y')}_",
            parse_mode="Markdown"
        )

        for oferta in ofertas:
            nombre = oferta.get("name", "Producto")
            precio = oferta.get("price", 0)
            precio_original = oferta.get("oldprice", precio)
            descuento = oferta.get("discount", 0)
            imagen = oferta.get("image", "")
            url_producto = oferta.get("url", "")
            link = generar_link_afiliado(token, url_producto)

            mensaje = (
                f"🛍️ *{nombre}*\n\n"
                f"💰 ~~${precio_original:,.0f}~~ → *${precio:,.0f} MXN*\n"
                f"🔥 *{descuento}% de descuento*\n\n"
                f"🛒 [Ver oferta aquí]({link})"
            )

            if imagen:
                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=imagen,
                    caption=mensaje,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=mensaje,
                    parse_mode="Markdown"
                )

            await asyncio.sleep(2)

        print(f"✅ {len(ofertas)} ofertas publicadas")

    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("🤖 Bot de OfertasJG iniciado")
    scheduler = AsyncIOScheduler()

    # Publicar 3 veces al día en horarios de alto tráfico
    scheduler.add_job(publicar_ofertas, 'cron', hour=9,  minute=0)
    scheduler.add_job(publicar_ofertas, 'cron', hour=14, minute=0)
    scheduler.add_job(publicar_ofertas, 'cron', hour=20, minute=0)

    scheduler.start()
    await publicar_ofertas()  # Publicar al iniciar
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
