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
CHECK_URL = "https://www.klasgame.com/revenger-online/revenger-online-gold"
SALES_DETAIL_URL = "https://www.klasgame.com/satis-yap/revenger-online/revenger-online-gold/revenger-online-1m"

MY_TOKEN = '7453834823:AAHUQNj727_TzXRG4o-ZYCuMM5TmdLTtK5c'
ADMIN_IDS = [5695472914, 6291821880] 
GROUP_ID = -1003568382481 

bot = Bot(token=MY_TOKEN)
dp = Dispatcher()

# --- VERİTABANI İŞLEMLERİ (Hata Korumalı) ---
def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS pins (pin TEXT PRIMARY KEY, days INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, expire TEXT, username TEXT)')
    
    # Sütun hatasını önlemek için kontrol
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN username TEXT')
    except: pass
    
    conn.commit()
    conn.close()

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

# --- SÜRE KONTROLÜ VE OTOMATİK KİCK (1 DAKİKADA BİR KONTROL) ---
# --- SÜRE KONTROLÜ VE OTOMATİK KİCK ---
# --- SÜRE KONTROLÜ, OTOMATİK KİCK VE ADMİN BİLGİLENDİRME ---
async def expiry_checker():
    while True:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("SELECT uid, expire, username FROM users")
        rows = cursor.fetchall()
        
        for uid, expire_str, username in rows:
            if uid in ADMIN_IDS: continue # Adminler muaf
            
            expire_dt = datetime.strptime(expire_str, '%Y-%m-%d %H:%M')
            if now > expire_dt:
                uname_info = f"@{username}" if username else f"ID: {uid}"
                log(f"Süresi dolan tespit edildi: {uname_info}")

                # 1. KULLANICIYA MESAJ GÖNDER
                try:
                    await bot.send_message(
                        uid, 
                        "❌ **Üyeliğinizin süresi dolmuştur.**\nGruptan otomatik olarak çıkarıldınız. Yeni pin alarak tekrar katılabilirsiniz.",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    log(f"Kullanıcıya mesaj iletilemedi (Botu engellemiş olabilir): {e}")

                # 2. ADMİNLERE RAPOR VER
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id, 
                            f"🔔 **Süre Sonu Bilgilendirmesi**\n\n👤 Kullanıcı: {uname_info}\n🆔 ID: `{uid}`\n📅 Bitiş Tarihi: {expire_str}\n\n🚫 Bu kullanıcı süresi dolduğu için gruptan atıldı.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        log(f"Admine rapor iletilemedi: {e}")

                # 3. GRUPTAN AT VE VERİTABANINDAN SİL
                try:
                    await bot.ban_chat_member(GROUP_ID, uid)
                    await bot.unban_chat_member(GROUP_ID, uid)
                    cursor.execute("DELETE FROM users WHERE uid = ?", (uid,))
                    log(f"Kullanıcı {uname_info} gruptan atıldı ve DB'den silindi.")
                except Exception as e:
                    log(f"Gruptan atma hatası ({uname_info}): {e}")
                    
        conn.commit()
        conn.close()
        await asyncio.sleep(30) # 30 saniyede bir kontrol (Testler için ideal)

# --- ADMİN PANELİ KOMUTLARI ---

@dp.message(Command("1dkpin"))
async def cmd_add_1dk_pin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.reply("Kullanım: /1dkpin pin1, pin2")
    pins = [p.strip() for p in parts[1].split(",")]
    
    conn = sqlite3.connect("data.db")
    for p in pins:
        if p: conn.execute("INSERT OR IGNORE INTO pins VALUES (?,?)", (p, -1)) # -1 işaretliyoruz
    conn.commit()
    conn.close()
    await message.reply(f"✅ {len(pins)} adet **1 dakikalık** test pini eklendi.")

@dp.message(Command("kullanicilar"))
async def cmd_kullanicilar(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT uid, expire, username FROM users")
    rows = cursor.fetchall()
    conn.close()
    if not rows: return await message.reply("Kayıtlı kullanıcı yok.")
    
    rapor = f"📊 **Aktif Üyeler ({len(rows)} kişi)**\n\n"
    for uid, expire, username in rows:
        uname = f"@{username}" if username else "Adı Yok"
        rapor += f"👤 {uname} (`{uid}`)\n⏳ Bitiş: {expire}\n---\n"
    await message.answer(rapor, parse_mode="Markdown")

@dp.message(Command("1aypin", "3aypin", "6aypin"))
async def add_pins(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    days = 30 if "1ay" in message.text else 90 if "3ay" in message.text else 180
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.reply("Kullanım: /1aypin pin1, pin2")
    pins = [p.strip() for p in parts[1].split(",")]
    conn = sqlite3.connect("data.db")
    for p in pins: conn.execute("INSERT OR IGNORE INTO pins VALUES (?,?)", (p, days))
    conn.commit()
    conn.close()
    await message.reply(f"✅ {len(pins)} adet pin havuzuna eklendi.")

# --- KULLANICI PİN GİRİŞİ ---

# --- PİN GİRİŞİ (TEK KULLANIMLIK LİNK ÜRETİMİ) ---
@dp.message(Command("pingiris"))
async def cmd_pin_giris(message: types.Message):
    if message.chat.type != "private": return
    parts = message.text.split()
    if len(parts) < 2: return await message.reply("Kullanım: `/pingiris PIN_KODU`", parse_mode="Markdown")
    
    pin_input = parts[1].strip()
    conn = sqlite3.connect("data.db"); cursor = conn.cursor()
    cursor.execute("SELECT days FROM pins WHERE pin = ?", (pin_input,))
    res = cursor.fetchone()
    
    if res:
        days = res[0]
        expire_date = (datetime.now() + timedelta(minutes=1 if days == -1 else days*1440)).strftime('%Y-%m-%d %H:%M')
            
        cursor.execute("INSERT OR REPLACE INTO users (uid, expire, username) VALUES (?,?,?)", 
                       (message.from_user.id, expire_date, message.from_user.username))
        cursor.execute("DELETE FROM pins WHERE pin = ?", (pin_input,))
        conn.commit()
        
        try:
            # KRİTİK AYAR: member_limit=1 (Sadece 1 kişi) ve expire_date (5 dk sonra link ölür)
            link = await bot.create_chat_invite_link(
                GROUP_ID, 
                member_limit=1, 
                expire_date=datetime.now() + timedelta(minutes=5)
            )
            await message.reply(f"✅ Başarılı! Üyeliğiniz onaylandı.\n📅 Bitiş: {expire_date}\n\n⚠️ Bu link TEK KULLANIMLIKTIR ve 5 dakika geçerlidir:\n🔗 {link.invite_link}")
        except Exception as e:
            await message.reply(f"✅ Onaylandı! Ancak link oluşturulamadı. Lütfen admine yazın.")
            log(f"Link hatası: {e}")
    else:
        await message.reply("❌ Hatalı veya kullanılmış pin.")
    conn.close()

# --- START KOMUTU (DİNAMİK KARŞILAMA) ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Kullanıcı admin mi kontrol et
    is_admin = message.from_user.id in ADMIN_IDS
    
    welcome_text = (
        f"👋 **Merhaba {message.from_user.first_name}!**\n\n"
        "Revenger Online Gold takip sistemine hoş geldin. "
        "Bu bot ile stok ve fiyat değişimlerini anlık olarak takip edebilirsin.\n\n"
        "📌 **Nasıl Kullanılır?**\n"
        "Eğer bir E-Pin'in varsa `/pingiris PIN_KODUNUZ` komutuyla üyeliğini başlatabilirsin. "
        "Üyeliğin onaylandığında sana gruba katılman için **tek kullanımlık** bir link göndereceğim.\n\n"
        "📜 **Kullanıcı Komutları:**\n"
        "🔹 `/pingiris <pin>` - Üyeliği başlatır.\n"
        "🔹 `/sure` - Kalan üyelik süreni gösterir.\n"
    )

    if is_admin:
        welcome_text += (
            "\n⚡ **Admin Paneli Komutları:**\n"
            "🔸 `/1aypin <pin1,pin2...>` - 30 günlük pin ekler.\n"
            "🔸 `/3aypin <pin1,pin2...>` - 90 günlük pin ekler.\n"
            "🔸 `/6aypin <pin1,pin2...>` - 180 günlük pin ekler.\n"
            "🔸 `/1dkpin <pin>` - 1 dakikalık TEST pini ekler.\n"
            "🔸 `/kullanicilar` - Aktif üyeleri listeler.\n"
            "🔸 `/duyuru` - (Foto altına yazılır) Herkese mesaj atar."
        )

    await message.reply(welcome_text, parse_mode="Markdown")

# --- SELENIUM TAKİP ---
async def check_loop():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    last_status, last_price = None, None
    while True:
        try:
            driver.get(CHECK_URL)
            btn = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "product-sell.button-top-animation")))
            current_status = "kapali" if "Şu an için alış aktif görünmüyor" in (btn.get_attribute("onclick") or "") else "acik"
            current_price = "???"
            if current_status == "acik":
                try:
                    driver.get(SALES_DETAIL_URL)
                    p_el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-label-value.unit-price")))
                    current_price = p_el.text.strip()
                except: pass
            if current_status != last_status:
                msg = f"{'✅ **SATIŞ AKTİF**' if current_status == 'acik' else '❌ **KAPALI**'}\n💰 Alış: {current_price}\n🔗 [Tıkla Sat]({SALES_DETAIL_URL})"
                await bot.send_message(GROUP_ID, msg, parse_mode="Markdown")
                last_status = current_status
            if current_status == "acik" and current_price != last_price and last_price is not None:
                await bot.send_message(GROUP_ID, f"💰 **Fiyat Güncellendi:** {current_price}")
                last_price = current_price
            if last_price is None: last_price = current_price
        except: pass
        await asyncio.sleep(20)

async def main():
    init_db()
    asyncio.create_task(check_loop())
    asyncio.create_task(expiry_checker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())