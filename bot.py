import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
import os

# Librerías externas necesarias (Asegúrate de instalarlas)
import httpx 
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# ========================================
# CONFIGURACIÓN — Lee de variables de entorno
# ========================================
TELEGRAM_TOKEN = "8641134190:AAHH96wQ5H3_TJjYfKK1meCJ5Cu-hMl4EuI"
CHANNEL_ID = "@OfertasJG"
ADMITAD_BASE64 = "ZGc4bHhlOEZHSVROZXlzeE9XcWpEbU05akxjNmUwOjh6QWRMNW5LbDBSdFE2RXpqcnVuWWlSWkZaeHhSZg=="
WEBSITE_ID = "2943808"
DESCUENTO_MINIMO = 5
# ========================================
# Memoria temporal para evitar enviar ofertas repetidas en ejecuciones seguidas
PRODUCTOS_ENVIADOS = []
# ========================================

async def get_admitad_token():
    """Obtiene token de acceso de Admitad (Asíncrono)"""
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
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, data=data, timeout=15)
            r.raise_for_status()
            token = r.json().get("access_token")
            print(f"✅ Token obtenido: {token[:10]}..." if token else "❌ No se obtuvo token")
            return token
    except Exception as e:
        print(f"❌ Error obteniendo token: {e}")
        return None

async def get_feeds(token):
    """Obtiene la lista de feeds disponibles (Asíncrono)"""
    try:
        url = "https://api.admitad.com/feeds/"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"website": WEBSITE_ID, "limit": 10}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, params=params, timeout=15)
            r.raise_for_status()
            feeds = r.json().get("results", [])
            print(f"📦 Feeds encontrados: {len(feeds)}")
            for f in feeds:
                print(f"  - {f.get('name')} | URL: {f.get('url')}")
            return feeds
    except Exception as e:
        print(f"❌ Error obteniendo feeds: {e}")
        return []

async def get_ofertas_desde_feed(feed_url):
    """Descarga y procesa el feed XML de productos sin bloquear el loop"""
    global PRODUCTOS_ENVIADOS
    try:
        print(f"📥 Descargando feed: {feed_url}")
        async with httpx.AsyncClient() as client:
            r = await client.get(feed_url, timeout=60)
            r.raise_for_status()
            
        # Parseo XML en memoria
        root = ET.fromstring(r.content)
        
        ofertas = []
        items = root.findall('.//offer') or root.findall('.//item') or root.findall('.//product')
        print(f"🔍 Productos encontrados en XML: {len(items)}")
        
        for item in items:
            try:
                precio_tag = item.find('price') or item.find('Price')
                precio = float(precio_tag.text or 0) if precio_tag is not None else 0
                
                oldprice_tag = item.find('oldprice') or item.find('old_price') or item.find('compare_at_price')
                precio_original = float(oldprice_tag.text or precio) if oldprice_tag is not None else precio
                
                if precio_original > precio and precio > 0:
                    descuento = round(((precio_original - precio) / precio_original) * 100)
                else:
                    descuento = 0
                
                if descuento < DESCUENTO_MINIMO:
                    continue
                
                nombre_tag = item.find('name') or item.find('title') or item.find('Name')
                nombre = nombre_tag.text if nombre_tag is not None else "Producto"
                
                imagen_tag = item.find('picture') or item.find('image') or item.find('Image')
                imagen = imagen_tag.text if imagen_tag is not None else ""
                
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
            except Exception:
                continue
        
        # Ordenamos por mayor descuento primero
        ofertas.sort(key=lambda x: x['descuento'], reverse=True)
        
        # FILTRO: Evitamos repetir lo que ya se envió en las últimas horas
        ofertas_nuevas = [o for o in ofertas if o['link'] not in PRODUCTOS_ENVIADOS]
        print(f"🎯 Ofertas con descuento válido: {len(ofertas)} | Nuevas sin enviar: {len(ofertas_nuevas)}")
        
        # Seleccionamos el top 3 de las nuevas
        seleccionadas = ofertas_nuevas[:3]
        
        # Guardamos en el historial para la siguiente vuelta
        for o in seleccionadas:
            PRODUCTOS_ENVIADOS.append(o['link'])
            
        # Controlamos que la lista en memoria no crezca infinitamente (mantiene las últimas 300)
        if len(PRODUCTOS_ENVIADOS) > 300:
            PRODUCTOS_ENVIADOS = PRODUCTOS_ENVIADOS[-300:]
            
        return seleccionadas
    
    except Exception as e:
        print(f"❌ Error procesando feed: {e}")
        return []

