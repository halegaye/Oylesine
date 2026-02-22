import asyncio
import sqlite3
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- AYARLAR ---
# Takip edilecek ürünlerin listesi
PRODUCTS = [
    {
        "name": "Nowa Online World ATLAS 1M",
        "check_url": "https://www.klasgame.com/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold",
        "detail_url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-atlas-1m"
    },
    {
        "name": "Nowa Online World ULTIMATE 1M",
        "check_url": "https://www.klasgame.com/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold",
        "detail_url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-ultimate-1m"
    },
    {
        "name": "Nowa Online World ARES - 10 M",
        "check_url": "https://www.klasgame.com/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold",
        "detail_url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-10-m"
    },
    {
        "name": "Nowa Online World ARES - 10 GB",
        "check_url": "https://www.klasgame.com/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold",
        "detail_url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-10-gb"
    }
]

MY_TOKEN = '8406334532:AAHp9hve4OpST2CbolaFwee_oUNcyHtfEh8'
ADMIN_IDS = [5695472914, 6291821880] 
GROUP_ID = -5135054083

bot = Bot(token=MY_TOKEN)
dp = Dispatcher()

# --- VERİTABANI VE LOG FONKSİYONLARI ---
def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS pins (pin TEXT PRIMARY KEY, days INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, expire TEXT, username TEXT)')
    try: cursor.execute('ALTER TABLE users ADD COLUMN username TEXT')
    except: pass
    conn.commit()
    conn.close()

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

# --- SELENIUM ÇOKLU TAKİP DÖNGÜSÜ ---
async def check_loop():
    options = Options()
    options.add_argument("--headless") # Arka planda çalışması için (isteğe bağlı)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    
    # Her ürünün son durumunu takip etmek için bir sözlük
    last_states = {p["name"]: {"status": None, "price": None} for p in PRODUCTS}

    log("Takip döngüsü başlatıldı...")

    while True:
        for product in PRODUCTS:
            p_name = product["name"]
            try:
                # 1. Ana sayfadan buton kontrolü (Açık/Kapalı)
                driver.get(product["check_url"])
                # Sayfadaki tüm ürün butonlarını buluyoruz
                # Not: Klasgame'de buton metnine veya linkine göre filtreleme yapmamız gerekebilir
                # Burada detail_url'yi içeren butonu bulmaya çalışıyoruz:
                wait = WebDriverWait(driver, 10)
                buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-sell.button-top-animation")))
                
                target_btn = None
                for btn in buttons:
                    if product["detail_url"].split('/')[-1] in (btn.get_attribute("onclick") or ""):
                        target_btn = btn
                        break
                
                if not target_btn:
                    continue

                current_status = "kapali" if "Şu an için alış aktif görünmüyor" in (target_btn.get_attribute("onclick") or "") else "acik"
                current_price = "???"

                # 2. Eğer açıksa detay sayfasına git ve fiyat al
                if current_status == "acik":
                    driver.get(product["detail_url"])
                    p_el = WebDriverWait(driver, 7).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-label-value.unit-price")))
                    current_price = p_el.text.strip()

                # 3. Değişiklik Kontrolü ve Bildirim
                prev = last_states[p_name]
                
                # Durum Değiştiyse (Açıldı/Kapandı)
                if current_status != prev["status"]:
                    icon = "✅" if current_status == "acik" else "❌"
                    status_txt = "SATIŞ AKTİF" if current_status == "acik" else "SATIŞA KAPANDI"
                    msg = (f"{icon} **{p_name}**\n"
                           f"📢 Durum: **{status_txt}**\n"
                           f"💰 Alış: `{current_price}`\n"
                           f"🔗 [Hemen Sat]({product['detail_url']})")
                    await bot.send_message(GROUP_ID, msg, parse_mode="Markdown", disable_web_page_preview=True)
                    prev["status"] = current_status

                # Sadece Fiyat Değiştiyse
                elif current_status == "acik" and current_price != prev["price"] and prev["price"] is not None:
                    msg = f"🔄 **Fiyat Güncellendi**\n📦 {p_name}\n💰 Yeni Fiyat: `{current_price}`"
                    await bot.send_message(GROUP_ID, msg, parse_mode="Markdown")
                
                prev["price"] = current_price
                await asyncio.sleep(2) # Sayfalar arası kısa bekleme (Ban yememek için)

            except Exception as e:
                log(f"Hata ({p_name}): {e}")
                continue

        await asyncio.sleep(30) # Tüm liste bittikten sonra 30 sn bekle

# --- DİĞER FONKSİYONLAR (Aynı Kalıyor) ---
# ... (expiry_checker, admin komutları, start vb. yukarıdaki kodun aynısı) ...