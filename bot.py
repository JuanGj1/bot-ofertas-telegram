import asyncio
import requests
import xml.etree.ElementTree as ET
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import os

# ========================================
# CONFIGURACIÓN — Lee de variables de entorno
# ========================================
TELEGRAM_TOKEN = "8641134190:AAHH96wQ5H3_TJjYfKK1meCJ5Cu-hMl4EuI"
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@OfertasJG")
ADMITAD_BASE64 = os.environ.get("ZGc4bHhlOEZHSVROZXlzeE9XcWpEbU05akxjNmUwOjh6QWRMNW5LbDBSdFE2RXpqcnVuWWlSWkZaeHhSZg==")
WEBSITE_ID = "2943808"
DESCUENTO_MINIMO = 5
# ========================================

def get_admitad_token():
    """Obtiene token de acceso de Admitad"""
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
        token = r.json().get("access_token")
        print(f"✅ Token obtenido: {token[:10]}..." if token else "❌ No se obtuvo token")
        return token
    except Exception as e:
        print(f"❌ Error obteniendo token: {e}")
        return None

def get_feeds(token):
    """Obtiene la lista de feeds disponibles"""
    try:
        url = "https://api.admitad.com/feeds/"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"website": WEBSITE_ID, "limit": 10}
        r = requests.get(url, headers=headers, params=params, timeout=15)
        feeds = r.json().get("results", [])
        print(f"📦 Feeds encontrados: {len(feeds)}")
        for f in feeds:
            print(f"  - {f.get('name')} | URL: {f.get('url')}")
        return feeds
    except Exception as e:
        print(f"❌ Error obteniendo feeds: {e}")
        return []

def get_ofertas_desde_feed(feed_url):
    """Descarga y procesa el feed XML de productos"""
    try:
        print(f"📥 Descargando feed: {feed_url}")
        r = requests.get(feed_url, timeout=60)
        root = ET.fromstring(r.content)
        
        ofertas = []
        # Buscar ofertas en diferentes formatos XML
        items = root.findall('.//offer') or root.findall('.//item') or root.findall('.//product')
        print(f"🔍 Productos encontrados en feed: {len(items)}")
        
        for item in items:
            try:
                # Obtener precio
                precio_tag = item.find('price') or item.find('Price')
                precio = float(precio_tag.text or 0) if precio_tag is not None else 0
                
                # Obtener precio original
                oldprice_tag = item.find('oldprice') or item.find('old_price') or item.find('compare_at_price')
                precio_original = float(oldprice_tag.text or precio) if oldprice_tag is not None else precio
                
                # Calcular descuento
                if precio_original > precio and precio > 0:
                    descuento = round(((precio_original - precio) / precio_original) * 100)
                else:
                    descuento = 0
                
                if descuento < DESCUENTO_MINIMO:
                    continue
                
                # Obtener nombre
                nombre_tag = item.find('name') or item.find('title') or item.find('Name')
                nombre = nombre_tag.text if nombre_tag is not None else "Producto"
                
                # Obtener imagen
                imagen_tag = item.find('picture') or item.find('image') or item.find('Image')
                imagen = imagen_tag.text if imagen_tag is not None else ""
                
                # Obtener URL (ya incluye tu ID de afiliado)
                url_tag = item.find('url') or item.find('link') or item.find('URL')
                link = url_tag.text if url_tag is not None else ""
                
                if nombre and link:
                    ofertas.append({
                        'nombre': nombre[:100],
                        'precio': precio,
                        'precio_original': precio_original,
                        'descuento': descuento,
                        'imagen': imagen,
                        'link': link
                    })
            except Exception as e:
                continue
        
        ofertas.sort(key=lambda x: x['descuento'], reverse=True)
        print(f"🎯 Ofertas con {DESCUENTO_MINIMO}%+ descuento: {len(ofertas)}")
        return ofertas[:3]
    
    except Exception as e:
        print(f"❌ Error procesando feed: {e}")
        return []

async def publicar_ofertas():
    """Publica las mejores ofertas en el canal de Telegram"""
    print(f"\n[{datetime.now()}] 🔍 Buscando ofertas...")
    
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        
        # Obtener token de Admitad
        token = get_admitad_token()
        if not token:
            print("❌ No se pudo obtener token de Admitad")
            return
        
        # Obtener feeds disponibles
        feeds = get_feeds(token)
        if not feeds:
            print("❌ No hay feeds disponibles")
            return
        
        # Usar el primer feed disponible
        feed_url = feeds[0].get("url", "")
        if not feed_url:
            print("❌ URL del feed vacía")
            return
        
        # Obtener ofertas del feed
        ofertas = get_ofertas_desde_feed(feed_url)
        
        if not ofertas:
            print("⚠️ Sin ofertas con descuento suficiente por ahora")
            return
        
        # Publicar encabezado
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🔥 *OFERTAS DEL DÍA* 🔥\n📅 _{datetime.now().strftime('%d de %B, %Y')}_",
            parse_mode="Markdown"
        )
        
        # Publicar cada oferta
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
            except Exception as e:
                print(f"⚠️ Error enviando oferta: {e}")
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=mensaje,
                    parse_mode="Markdown"
                )
            
            await asyncio.sleep(2)
        
        print(f"✅ {len(ofertas)} ofertas publicadas exitosamente")
    
    except Exception as e:
        print(f"❌ Error general: {e}")

async def main():
    print("🤖 Bot de OfertasJG iniciado")
    print(f"📢 Canal: {CHANNEL_ID}")
    print(f"🔑 WEBSITE_ID: {WEBSITE_ID}")
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(publicar_ofertas, 'cron', hour=9,  minute=0)
    scheduler.add_job(publicar_ofertas, 'cron', hour=14, minute=0)
    scheduler.add_job(publicar_ofertas, 'cron', hour=20, minute=0)
    scheduler.start()
    
    await publicar_ofertas()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
