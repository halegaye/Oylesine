import asyncio
import sqlite3
from datetime import datetime, timedelta
import random
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- AYARLAR ---
CHECK_URL = "https://www.klasgame.com/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold"
LOOP_INTERVAL = 10  # 10 Saniyede bir tarama yapacak

COOKIE_RAW = "PHPSESSID=kl1rjo0818ibtoqnm3opmqnonl;4cb2f9b65921a3764f08be04dfcb3a44=1785005400__5MTQxODI3NDcwNVVHRDBNLTJFUTNUSS0ySzc3Vjc2QTY1MDU1ODAyMDRGMTc4NTAwNTQwMA%3D%3D;d5fe1054dca240652d5a0e04d957fa23=58665b8d6d881b278f3f532140461f44;f7a278a0c9779aa260eca8138105b3eb=1;_gid=GA1.2.1278223595.1785005401;cbb6ed018c223b30b054b12420ecdfe7=https%3A%2F%2Fwww.klasgame.com%2Fmmorpg-oyunlar%2Fmyko-mobile%2Fmyko-mobile-gold;_gcl_au=1.1.1917313180.1785005401.1561725577.1785007214.1785007216.1831945362.1785007214.1785007216;3f46be58e9e603958af6956de0b91395=Y;9a89e1f1a137fd1c68ba9e727856d032=ysf.krdmn2007%40gmail.com;d532c465722686b81f4a5ac1aded6fdf=Hjklhjkl1;29f3203fae946d94ff2bf7428f0b61b4=d3a9dd1ffd2042491370d7d0e64e5358;_ga_25E93VLEHL=GS2.1.s1785005401$o1$g1$t1785007220$j46$l0$h0;_ga=GA1.1.2075272725.1785005401;klc_btoken=6gbu1sq8c6etv2i53uscunolnwkgjt04"

PRODUCTS = [
    {"name": "Nowa Online World ATLAS 1M", "index": 0, "url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-atlas-1m"},
    
    {"name": "Nowa Online World ARES - 10 M", "index": 2, "url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-10-m"},
    {"name": "Nowa Online World ARES - 10 GB", "index": 3, "url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-10-gb"}
]

MY_TOKEN = '8406334532:AAHp9hve4OpST2CbolaFwee_oUNcyHtfEh8'
ADMIN_IDS = [5695472914, 6291821880] 
GROUP_ID = -5135054083

bot = Bot(token=MY_TOKEN)
dp = Dispatcher()

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def create_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(15) 
    return driver

async def inject_cookies(driver):
    try:
        driver.get("https://www.klasgame.com")
        await asyncio.sleep(2)
        driver.delete_all_cookies()

        cookie_list = COOKIE_RAW.split(';')
        added_count = 0

        for item in cookie_list:
            item = item.strip()
            if not item or '=' not in item:
                continue
            name, value = item.split('=', 1)
            cookie_dict = {
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.klasgame.com',
                'path': '/'
            }
            try:
                driver.add_cookie(cookie_dict)
                added_count += 1
            except Exception:
                pass

        log(f"🔑 {added_count} adet çerez enjekte edildi.")
        driver.refresh()
        await asyncio.sleep(2)

        if "Çıkış Yap" in driver.page_source or "Hesabım" in driver.page_source:
            log("✅ BAŞARILI: Çerezler aktif, hesaba giriş yapıldı!")
            return True
        else:
            log("⚠️ UYARI: Hesaba giriş görünmüyor. Çerezleri tazelemek gerekebilir.")
            return False
    except Exception as e:
        log(f"🚨 Çerez enjeksiyon hatası: {e}")
        return False

