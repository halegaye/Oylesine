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
CHECK_URL = "https://www.klasgame.com/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold"

# Senin verdiğin cookie metni
COOKIE_RAW = "f7a278a0c9779aa260eca8138105b3eb=1;PHPSESSID=mo4liuputu2bo47ep1vj07iiuq;4cb2f9b65921a3764f08be04dfcb3a44=1771779180__7NjkyMzE1NDM2NC41MVoySjhRLTNMUUY3LTVFSk45Njk5QjM0NkM3NzM3MjE3NzE3NzkxODA%3D;d5fe1054dca240652d5a0e04d957fa23=0fb4ff750a277215b35ab5868b4b1c1b;_gid=GA1.2.1423029145.1771779189;cbb6ed018c223b30b054b12420ecdfe7=https%3A%2F%2Fwww.klasgame.com%2Fmmorpg-oyunlar%2Fnowa-online-world%2Fnowa-online-world-gold;568d2c2a2914da32705508867db0b643=1;_gcl_au=1.1.672825474.1766333096.38780360.1771784782.1771784804;3f46be58e9e603958af6956de0b91395=Y;9a89e1f1a137fd1c68ba9e727856d032=ysf.krdmn2007%40gmail.com;d532c465722686b81f4a5ac1aded6fdf=hjklhjkl1;29f3203fae946d94ff2bf7428f0b61b4=d3a9dd1ffd2042491370d7d0e64e5358;_ga_25E93VLEHL=GS2.1.s1771784774$o20$g1$t1771784810$j24$l0$h0;_ga=GA1.1.1236675467.1758353954"

PRODUCTS = [
    {"name": "Nowa Online World ATLAS 1M", "index": 0, "url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-atlas-1m"},
    {"name": "Nowa Online World ULTIMATE 1M", "index": 1, "url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-ultimate-1m"},
    {"name": "Nowa Online World ARES - 10 M", "index": 2, "url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-10-m"},
    {"name": "Nowa Online World ARES - 10 GB", "index": 3, "url": "https://www.klasgame.com/satis-yap/mmorpg-oyunlar/nowa-online-world/nowa-online-world-gold/nowa-online-world-10-gb"}
]

MY_TOKEN = '8406334532:AAHp9hve4OpST2CbolaFwee_oUNcyHtfEh8'
ADMIN_IDS = [5695472914, 6291821880] 
GROUP_ID = -5135054083 # Başına -100 eklemeyi unutma kanka

bot = Bot(token=MY_TOKEN)
dp = Dispatcher()

# --- YARDIMCI FONKSİYONLAR ---
def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def add_cookies(driver):
    """Cookie metnini parçalar ve driver'a enjekte eder"""
    try:
        # 1. Önce siteye git (Domain kimliği oluşması için şart)
        driver.get("https://www.klasgame.com")
        log("Siteye ilk giriş yapıldı, çerezler enjekte ediliyor...")
        await_sleep(2) # Sayfanın oturması için kısa bekleme

        # 2. Tüm çerezleri temizle (Eski oturum kalmasın)
        driver.delete_all_cookies()

        # 3. Çerezleri parçala ve tek tek ekle
        cookies = COOKIE_RAW.split(';')
        for cookie in cookies:
            if '=' in cookie:
                # Cookie ismini ve değerini ayır
                parts = cookie.strip().split('=', 1)
                name = parts[0]
                value = parts[1]
                
                # Klasgame için kritik çerez ayarları
                cookie_dict = {
                    'name': name,
                    'value': value,
                    'domain': 'www.klasgame.com', # Domain'i netleştiriyoruz
                    'path': '/',
                }
                driver.add_cookie(cookie_dict)
        
        # 4. Çerezleri ekledikten sonra sayfayı YENİLE (Login'in aktif olması için)
        driver.refresh()
        log("Sayfa yenilendi, giriş kontrol ediliyor...")
        
        # 5. Opsiyonel: Giriş yapılıp yapılmadığını konsola bas (Görsel kontrol)
        if "Çıkış Yap" in driver.page_source:
            log("BAŞARILI: Hesaba giriş yapıldı!")
        else:
            log("UYARI: Giriş yapılamadı. Çerezlerin güncelliğini kontrol et.")
            
    except Exception as e:
        log(f"Çerez yükleme sırasında hata oluştu: {e}")

# Bu fonksiyonun loop içinde doğru çağrılması için ufak bir bekleme ekleyelim
import time
def await_sleep(seconds):
    time.sleep(seconds)
    