async def publicar_ofertas():
    """Publica las mejores ofertas en el canal de Telegram"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 Iniciando búsqueda automática de ofertas...")
    
    try:
        # 1. Obtener Token
        token = await get_admitad_token()
        if not token: return
        
        # 2. Obtener Feeds
        feeds = await get_feeds(token)
        if not feeds: return
        
        feed_url = feeds[0].get("url", "")
        if not feed_url: return
        
        # 3. Obtener Ofertas filtradas
        ofertas = await get_ofertas_desde_feed(feed_url)
        if not ofertas:
            print("⚠️ No se encontraron ofertas nuevas con suficiente descuento en esta vuelta.")
            return

        # 4. Enviar a Telegram mediante Contexto Asíncrono seguro
        async with Bot(token=TELEGRAM_TOKEN) as bot:
            
            # Publicar encabezado común (Formato HTML seguro)
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"🔥 <b>NUEVAS OFERTAS DETECTADAS</b> 🔥\n📅 <i>{datetime.now().strftime('%d/%m/%Y - %H:%M')}</i>",
                parse_mode=ParseMode.HTML
            )
            
            # Publicar de forma individual cada oferta
            for oferta in ofertas:
                mensaje = (
                    f"🛍️ <b>{oferta['nombre']}</b>\n\n"
                    f"💰 <s>${oferta['precio_original']:,.0f}</s> → <b>${oferta['precio']:,.0f}</b>\n"
                    f"🔥 <b>{oferta['descuento']}% de DESCUENTO</b>\n\n"
                    f"🛒 <a href='{oferta['link']}'>Ver oferta aquí</a>"
                )
                
                try:
                    if oferta.get('imagen'):
                        await bot.send_photo(
                            chat_id=CHANNEL_ID,
                            photo=oferta['imagen'],
                            caption=mensaje,
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=mensaje,
                            parse_mode=ParseMode.HTML
                        )
                except Exception as e:
                    print(f"⚠️ Error enviando foto/formato: {e}. Reintentando solo texto por seguridad...")
                    try:
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=mensaje,
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e_critico:
                        print(f"❌ Error crítico, no se pudo enviar el mensaje: {e_critico}")
                
                # Pausa de cortesía para no saturar las políticas antispam de Telegram
                await asyncio.sleep(2)
            
            print(f"✅ {len(ofertas)} ofertas publicadas con éxito.")
            
    except Exception as e:
        print(f"❌ Error general en ciclo de publicación: {e}")

async def main():
    print("🤖 Bot de Ofertas automatizado iniciado.")
    print(f"📢 Destino: {CHANNEL_ID}")
    
    # Configuramos el planificador para ejecutarse cada 10 minutos
    scheduler = AsyncIOScheduler()
    scheduler.add_job(publicar_ofertas, 'interval', minutes=10)
    scheduler.start()
    print("⏰ Planificador activo: Buscando chollos cada 10 minutos.")
    
    # Primera ejecución manual nada más encender el bot para no esperar 10 mins
    await publicar_ofertas()
    
    # Mantiene vivo el bucle asíncrono del script
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    # Recordatorio de instalación: pip install httpx python-telegram-bot apscheduler
    asyncio.run(main())