# --- SELENIUM ANA DÖNGÜ ---
async def check_loop():
    driver = None
    # Başlangıçta durumları None yapıyoruz ki ilk taramada mevcut durumu hafızaya alsın, durduk yere eski veriyi tetiklemesin
    last_states = {p["name"]: {"status": None, "price": None} for p in PRODUCTS}

    while True:
        try:
            if driver is None:
                log("🌐 Tarayıcı başlatılıyor...")
                driver = create_driver()
                await inject_cookies(driver)

            driver.get(CHECK_URL)
            wait = WebDriverWait(driver, 10)
            buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-sell.button-top-animation")))

            for product in PRODUCTS:
                p_name = product["name"]
                p_idx = product["index"]
                p_url = product["url"]

                if len(buttons) > p_idx:
                    btn = buttons[p_idx]
                    onclick = btn.get_attribute("onclick") or ""
                    
                    # Butonun durumunu tespit et
                    current_status = "kapali" if "Şu an için alış aktif görünmüyor" in onclick else "acik"
                    prev = last_states[p_name]

                    # Eğer durum değiştiyse (Örn: kapaliydı acik oldu, ya da acikti kapali oldu)
                    if prev["status"] is not None and current_status != prev["status"]:
                        
                        # 1. Kural: KAPALI OLAN BUTON AÇILIRSA
                        if current_status == "acik":
                            current_price = "???"
                            try:
                                # Fiyatı çekmek için ürün detayına git
                                driver.get(p_url)
                                p_el = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-label-value.unit-price")))
                                current_price = p_el.text.strip()
                                
                                # Ana sayfaya geri dön ve butonları tazele
                                driver.get(CHECK_URL)
                                buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-sell.button-top-animation")))
                            except Exception as inner_e:
                                log(f"Fiyat çekilemedi ({p_name}): {inner_e}")

                            msg = f"✅ **SATIŞ AKTİF OLMUŞTUR! (Buton Açıldı)**\n📦 **{p_name}**\n💰 Alış Fiyatı: `{current_price}`\n🔗 [Hemen Satışa Git]({p_url})"
                            log(f"🔔 Durum Değişti (AÇILDI): {p_name}")
                            prev["price"] = current_price

                        # 2. Kural: AÇIK OLAN BUTON KAPANIRSA
                        else:
                            msg = f"❌ **SATIŞ KAPANMIŞTIR! (Buton Kapandı)**\n📦 **{p_name}**"
                            log(f"🔔 Durum Değişti (KAPANDI): {p_name}")

                        # Gruba bildirimi gönder
                        try:
                            await bot.send_message(GROUP_ID, msg, parse_mode="Markdown")
                        except Exception as te:
                            log(f"Telegram Mesaj Hatası: {te}")

                    # Eğer buton açıksa ve fiyatta bir güncelleme olduysa (Durum değişmeden sadece fiyat değişirse)
                    elif current_status == "acik" and prev["status"] == "acik":
                        try:
                            driver.get(p_url)
                            p_el = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-label-value.unit-price")))
                            current_price = p_el.text.strip()
                            
                            if prev["price"] is not None and current_price != prev["price"]:
                                await bot.send_message(GROUP_ID, f"💰 **Fiyat Güncellendi!**\n📦 {p_name}\n💵 Yeni Fiyat: `{current_price}`", parse_mode="Markdown")
                                prev["price"] = current_price
                            
                            driver.get(CHECK_URL)
                            buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-sell.button-top-animation")))
                        except Exception:
                            pass

                    # Hafızayı güncelle
                    prev["status"] = current_status
                    if prev["price"] is None and current_status == "acik":
                        # İlk açılışta fiyatı eşitlemek için
                        prev["price"] = "???"

        except Exception as e:
            log(f"💥 Hata oluştu: {e}")
            log("🔄 Sürücü sıfırlanıyor, 5 saniye sonra döngü devam edecek...")
            if driver:
                try: driver.quit()
                except Exception: pass
                driver = None
            await asyncio.sleep(5)
            continue

        await asyncio.sleep(LOOP_INTERVAL)

# --- VERİTABANI İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS pins (pin TEXT PRIMARY KEY, days INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, expire TEXT, username TEXT)')
    conn.commit()
    conn.close()

async def expiry_checker():
    while True:
        try:
            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()
            now = datetime.now()
            cursor.execute("SELECT uid, expire, username FROM users")
            rows = cursor.fetchall()
            for uid, expire_str, username in rows:
                if uid in ADMIN_IDS: continue
                expire_dt = datetime.strptime(expire_str, '%Y-%m-%d %H:%M')
                if now > expire_dt:
                    try:
                        await bot.ban_chat_member(GROUP_ID, uid)
                        await bot.unban_chat_member(GROUP_ID, uid)
                        cursor.execute("DELETE FROM users WHERE uid = ?", (uid,))
                        log(f"🚫 Süresi biten {username} gruptan çıkartıldı.")
                    except Exception: pass
            conn.commit()
            conn.close()
        except Exception: pass
        await asyncio.sleep(60)

# --- BOT KOMUTLARI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Bot Aktif! Pin girmek için `/pingiris PIN` kullanın kanka.")

@dp.message(Command("pingiris"))
async def cmd_pin_giris(message: types.Message):
    if message.chat.type != "private": return
    parts = message.text.split()
    if len(parts) < 2: return await message.reply("Kullanım: `/pingiris PIN`")
    pin_input = parts[1].strip()
    
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT days FROM pins WHERE pin = ?", (pin_input,))
    res = cursor.fetchone()
    if res:
        days = res[0]
        expire_date = (datetime.now() + timedelta(minutes=1 if days == -1 else days*1440)).strftime('%Y-%m-%d %H:%M')
        cursor.execute("INSERT OR REPLACE INTO users (uid, expire, username) VALUES (?,?,?)", (message.from_user.id, expire_date, message.from_user.username))
        cursor.execute("DELETE FROM pins WHERE pin = ?", (pin_input,))
        conn.commit()
        
        link = await bot.create_chat_invite_link(GROUP_ID, member_limit=1, expire_date=datetime.now() + timedelta(minutes=5))
        await message.reply(f"✅ Üyelik onaylandı!\n📅 Süre Bitişi: {expire_date}\n🔗 Davet Linki: {link.invite_link}")
    else:
        await message.reply("❌ Geçersiz PIN.")
    conn.close()

async def main():
    init_db()
    asyncio.create_task(check_loop())
    asyncio.create_task(expiry_checker())
    log("🔥 Kesintisiz 10 saniyelik buton durum takip motoru aktif edildi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())