# --- VERİTABANI İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS pins (pin TEXT PRIMARY KEY, days INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, expire TEXT, username TEXT)')
    try: cursor.execute('ALTER TABLE users ADD COLUMN username TEXT')
    except: pass
    conn.commit()
    conn.close()

# --- SELENIUM TAKİP ---
async def check_loop():
    options = Options()
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    
    # 1. ADIM: Çerezleri yükle (Giriş yapılmış gibi davran)
    add_cookies(driver)
    
    last_states = {p["name"]: {"status": None, "price": None} for p in PRODUCTS}
    
    while True:
        try:
            driver.get(CHECK_URL)
            wait = WebDriverWait(driver, 20)
            buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-sell.button-top-animation")))

            for product in PRODUCTS:
                p_name = product["name"]
                p_idx = product["index"]
                p_url = product["url"]

                if len(buttons) > p_idx:
                    btn = buttons[p_idx]
                    onclick = btn.get_attribute("onclick") or ""
                    
                    current_status = "kapali" if "Şu an için alış aktif görünmüyor" in onclick else "acik"
                    current_price = "???"

                    if current_status == "acik":
                        try:
                            driver.get(p_url)
                            p_el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-label-value.unit-price")))
                            current_price = p_el.text.strip()
                            driver.get(CHECK_URL)
                            buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-sell.button-top-animation")))
                        except: pass

                    prev = last_states[p_name]

                    if current_status != prev["status"]:
                        icon = "✅ **SATIŞ AKTİF (Hesaplı)**" if current_status == "acik" else "❌ **KAPALI (Hesaplı)**"
                        msg = f"{icon}\n📦 **{p_name}**\n💰 Alış: `{current_price}`\n🔗 [Tıkla Sat]({p_url})"
                        await bot.send_message(GROUP_ID, msg, parse_mode="Markdown")
                        log(f"Grup Bildirimi: {p_name} -> {current_status}")
                        prev["status"] = current_status

                    if current_status == "acik" and current_price != prev["price"] and prev["price"] is not None:
                        await bot.send_message(GROUP_ID, f"💰 **Fiyat Güncellendi**\n📦 {p_name}\n💵 Yeni: `{current_price}`")
                        prev["price"] = current_price
                    
                    if prev["price"] is None: prev["price"] = current_price

        except Exception as e:
            log(f"Döngü hatası: {e}")
        
        await asyncio.sleep(30)

# --- (Diğer kısımlar: expiry_checker, bot komutları ve main aynı kalıyor) ---
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
                        log(f"Süresi dolan {username} gruptan atıldı.")
                    except: pass
            conn.commit()
            conn.close()
        except Exception as e: log(f"Hata (Expiry): {e}")
        await asyncio.sleep(60)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Bot Aktif! Pin girmek için `/pingiris PIN` kullanın.")

@dp.message(Command("pingiris"))
async def cmd_pin_giris(message: types.Message):
    if message.chat.type != "private": return
    parts = message.text.split()
    if len(parts) < 2: return await message.reply("Kullanım: `/pingiris PIN`")
    pin_input = parts[1].strip()
    conn = sqlite3.connect("data.db"); cursor = conn.cursor()
    cursor.execute("SELECT days FROM pins WHERE pin = ?", (pin_input,))
    res = cursor.fetchone()
    if res:
        days = res[0]
        expire_date = (datetime.now() + timedelta(minutes=1 if days == -1 else days*1440)).strftime('%Y-%m-%d %H:%M')
        cursor.execute("INSERT OR REPLACE INTO users (uid, expire, username) VALUES (?,?,?)", (message.from_user.id, expire_date, message.from_user.username))
        cursor.execute("DELETE FROM pins WHERE pin = ?", (pin_input,))
        conn.commit()
        link = await bot.create_chat_invite_link(GROUP_ID, member_limit=1, expire_date=datetime.now() + timedelta(minutes=5))
        await message.reply(f"✅ Üyelik aktif!\n📅 Bitiş: {expire_date}\n🔗 Link: {link.invite_link}")
    else:
        await message.reply("❌ Hatalı pin.")
    conn.close()

@dp.message(Command("1aypin"))
async def cmd_1ay(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    pins = [p.strip() for p in message.text.split(maxsplit=1)[1].split(",")]
    conn = sqlite3.connect("data.db")
    for p in pins: conn.execute("INSERT INTO pins VALUES (?,?)", (p, 30))
    conn.commit(); conn.close()
    await message.reply("Eklendi.")

async def main():
    init_db()
    asyncio.create_task(check_loop())
    asyncio.create_task(expiry_checker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())