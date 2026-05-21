import asyncio
import requests
import xml.etree.ElementTree as ET
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import base64

# ========================================
# TUS VALORES
# ========================================
TELEGRAM_TOKEN = "8641134190:AAHH96wQ5H3_TJjYfKK1meCJ5Cu-hMl4EuI"
CHANNEL_ID = "@OfertasJG"
CLIENT_ID = "dg8lxe8FGITNeysxOWqjDmM9jLc6e0"
CLIENT_SECRET = "8zAdL5nKl0RtQ6EzjrunYiRZFZxxRf"
WEBSITE_ID = "2943808"
DESCUENTO_MINIMO = 5
# ========================================

ADMITAD_BASE64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

def get_token():
    try:
        r = requests.post(
            "https://api.admitad.com/token/",
            headers={
                "Authorization": f"Basic {ADMITAD_BASE64}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "client_credentials",
                "scope": "advcampaigns banners coupons feeds manage_adspace"
            },
            timeout=15
        )
        token = r.json().get("access_token")
        print(f"Token: {'OK' if token else 'FALLO - ' + str(r.json())}")
        return token
    except Exception as e:
        print(f"Error token: {e}")
        return None

def get_feed_url(token):
    try:
        r = requests.get(
            "https://api.admitad.com/feeds/",
            headers={"Authorization": f"Bearer {token}"},
            params={"website": WEBSITE_ID, "limit": 10},
            timeout=15
        )
        feeds = r.json().get("results", [])
        print(f"Feeds encontrados: {len(feeds)}")
        if feeds:
            return feeds[0].get("url")
        return None
    except Exception as e:
        print(f"Error feeds: {e}")
        return None

def get_ofertas(feed_url):
    try:
        r = requests.get(feed_url, timeout=60)
        root = ET.fromstring(r.content)
        items = root.findall('.//offer') or root.findall('.//item') or root.findall('.//product')
        print(f"Productos en feed: {len(items)}")
        
        ofertas = []
        for item in items:
            try:
                precio_tag = item.find('price') or item.find('Price')
                precio = float(precio_tag.text or 0) if precio_tag is not None else 0
                
                oldprice_tag = item.find('oldprice') or item.find('old_price')
                precio_original = float(oldprice_tag.text or precio) if oldprice_tag is not None else precio
                
                descuento = round(((precio_original - precio) / precio_original) * 100) if precio_original > precio else 0
                
                if descuento < DESCUENTO_MINIMO:
                    continue
                
                nombre_tag = item.find('name') or item.find('title')
                imagen_tag = item.find('picture') or item.find('image')
                url_tag = item.find('url') or item.find('link')
                
                ofertas.append({
                    'nombre': (nombre_tag.text or "Producto")[:100],
                    'precio': precio,
                    'precio_original': precio_original,
                    'descuento': descuento,
                    'imagen': imagen_tag.text if imagen_tag is not None else "",
                    'link': url_tag.text if url_tag is not None else ""
                })
            except:
                continue
        
        ofertas.sort(key=lambda x: x['descuento'], reverse=True)
        print(f"Ofertas con {DESCUENTO_MINIMO}%+ descuento: {len(ofertas)}")
        return ofertas[:3]
    except Exception as e:
        print(f"Error feed: {e}")
        return []

async def publicar_ofertas():
    print(f"\n[{datetime.now()}] Buscando ofertas...")
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        
        token = get_token()
        if not token:
            print("Sin token de Admitad")
            return
        
        feed_url = get_feed_url(token)
        if not feed_url:
            print("Sin feed disponible")
            return
        
        ofertas = get_ofertas(feed_url)
        if not ofertas:
            print("Sin ofertas disponibles")
            return
        
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🔥 *OFERTAS DEL DÍA* 🔥\n📅 _{datetime.now().strftime('%d de %B, %Y')}_",
            parse_mode="Markdown"
        )
        
        for oferta in ofertas:
            mensaje = (
                f"🛍️ *{oferta['nombre']}*\n\n"
                f"💰 ~~${oferta['precio_original']:,.0f}~~ → *${oferta['precio']:,.0f}*\n"
                f"🔥 *{oferta['descuento']}% de descuento*\n\n"
                f"🛒 [Ver oferta aquí]({oferta['link']})"
            )
            try:
                if oferta.get('imagen'):
                    await bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=oferta['imagen'],
                        caption=mensaje,
                        parse_mode="Markdown"
                    )
                else:
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=mensaje,
                        parse_mode="Markdown"
                    )
            except:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=mensaje,
                    parse_mode="Markdown"
                )
            await asyncio.sleep(2)
        
        print(f"✅ {len(ofertas)} ofertas publicadas")
    
    except Exception as e:
        print(f"Error general: {e}")

async def main():
    print("🤖 Bot de OfertasJG iniciado")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(publicar_ofertas, 'cron', hour=9,  minute=0)
    scheduler.add_job(publicar_ofertas, 'cron', hour=14, minute=0)
    scheduler.add_job(publicar_ofertas, 'cron', hour=20, minute=0)
    scheduler.start()
    await publicar_ofertas()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
