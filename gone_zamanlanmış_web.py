import base64
from io import BytesIO
import os
import json
import asyncio
import threading
import aiohttp
from datetime import datetime, timedelta, timezone
import mariadb
import mysql.connector  # Artık kullanılmasa da korunuyor

# Flask (Telegram Mini App İçeriğini Barındırmak İçin)
from flask import Flask, render_template_string, request, jsonify

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest

# ================== Telegram ==================
TOKEN = "8998840361:AAFo0zlNHBjyEG2ifaN1UilbSadIyVX4bOs" 
CHANNEL_USERNAME = "@Kankadenemedir"

# 🌐 TELEGRAM MINI APP PANEL LİNKİNİZ
WEB_APP_URL = " https://1fb5-94-55-16-47.ngrok-free.app".strip()

# ================== Betco API ==================
BETCO_TOKEN = "caa44f6274c3479fc69f8f1219227053c0e19492ff63f6f3a0194eb51661f234"
BETCO_GET_CLIENTS_URL = "https://backofficewebadmin.betcostatic.com/api/tr/Client/GetClients"
BETCO_ADD_CLIENT_BONUS_URL = "https://backofficewebadmin.betcostatic.com/api/tr/Client/AddClientToBonus"

# ================== Token Yönetimi ve DB Config ==================
ADMIN_IDS = [5695472914, 5947341902, 805254965, 1782604827, 8423465949]
SPECIAL_GROUP_ID = -4876211377 

last_token_change = None

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "root",
    "password": "root",
    "database": "101"
}

BONUS_USERS_FILE = "bonus_users.json"
USERS_FILE = "users.json"
DRAFT_FILE = "drafts.json"
BONUS_CONFIG_FILE = "bonuses.json"
SCHEDULED_FILE = "scheduled_broadcasts.json"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Varsayılan Bonus Ayarları
DEFAULT_BONUS_CONFIG = {
    "freespin": {
        "label": "🎰 500 FreeSpin",
        "PartnerBonusId": 604382,
        "Amount": "500"
    },
    "freebet": {
        "label": "⚽ 50 FreeBet",
        "PartnerBonusId": 604383,
        "Amount": "50"
    }
}

print("🚀 Sistem ve Telegram Mini App paneli başlatılıyor...")

# ---- Global Bot Referansı ----
telegram_app = None
# Global event loop referansı
telegram_loop = None

# ================== Bonus Config Fonksiyonları ==================
def load_bonus_config():
    if not os.path.exists(BONUS_CONFIG_FILE):
        save_bonus_config(DEFAULT_BONUS_CONFIG)
        return DEFAULT_BONUS_CONFIG
    try:
        with open(BONUS_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Bonus ayarları okunamadı: {e}")
        return DEFAULT_BONUS_CONFIG

def save_bonus_config(config):
    try:
        with open(BONUS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Bonus ayarları kaydedilemedi: {e}")

# ================== Zamanlanmış Duyuru Fonksiyonları ==================
def load_scheduled_broadcasts():
    if not os.path.exists(SCHEDULED_FILE):
        return []
    try:
        with open(SCHEDULED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_scheduled_broadcasts(data):
    try:
        with open(SCHEDULED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Zamanlanmış duyurular kaydedilemedi: {e}")

# ---- Dosya / İstatistik Fonksiyonları ----
def get_user_counts():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            u_list = json.load(f)
    except Exception:
        u_list = []

    total = 0
    active = 0
    blocked = 0
    last_24h = 0
    last_7d = 0

    now = datetime.now()

    for u in u_list:
        if isinstance(u, dict):
            total += 1
            if u.get("status") == "active":
                active += 1
            elif u.get("status") == "blocked":
                blocked += 1
            else:
                active += 1 # Varsayılan aktif

            # Zaman filtreleri
            join_date_str = u.get("join_date")
            if join_date_str:
                try:
                    join_date = datetime.strptime(join_date_str, "%Y-%m-%d %H:%M:%S")
                    diff = now - join_date
                    if diff <= timedelta(days=1):
                        last_24h += 1
                    if diff <= timedelta(days=7):
                        last_7d += 1
                except ValueError:
                    pass
        else:
            total += 1
            active += 1

    return {
        "total": total,
        "active": active,
        "blocked": blocked,
        "last_24h": last_24h,
        "last_7d": last_7d
    }

def has_taken_bonus(user_id: int) -> bool:
    try:
        with open(BONUS_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return user_id in data
    except FileNotFoundError:
        return False

def mark_bonus_given(user_id: int):
    try:
        with open(BONUS_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    if user_id not in data:
        data.append(user_id)
        with open(BONUS_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def save_user(user_id: int):
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

# ================== /settoken Komutu ==================
async def set_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BETCO_TOKEN, last_token_change
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id != SPECIAL_GROUP_ID and (update.effective_chat.type != "private" or user_id not in ADMIN_IDS):
        await update.message.reply_text("❌ Bu komutu kullanmaya yetkiniz yok!")
        return
    if not context.args:
        await update.message.reply_text("❌ Kullanım: /settoken <yeni_token>")
        return

    BETCO_TOKEN = context.args[0].strip()
    last_token_change = datetime.now(timezone.utc)
    await update.message.reply_text("✅ Betco token başarıyla güncellendi!")

# ================== 10 Saat Sonra Hatırlatma Task ==================
async def token_reminder_task(app):
    global last_token_change
    while True:
        if last_token_change:
            now = datetime.now(timezone.utc)
            if now - last_token_change >= timedelta(hours=10):
                for admin_id in ADMIN_IDS:
                    try:
                        await app.bot.send_message(admin_id, "⚠️ Betco token 10 saat oldu, güncellemeniz gerekebilir!")
                    except Exception as e:
                        print(f"Mesaj gönderilemedi: {e}")
                last_token_change = None 
        await asyncio.sleep(60 * 60)

# ================== Zamanlanmış Duyuru Takip Görevi ==================
async def scheduled_broadcast_task(app):
    while True:
        try:
            scheduled_items = load_scheduled_broadcasts()
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%dT%H:%M")
            items_to_send = []

            for item in scheduled_items:
                if item.get("status") == "pending":
                    send_time = item.get("send_time")
                    if send_time and send_time <= now_str:
                        # Status'u tamamlandı olarak işaretle ve yürütülme zamanını yaz
                        item["status"] = "completed"
                        item["executed_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
                        items_to_send.append(item)

            if items_to_send:
                # 🚀 ANINDA KAYDET: Web panelde bekleme durumu hemen "Gönderildi / Geçmiş"e geçsin
                save_scheduled_broadcasts(scheduled_items)

                for item in items_to_send:
                    print(f"⏰ [ZAMANLANMIŞ DUYURU] Otomatik gönderim başlatıldı! (ID: {item.get('id')})")
                    try:
                        with open(USERS_FILE, "r", encoding="utf-8") as f:
                            all_users = json.load(f)
                        
                        u_list = [u for u in all_users if isinstance(u, dict) and u.get("status") != "blocked"]
                        for u in all_users:
                            if not isinstance(u, dict):
                                u_list.append(u)

                        if u_list:
                            await send_bulk_message(u_list, item.get("message", ""), item.get("photo", ""))
                    except Exception as e:
                        print(f"❌ Zamanlanmış duyuru gönderim hatası ({item.get('id')}): {e}")

        except Exception as e:
            print(f"⚠️ Scheduled broadcast task hatası: {e}")

        await asyncio.sleep(15)  # 15 saniyede bir hızlı kontrol

# ---- Betco API Çağrıları ve Arama Mantığı ----
async def betco_post(url: str, payload: dict):
    headers = {
        "authentication": BETCO_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://backoffice.betcostatic.com",
        "Referer": "https://backoffice.betcostatic.com/",
        "User-Agent": "Mozilla/5.0 TelegramBot"
    }
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                text = await resp.text()
                status = resp.status
                if status == 401: return {"HasError": True, "AlertMessage": "401 Unauthorized (Token geçersiz)"}
                if status == 403: return {"HasError": True, "AlertMessage": "403 Forbidden"}
                if status >= 500: return {"HasError": True, "AlertMessage": f"Sunucu hatası: {status}"}
                try: return json.loads(text)
                except Exception: return {"HasError": True, "AlertMessage": "JSON parse edilemedi", "_raw": text}
        except Exception as e:
            return {"HasError": True, "AlertMessage": f"Request exception: {e}"}

def extract_users(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        if "Data" in data and isinstance(data["Data"], dict):
            if "Objects" in data["Data"] and isinstance(data["Data"]["Objects"], list):
                return data["Data"]["Objects"]
        for key in ("Items", "Rows", "Clients"):
            if key in data and isinstance(data[key], list): return data[key]
        for key in ("Login", "UserName", "NickName"):
            if key in data: return [data]
    return []

async def betco_find_user(username: str):
    base_payload = {"Login": username, "IsOrderedDesc": True, "MaxRows": 20, "SkeepRows": 0, "IsStartWithSearch": False}
    data1 = await betco_post(BETCO_GET_CLIENTS_URL, base_payload)
    users = extract_users(data1)
    if not users:
        payload2 = dict(base_payload)
        payload2["IsStartWithSearch"] = True
        data2 = await betco_post(BETCO_GET_CLIENTS_URL, payload2)
        users = extract_users(data2)

    uname = username.strip().lower()
    exact = [u for u in users if any(isinstance(u.get(k), str) and u.get(k).strip().lower() == uname for k in ("Login", "UserName", "NickName"))]
    if exact: return {"ok": True, "user": exact[0], "raw": users}
    partial = [u for u in users if any(uname in u.get(k).strip().lower() for k in ("Login", "UserName", "NickName") if isinstance(u.get(k), str))]
    if partial: return {"ok": True, "user": partial[0], "raw": users}

# ================== Telegram Bot Mantığı ==================
async def check_membership(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except BadRequest: return False

async def start_command(update, context):
    user = update.effective_user
    uid = user.id
    username = user.username or ""
    
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            u_list = json.load(f)
    except Exception:
        u_list = []

    user_exists = False
    for u in u_list:
        if isinstance(u, dict) and u.get("id") == uid:
            user_exists = True
            u["status"] = "active"
            u["username"] = username
            break
        elif isinstance(u, (int, str)) and str(u) == str(uid):
            u_list.remove(u)
            break

    if not user_exists:
        new_user = {
            "id": uid,
            "username": username,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active"
        }
        u_list.append(new_user)
        print(f"🆕 Yeni kullanıcı kaydedildi: {uid} (@{username})")

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(u_list, f, ensure_ascii=False, indent=4)

    if await check_membership(uid, context):
        await update.message.reply_text(
            f"🎉 Tebrikler {user.first_name}! Kanalımıza başarıyla katıldınız.\n"
            "Artık bonusunuzu alabilmek için bana Betco kullanıcı adınızı yazınız."
        )
    else:
        await send_invite_message(update)

async def send_invite_message(update: Update):
    user_name = update.effective_user.first_name
    photo_url = "https://r.resimlink.com/wcgRmJG.jpg"
    caption_text = f"Sayın {user_name}, Telegram kanalımızı henüz takibe almadığınız için etkinliğimizden yararlanamamaktasınız.\n\n📢 Kanalımıza katılmak için lütfen aşağıdaki butona tıklayınız"
    keyboard = [
        [InlineKeyboardButton("🎯 Kanala katılmak için hemen tıkla", url="https://t.me/goneresminew")],
        [InlineKeyboardButton("🎯 Kanala katıldım", callback_data="joined")]
    ]
    await update.message.reply_photo(photo=photo_url, caption=caption_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "joined":
        if await check_membership(user_id, context):
            await query.edit_message_caption(
                caption=f"🎉 Tebrikler {query.from_user.first_name}! Kanalımıza başarıyla katıldınız.\nArtık bonusunuzu alabilmek için bana Betco kullanıcı adınızı yazınız."
            )
        else: await query.answer("❌ Hâlâ kanala katılmamışsınız!", show_alert=True)

async def give_bonus(client_id: int, bonus_key: str):
    bonus_map = load_bonus_config()
    bonus_cfg = bonus_map.get(bonus_key)
    if not bonus_cfg: 
        return {"HasError": True, "AlertMessage": f"Bilinmeyen bonus tipi: {bonus_key}"}
    
    payload = {
        "ClientId": client_id, 
        "MessageChannel": None, 
        "Amount": str(bonus_cfg.get("Amount", "0")), 
        "MessageSubject": None, 
        "MessageContent": None, 
        "Count": None, 
        "PartnerBonusId": int(bonus_cfg.get("PartnerBonusId", 0))
    }
    return await betco_post(BETCO_ADD_CLIENT_BONUS_URL, payload)

async def betco_get_user_by_id(client_id: int):
    url = f"https://backofficewebadmin.betcostatic.com/api/tr/Client/GetClientById?id={client_id}"
    headers = {"authentication": BETCO_TOKEN, "Accept": "application/json, text/plain, */*", "User-Agent": "Mozilla/5.0 TelegramBot"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            try: return json.loads(await resp.text())
            except Exception: return {"HasError": True}

async def betco_get_last_login_ip(client_id: int):
    url = "https://backofficewebadmin.betcostatic.com/api/tr/Client/GetLogins"
    payload = {"ClientId": client_id, "StartDate": None, "EndDate": None, "MaxRows": 10, "SkipRows": 0}
    result = await betco_post(url, payload)
    try: return result.get("Data", {}).get("Objects", [])[0]["LoginIP"]
    except Exception: return None

async def check_ip_conflict(ip: str):
    url = "https://backofficewebadmin.betcostatic.com/api/tr/Client/GetClientsByIPAddress"
    payload = {"LoginIP": ip, "SkeepRows": 0, "MaxRows": 10}
    result = await betco_post(url, payload)
    try:
        count = result.get("Data", {}).get("Count", 0)
        return count > 1, result.get("Data", {}).get("Objects", [])
    except Exception: return False, []

async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id
    
    if has_taken_bonus(tg_user_id):
        await update.message.reply_text("⚠️ Bu Telegram hesabı üzerinden daha önce bonus alındı!")
        return
    
    username = (update.message.text or "").strip()
    if not username:
        return

    tg_user_id = update.effective_user.id
    save_user(tg_user_id)
    await update.message.reply_text("🔍 Kullanıcı adı sorgulanıyor, lütfen bekleyin...")

    api_result = None
    try:
        api_result = await betco_find_user(username)
    except Exception:
        api_result = None

    user = (api_result.get("user") if api_result else {}) or {}
    client_id = user.get("Id")
    detail = {}
    if client_id:
        try:
            detail_resp = await betco_get_user_by_id(client_id)
            if detail_resp and not detail_resp.get("HasError"):
                detail = detail_resp.get("Data") or {}
        except Exception:
            detail = {}

    FirstName = (detail.get("FirstName") or user.get("FirstName") or "") or ""
    MiddleName = (detail.get("MiddleName") or user.get("MiddleName") or "") or ""
    LastName = (detail.get("LastName") or user.get("LastName") or "") or ""
    DocNumber = (detail.get("DocNumber") or user.get("DocNumber") or "") or ""
    BirthDate = (detail.get("BirthDate") or user.get("BirthDate") or "") or ""

    conn = None
    rows = []

    try:
        if not DocNumber:
            await update.message.reply_text("❌ Kullanıcının TC bilgisi bulunamadı, doğrulama yapılamıyor.")
            return
        
        birth_year = None
        if not BirthDate:
            await update.message.reply_text("❌ Kullanıcının doğum tarihi bulunamadı, doğrulama yapılamıyor.")
            return
        try:
            birthdate_obj = datetime.fromisoformat(BirthDate.split("T")[0])
            birth_year = birthdate_obj.year
        except Exception:
            await update.message.reply_text("❌ Doğum tarihi formatı okunamadı.")
            return
            
        conn = mariadb.connect(**DB_CONFIG)
        print("✅ Database bağlantısı kuruldu.")
        
        cursor = conn.cursor()
        clauses = []
        params = []

        clauses.append("TC = %s")
        params.append(DocNumber)

        clauses.append("DOGUMTARIHI LIKE %s")
        params.append(f"%{birth_year}")
        
        full_name = FirstName
        if MiddleName:
            full_name += f" {MiddleName}"
        if full_name:
            clauses.append("UPPER(ADI) = %s")
            params.append(full_name.upper())

        if LastName:
            clauses.append("UPPER(SOYADI) = %s")
            params.append(LastName.upper())

        if clauses:
            sql = "SELECT * FROM kullanicilar WHERE " + " AND ".join(clauses)
            print("DEBUG SQL:", sql, "PARAMS:", params)
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            
        cursor.close()
    
    except mariadb.Error as e:
        await update.message.reply_text(f"❌ Veritabanı sorgusunda hata: {e}")
        return
    except Exception as e:
        await update.message.reply_text(f"❌ Beklenmedik bir hata oluştu: {e}")
        return
    finally:
        if conn and conn.open:
            conn.close()
            print("Database bağlantısı kapatıldı.")

    if not rows:
        await update.message.reply_text("❌ TC veya diğer bilgiler doğrulanmadı. \n \nEğer yanlış kullanıcı adı yazdıysanız tekrar deneyin. \n \n Eğer bilgileriniz size ait ise lütfen destek ile iletişime geçin.")
        return
    
    if rows:
        await update.message.reply_text("✅ TC doğrulandı, diğer filtrelere geçiliyor...")

        if not (api_result and api_result.get("ok")):
            try:
                api_result = await betco_find_user(username)
            except Exception as e:
                await update.message.reply_text(f"❌ Betco sorgusunda hata oluştu: {e}")
                return

        if not api_result or not api_result.get("ok"):
            await update.message.reply_text(
                "⚠️ Veritabanında eşleşme bulundu fakat Betco sisteminde kullanıcı bulunamadı. "
                "Lütfen destek ile iletişime geçin."
            )
            return

        user = api_result.get("user", {}) or {}
        client_id = user.get("Id")
        if not client_id:
            await update.message.reply_text("⚠️ Kullanıcı ID bulunamadı, işlem yapılamıyor.")
            return

        detail = {}
        try:
            detail_resp = await betco_get_user_by_id(client_id)
            if not detail_resp or detail_resp.get("HasError"):
                await update.message.reply_text("❌ Kullanıcı detayları alınamadı.")
                return
            detail = detail_resp.get("Data", {}) or {}
        except Exception:
            await update.message.reply_text("❌ Kullanıcı detayları alınamadı.")
            return
            
        created_date_str = detail.get("CreatedLocalDate") or user.get("CreatedLocalDate")
        if created_date_str:
            try:
                created_date = datetime.fromisoformat(created_date_str.split("T")[0])
                today = datetime.now().date()
                cutoff = datetime.combine(today - timedelta(days=7), datetime.min.time())
                cutoff_date_str_fmt = cutoff.strftime("%d.%m.%Y")

                if created_date < cutoff:
                    await update.message.reply_text(
                        f"❌ {cutoff_date_str_fmt} tarihinden önce kayıt olduğunuz için bonus hakkınız bulunmamaktadır."
                    )
                    return
            except Exception as e:
                print(f"CreatedLocalDate parse hatası: {e}, value={created_date_str}")
                
        last_casino_bet = detail.get("LastCasinoBetLocalDate") or detail.get("LastCasinoBetTime")
        if last_casino_bet:
            await update.message.reply_text(
                "⚠️ Daha önceden casino oynamış olduğunuz için bonus hakkınız bulunmamaktadır."
            )
            return
            
        first_deposit = detail.get("FirstDepositLocalDate") or detail.get("FirstDepositTime")
        if first_deposit:
            await update.message.reply_text(
                "⚠️ Daha önceden yatırım yaptığınız için bonus hakkınız bulunmamaktadır."
            )
            return

        try:
            bonuses_payload = {
                "StartDateLocal": None, "EndDateLocal": None, "BonusType": None,
                "AcceptanceType": None, "ClientBonusId": "", "PartnerBonusId": "", 
                "PartnerExternalBonusId": "", "ClientId": client_id
            }
            bonuses_resp = await betco_post(
                "https://backofficewebadmin.betcostatic.com/api/tr/Client/GetClientBonuses",
                bonuses_payload
            )
        except Exception:
            await update.message.reply_text("❌ Bonus geçmişi sorgulanırken hata oluştu.")
            return

        if not bonuses_resp or bonuses_resp.get("HasError"):
            await update.message.reply_text("❌ Bonus geçmişi alınamadı, işlem iptal edildi.")
            return

        bonuses_data = bonuses_resp.get("Data", [])

        def has_active_noncancelled_bonus(bonus_items):
            items = []
            if isinstance(bonus_items, dict):
                items = bonus_items.get("Objects", []) or []
            elif isinstance(bonus_items, list):
                items = bonus_items
            for b in items:
                if b and b.get("CancellationNote") is None and b.get("Status") not in ("Cancelled", "Deleted", "Expired"):
                    return True
            return False

        if has_active_noncancelled_bonus(bonuses_data):
            await update.message.reply_text("⚠️ Üzgünüz, daha önce bonus alma hakkınızı kullanmış bulunmaktasınız.")
            return

        if user.get("HasReceivedBonus"):
            await update.message.reply_text("⚠️ Daha önce bonus almışsınız. Tekrar bonus alamazsınız.")
            return
        
        created_date_str = detail.get("CreatedLocalDate") or user.get("CreatedLocalDate")
        if created_date_str:
            try:
                created_date = datetime.fromisoformat(created_date_str.split("T")[0])
                cutoff = datetime(2025, 9, 15)

                if created_date < cutoff:
                    await update.message.reply_text(
                        f"❌ 15.09.2025 tarihinden önce kayıt olduğunuz için bonus hakkınız bulunmamaktadır."
                    )
                    return
            except Exception as e:
                print(f"CreatedLocalDate parse hatası: {e}, value={created_date_str}")

    if client_id:
        last_ip = await betco_get_last_login_ip(client_id)
        if last_ip:
            ip_conflict, users_with_same_ip = await check_ip_conflict(last_ip)
            if ip_conflict:
                await update.message.reply_text(
                    f"❌ IP çakışması tespit edildi! Bu IP {len(users_with_same_ip)} kullanıcı tarafından kullanılıyor.\n"
                    "⚠️ Bu nedenle bonus alamazsınız."
                )
                return
                
        # Panellerden dinamik olarak tanımlanan tüm bonus butonlarını oluştur
        bonus_map = load_bonus_config()
        keyboard = []
        for b_key, b_val in bonus_map.items():
            btn_label = b_val.get("label", b_key.upper())
            keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"bonus_{b_key}_{client_id}")])

        if not keyboard:
            await update.message.reply_text("⚠️ Şu an tanımlı aktif bonus seçeneği bulunmamaktadır.")
            return

        await update.message.reply_text(
            "🎉 Bonusunuzu seçiniz:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if api_result and api_result.get("ok") and api_result.get("user"):
        await update.message.reply_text(
            "❌ TC’niz doğrulanamadı!\n \nEğer yanlış kullanıcı adı yazdıysanız lütfen tekrar deneyin.\n\nEğer bilgileriniz size ait ise lütfen destek ile iletişime geçin."
        )
        return

    await update.message.reply_text("❌ Kullanıcı bulunamadı veya yanıt boş.")


async def bonus_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id 

    if has_taken_bonus(user_id):
        await query.answer("⚠️ Bu Telegram hesabı üzerinden daha önce bonus alındı!", show_alert=True)
        return

    if query.data.startswith("bonus_"):
        parts = query.data.split("_")
        client_id_str = parts[-1]
        bonus_key = "_".join(parts[1:-1])

        resp = await give_bonus(int(client_id_str), bonus_key)
        if resp.get("HasError"):
            await query.edit_message_text(f"❌ Bonus yüklenemedi: {resp.get('AlertMessage')}")
        else:
            bonus_cfg = load_bonus_config().get(bonus_key, {})
            bonus_title = bonus_cfg.get("label", bonus_key.upper())
            await query.edit_message_text(f"✅ {bonus_title} hesabınıza başarıyla yüklendi!")
            mark_bonus_given(user_id)

# ================== 🔐 Sadece Adminlerin Görebileceği Panel Komutu ==================
async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bu paneli açmaya yetkiniz bulunmamaktadır!")
        return

    clean_url = WEB_APP_URL.strip()
    keyboard = [
        [InlineKeyboardButton("📱 Toplu Mesaj Panelini Aç", web_app=WebAppInfo(url=clean_url))]
    ]
    await update.message.reply_text(
        "🛠 **GoneResmi Yönetim Arayüzü**\n\nAşağıdaki butona tıklayarak toplu duyuru panelini doğrudan bot ekranından yönetebilirsiniz.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== 🌐 FLASK WEB ARAYÜZÜ (MINI APP ARKA PLANI) 🌐 ==================
flask_app = Flask(__name__)
flask_app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

PANEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gelişmiş Duyuru & Yönetim Paneli</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #121212;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
        }
        .container {
            width: 100%;
            max-width: 650px;
            background: #1e1e1e;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        h2 { text-align: center; color: #ffffff; margin-bottom: 20px; font-weight: 600; }
        h3 { color: #00adb5; font-size: 16px; margin-top: 0; margin-bottom: 12px; border-bottom: 1px solid #333; padding-bottom: 6px; }
        
        .stats-box {
            display: flex;
            justify-content: space-between;
            background: #252525;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 13px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .stats-box span { color: #00adb5; font-weight: bold; }
        .alert {
            padding: 12px;
            background-color: #2d4059;
            color: #00adb5;
            border-left: 4px solid #00adb5;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        label { display: block; margin-bottom: 6px; font-weight: 500; font-size: 13px; color: #aaaaaa; }
        
        .drop-zone {
            width: 100%;
            height: 140px;
            border: 2px dashed #444444;
            border-radius: 8px;
            background: #252525;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: border-color 0.3s, background-color 0.3s;
            margin-bottom: 15px;
            color: #888888;
            text-align: center;
            padding: 10px;
            box-sizing: border-box;
        }
        .drop-zone.drag-over { border-color: #00adb5; background: #2a3a3a; color: #ffffff; }
        .drop-zone img { max-height: 120px; max-width: 100%; border-radius: 6px; display: none; }
        
        textarea {
            width: 100%;
            height: 130px;
            background: #252525;
            border: 1px solid #333333;
            border-radius: 8px;
            color: #ffffff;
            padding: 12px;
            box-sizing: border-box;
            resize: vertical;
            font-size: 14px;
            margin-bottom: 5px;
        }
        textarea:focus { border-color: #00adb5; outline: none; }
        
        .editor-tools {
            display: flex;
            gap: 6px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        .tool-btn {
            background-color: #2d2d2d;
            border: 1px solid #444444;
            color: #eeeeee;
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s, color 0.2s;
        }
        .tool-btn:hover {
            background-color: #00adb5;
            color: #ffffff;
            border-color: #00adb5;
        }
        
        .btn-group { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
        button, .btn {
            padding: 10px 14px;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 14px;
            text-align: center;
        }
        .btn-primary { background: #00adb5; color: white; width: 100%; font-size: 15px; margin-top: 5px; }
        .btn-primary:hover { background: #008c9e; }
        .btn-warning { background: #ff9800; color: white; width: 100%; font-size: 14px; margin-top: 8px; }
        .btn-warning:hover { background: #e68a00; }
        .btn-secondary { background: #393e46; color: #eeeeee; }
        .btn-secondary:hover { background: #4b525d; }
        .btn-danger { background: #ff4141; color: white; }
        .btn-danger:hover { background: #dd3333; }
        .btn-sm { padding: 4px 8px; font-size: 12px; }
        
        .panel-section {
            background: #252525;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #333;
        }
        select, input[type="text"], input[type="number"], input[type="datetime-local"] {
            width: 100%;
            padding: 10px;
            background: #1e1e1e;
            border: 1px solid #444;
            color: white;
            border-radius: 6px;
            box-sizing: border-box;
            margin-bottom: 10px;
            font-size: 14px;
        }
        select:focus, input:focus { border-color: #00adb5; outline: none; }
        
        .bonus-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        @media (max-width: 500px) {
            .bonus-grid { grid-template-columns: 1fr; }
        }
        .bonus-card {
            background: #1e1e1e;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #3d3d3d;
        }
        
        .table-container {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 10px;
        }
        th, td {
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #333;
        }
        th { background-color: #1e1e1e; color: #00adb5; }
        .badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }
        .badge-pending { background: #ff9800; color: #121212; }
        .badge-completed { background: #4caf50; color: white; }
    </style>
</head>
<body>

<div class="container">
    <h2>📢 GoneResmi Yönetim Paneli</h2>
    
    <div class="stats-box">
        <div>Toplam: <span>{{ stats.total }}</span></div>
        <div>Aktif: <span>{{ stats.active }}</span></div>
        <div>Engellemiş: <span style="color: #ff4141;">{{ stats.blocked }}</span></div>
        <div>Son 24s: <span>{{ stats.last_24h }}</span></div>
        <div>Son 1 Hafta: <span style="color: #00adb5;">{{ stats.last_7d }}</span></div>
    </div>

    {% if status %}
    <div class="alert">{{ status }}</div>
    {% endif %}

    <!-- 🎁 DİNAMİK BONUS BUTONLARI YÖNETİMİ -->
    <div class="panel-section">
        <h3>🎁 Bonus Butonları Yönetimi</h3>
        <p style="font-size: 12px; color: #aaa; margin-bottom: 15px;">Telegram botunda kullanıcılara gösterilecek bonus butonlarını düzenleyebilir, silebilir veya yenilerini ekleyebilirsiniz.</p>
        
        <!-- Mevcut Butonları Güncelleme Formu -->
        <form method="POST">
            <input type="hidden" name="action" value="save_bonuses">
            <div style="display: flex; flex-direction: column; gap: 15px;">
                {% for b_key, b_val in bonus_config.items() %}
                <div class="bonus-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                        <span style="color:#00adb5; font-weight:bold; font-size: 14px;">🔑 Anahtar Kimlik: {{ b_key }}</span>
                        <input type="hidden" name="b_key" value="{{ b_key }}">
                    </div>
                    <div class="bonus-grid">
                        <div>
                            <label>Buton Metni (Telegram'da Görünür):</label>
                            <input type="text" name="b_label" value="{{ b_val.label }}" required>
                        </div>
                        <div>
                            <label>Partner Bonus ID:</label>
                            <input type="number" name="b_id" value="{{ b_val.PartnerBonusId }}" required>
                        </div>
                        <div style="grid-column: span 2;">
                            <label>Miktar (Amount):</label>
                            <input type="text" name="b_amount" value="{{ b_val.Amount }}" required>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% if bonus_config %}
            <button type="submit" class="btn btn-secondary" style="width:100%; margin-top:12px;">💾 Tüm Buton Değişikliklerini Kaydet</button>
            {% else %}
            <p style="font-size:13px; color:#888;">Henüz kayıtlı bonus butonu yok. Aşağıdan yeni buton ekleyebilirsiniz.</p>
            {% endif %}
        </form>

        <hr style="border: 0; border-top: 1px solid #333; margin: 20px 0;">

        <!-- Yeni Buton Ekleme ve Silme Bölümü -->
        <div style="display: grid; grid-template-columns: 1fr; gap: 15px;">
            <!-- Yeni Buton Ekle -->
            <form method="POST" style="background: #1e1e1e; padding: 12px; border-radius: 6px; border: 1px dashed #00adb5;">
                <input type="hidden" name="action" value="add_bonus">
                <label style="color:#00adb5; font-weight:bold; margin-bottom:10px;">➕ Yeni Bonus Butonu Ekle</label>
                <div class="bonus-grid">
                    <div>
                        <label>Buton Kimliği (Tek kelime, örn: bonus_3):</label>
                        <input type="text" name="new_key" placeholder="Örn: deneme_bonusu" required>
                    </div>
                    <div>
                        <label>Buton Metni:</label>
                        <input type="text" name="new_label" placeholder="Örn: 🎁 100 TL Deneme Bonusu" required>
                    </div>
                    <div>
                        <label>Partner Bonus ID:</label>
                        <input type="number" name="new_id" placeholder="Örn: 604384" required>
                    </div>
                    <div>
                        <label>Miktar (Amount):</label>
                        <input type="text" name="new_amount" placeholder="Örn: 100" required>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary" style="margin-top:10px;">➕ Butonu Ekle</button>
            </form>

            <!-- Buton Silme -->
            {% if bonus_config %}
            <form method="POST" style="background: #1e1e1e; padding: 12px; border-radius: 6px; border: 1px solid #3d3d3d;">
                <input type="hidden" name="action" value="delete_bonus">
                <label style="color:#ff4141; font-weight:bold; margin-bottom:10px;">🗑️ Var Olan Bir Butonu Sil</label>
                <select name="delete_key" required style="margin-bottom:10px;">
                    <option value="">-- Silinecek Butonu Seçin --</option>
                    {% for b_key, b_val in bonus_config.items() %}
                    <option value="{{ b_key }}">{{ b_val.label }} (ID: {{ b_key }})</option>
                    {% endfor %}
                </select>
                <button type="submit" class="btn btn-danger" style="width:100%;" onclick="return confirm('Bu bonus butonunu silmek istediğinizden emin misiniz?')">🗑️ Seçilen Butonu Sil</button>
            </form>
            {% endif %}
        </div>
    </div>

    <!-- 📂 TASLAK YÖNETİMİ -->
    <div class="panel-section">
        <h3>📁 Taslak Yönetimi</h3>
        <form method="POST" id="main_form">
            <input type="hidden" name="photo_url" id="photo_url" value="{{ draft_photo }}">
            
            <label>Kayıtlı Taslaklar:</label>
            <select name="selected_draft" id="selected_draft">
                <option value="">-- Bir Taslak Seçin --</option>
                {% for title in all_drafts %}
                <option value="{{ title }}">{{ title }}</option>
                {% endfor %}
            </select>
            <div class="btn-group">
                <button type="submit" name="action" value="load" class="btn btn-secondary">📂 Seçilen Taslağı Yükle</button>
                <button type="submit" name="action" value="delete" class="btn btn-danger">🗑️ Seçileni Sil</button>
            </div>

            <hr style="border: 0; border-top: 1px solid #333; margin: 15px 0;">

            <label>Yeni Taslak Başlığı:</label>
            <input type="text" name="draft_title" id="draft_title" placeholder="Örn: Hafta Sonu Kampanyası">
            <button type="submit" name="action" value="save" class="btn btn-secondary" style="width:100%;">💾 Mevcut Paneli Bu Başlıkla Kaydet</button>
    </div>

    <!-- 📢 DUYURU VE ZAMANLANMIŞ DUYURU GÖNDERİMİ -->
    <div class="panel-section">
        <h3>📢 Duyuru Hazırlama ve Gönderim</h3>
            <label>Duyuru Görseli (Sürükle-Bırak veya Ctrl+V ile Yapıştır):</label>
            <div class="drop-zone" id="drop_zone">
                <div id="drop_text">Resmi buraya sürükleyin, tıklayıp seçin veya kopyalayıp yapıştırın.</div>
                <img id="preview_img" src="{{ draft_photo }}" {% if draft_photo %} style="display:block;" {% endif %}>
            </div>
            {% if draft_photo %}
            <button type="button" class="btn btn-danger" id="clear_img_btn" style="width:100%; padding:6px; margin-bottom:15px; font-size:12px;">🖼️ Görseli Kaldır</button>
            {% endif %}

            <label>Duyuru Metni:</label>
            
            <div class="editor-tools">
                <button type="button" class="tool-btn" onclick="wrapText('b')">Kalın</button>
                <button type="button" class="tool-btn" onclick="wrapText('i')">İtalik</button>
                <button type="button" class="tool-btn" onclick="addLink()">Link</button>
                <button type="button" class="tool-btn" onclick="wrapText('code')">Kod</button>
                <button type="button" class="tool-btn" onclick="insertBr()">↩️ Yeni Satır</button>
            </div>
            
            <textarea name="message" id="msg_text" placeholder="Mesajınızı yazın... HTML etiketleri desteklenir.">{{ draft_text }}</textarea>
            
            <button type="submit" name="action" value="send" class="btn btn-primary" onclick="return confirm('Tüm kullanıcılara duyuru HEMENT gönderilecektir. Onaylıyor musunuz?')">🚀 Toplu Duyuruyu Anında Başlat</button>
            
            <hr style="border: 0; border-top: 1px solid #333; margin: 20px 0;">

            <!-- ⏰ ZAMANLANMIŞ DUYURU EKLEME -->
            <label style="color:#ff9800; font-weight:bold;">⏰ VEYA Duyuruyu İleri Bir Tarihe Zamanla:</label>
            <input type="datetime-local" name="scheduled_time" id="scheduled_time">
            <button type="submit" name="action" value="schedule_send" class="btn btn-warning" onclick="return confirm('Bu duyuru belirttiğiniz tarih ve saatte otomatik gönderilmek üzere planlanacaktır. Onaylıyor musunuz?')">⏰ Duyuruyu Zamanla</button>
        </form>
    </div>

    <!-- ⏰ BEKLEYEN PLANLANMIŞ DUYURULAR -->
    <div class="panel-section">
        <h3>⏰ Bekleyen Planlanmış Duyurular</h3>
        {% set pending_list = [] %}
        {% for item in scheduled_list %}
            {% if item.status == 'pending' %}
                {% set _ = pending_list.append(item) %}
            {% endif %}
        {% endfor %}

        {% if pending_list %}
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Hedef Tarih / Saat</th>
                        <th>Mesaj Özeti</th>
                        <th>Durum</th>
                        <th>İşlem</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in pending_list %}
                    <tr>
                        <td>{{ item.send_time.replace('T', ' ') }}</td>
                        <td>{{ item.message[:35] }}{% if item.message|length > 35 %}...{% endif %}</td>
                        <td><span class="badge badge-pending">Bekliyor</span></td>
                        <td>
                            <form method="POST" style="display:inline;">
                                <input type="hidden" name="action" value="delete_scheduled">
                                <input type="hidden" name="sched_id" value="{{ item.id }}">
                                <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Bu zamanlanmış duyuruyu iptal etmek istediğinize emin misiniz?')">İptal Et</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <p style="font-size:13px; color:#888;">Henüz bekleyen planlanmış duyuru bulunmamaktadır.</p>
        {% endif %}
    </div>

    <!-- ✅ GÖNDERİLMİŞ DUYURULAR GEÇMİŞİ -->
    <div class="panel-section">
        <h3>✅ Gönderilmiş Duyurular Geçmişi</h3>
        {% set completed_list = [] %}
        {% for item in scheduled_list %}
            {% if item.status == 'completed' %}
                {% set _ = completed_list.append(item) %}
            {% endif %}
        {% endfor %}

        {% if completed_list %}
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Gönderildiği Tarih / Saat</th>
                        <th>Mesaj Özeti</th>
                        <th>Durum</th>
                        <th>İşlem</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in completed_list|reverse %}
                    <tr>
                        <td>{{ item.executed_at if item.executed_at else item.send_time.replace('T', ' ') }}</td>
                        <td>{{ item.message[:40] }}{% if item.message|length > 40 %}...{% endif %}</td>
                        <td><span class="badge badge-completed">Gönderildi</span></td>
                        <td>
                            <form method="POST" style="display:inline;">
                                <input type="hidden" name="action" value="delete_scheduled">
                                <input type="hidden" name="sched_id" value="{{ item.id }}">
                                <button type="submit" class="btn btn-secondary btn-sm" onclick="return confirm('Bu geçmiş kaydını listeden temizlemek istiyor musunuz?')">Temizle</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <p style="font-size:13px; color:#888;">Henüz tamamlanmış zamanlanmış duyuru geçmişi yok.</p>
        {% endif %}
    </div>
</div>

<script>
    function wrapText(tag) {
        var txtArea = document.getElementById("msg_text");
        var start = txtArea.selectionStart;
        var end = txtArea.selectionEnd;
        var text = txtArea.value;
        var selected = text.substring(start, end);
        
        var replacement = "<" + tag + ">" + selected + "</" + tag + ">";
        txtArea.value = text.substring(0, start) + replacement + text.substring(end);
        
        txtArea.focus();
        txtArea.selectionStart = start;
        txtArea.selectionEnd = start + replacement.length;
    }

    function addLink() {
        var url = prompt("Link Adresini Girin:", "https://");
        if(url) {
            var txtArea = document.getElementById("msg_text");
            var start = txtArea.selectionStart;
            var end = txtArea.selectionEnd;
            var text = txtArea.value;
            var selected = text.substring(start, end) || "Link Metni";
            
            var replacement = '<a href="' + url + '">' + selected + '</a>';
            txtArea.value = text.substring(0, start) + replacement + text.substring(end);
            
            txtArea.focus();
        }
    }

    function insertBr() {
        var txtArea = document.getElementById("msg_text");
        var start = txtArea.selectionStart;
        var end = txtArea.selectionEnd;
        var text = txtArea.value;
        txtArea.value = text.substring(0, start) + "\\n" + text.substring(end);
        txtArea.selectionStart = txtArea.selectionEnd = start + 1;
        txtArea.focus();
    }

    const dropZone = document.getElementById('drop_zone');
    const previewImg = document.getElementById('preview_img');
    const dropText = document.getElementById('drop_text');
    const photoUrlInput = document.getElementById('photo_url');
    const clearImgBtn = document.getElementById('clear_img_btn');

    if (clearImgBtn) {
        clearImgBtn.addEventListener('click', () => {
            photoUrlInput.value = '';
            previewImg.src = '';
            previewImg.style.display = 'none';
            dropText.style.display = 'block';
        });
    }

    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('drag-over'); });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if(files.length > 0) { handleImage(files[0]); }
    });

    dropZone.addEventListener('click', () => {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.onchange = (e) => { if(e.target.files.length > 0) handleImage(e.target.files[0]); };
        fileInput.click();
    });

    window.addEventListener('paste', (e) => {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                const blob = items[i].getAsFile();
                handleImage(blob);
            }
        }
    });

    function handleImage(file) {
        if (!file.type.match('image.*')) { alert('Lütfen sadece resim dosyası yükleyin!'); return; }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = function() {
                const max_width = 1024;
                let width = img.width;
                let height = img.height;

                if (width > max_width) {
                    height = Math.round((height * max_width) / width);
                    width = max_width;
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                const dataUrl = canvas.toDataURL('image/jpeg', 0.6); 
                
                previewImg.src = dataUrl;
                previewImg.style.display = 'block';
                dropText.style.display = 'none';
                photoUrlInput.value = dataUrl;
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
</script>
</body>
</html>
"""

# ================== 🌐 FLASK WEB ARAYÜZÜ FONKSİYONU ==================
@flask_app.route("/", methods=["GET", "POST"])
def index():
    status = None
    draft_text = "<b>Merhaba!</b> Duyuru metni..."
    draft_photo = ""

    all_drafts = {}
    if os.path.exists(DRAFT_FILE):
        try:
            with open(DRAFT_FILE, "r", encoding="utf-8") as f:
                all_drafts = json.load(f)
        except Exception:
            all_drafts = {}

    bonus_config = load_bonus_config()

    if request.method == "POST":
        action = request.form.get("action")
        msg_content = request.form.get("message", "")
        photo_url = request.form.get("photo_url", "")
        draft_title = request.form.get("draft_title", "").strip()
        selected_draft = request.form.get("selected_draft", "")

        # 🎁 TÜM BONUS BUTONLARINI GÜNCELLE
        if action == "save_bonuses":
            b_keys = request.form.getlist("b_key")
            b_labels = request.form.getlist("b_label")
            b_ids = request.form.getlist("b_id")
            b_amounts = request.form.getlist("b_amount")

            new_cfg = {}
            for i in range(len(b_keys)):
                k = b_keys[i].strip()
                if k:
                    try:
                        p_id = int(b_ids[i].strip())
                    except ValueError:
                        p_id = 0
                    new_cfg[k] = {
                        "label": b_labels[i].strip(),
                        "PartnerBonusId": p_id,
                        "Amount": b_amounts[i].strip()
                    }
            bonus_config = new_cfg
            save_bonus_config(bonus_config)
            status = "✅ Tüm bonus butonları başarıyla güncellendi!"

        # ➕ YENİ BONUS BUTONU EKLE
        elif action == "add_bonus":
            new_key = request.form.get("new_key", "").strip().lower().replace(" ", "_")
            new_label = request.form.get("new_label", "").strip()
            new_id_str = request.form.get("new_id", "").strip()
            new_amount = request.form.get("new_amount", "").strip()

            if not new_key or not new_label:
                status = "❌ Hata: Buton kimliği ve buton metni boş olamaz!"
            else:
                try:
                    new_id = int(new_id_str)
                except ValueError:
                    new_id = 0
                
                bonus_config[new_key] = {
                    "label": new_label,
                    "PartnerBonusId": new_id,
                    "Amount": new_amount
                }
                save_bonus_config(bonus_config)
                status = f"✅ '{new_label}' butonu başarıyla eklendi!"

        # 🗑️ BONUS BUTONU SİL
        elif action == "delete_bonus":
            delete_key = request.form.get("delete_key", "").strip()
            if delete_key in bonus_config:
                del bonus_config[delete_key]
                save_bonus_config(bonus_config)
                status = f"🗑️ '{delete_key}' bonus butonu sistemden silindi."
            else:
                status = "❌ Hata: Silinecek buton bulunamadı!"

        # 💾 Başlıkla Taslak Kaydetme Butonu
        elif action == "save":
            if not draft_title:
                status = "❌ Hata: Taslağı kaydetmek için lütfen bir başlık yaz kanka!"
                draft_text = msg_content
                draft_photo = photo_url
            else:
                all_drafts[draft_title] = {"text": msg_content, "photo": photo_url}
                with open(DRAFT_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_drafts, f, ensure_ascii=False, indent=4)
                draft_text = msg_content
                draft_photo = photo_url
                status = f"✅ '{draft_title}' başlıklı taslak başarıyla kaydedildi."

        # 📂 Listeden Seçilen Taslağı Yükleme Butonu
        elif action == "load":
            if selected_draft in all_drafts:
                draft_text = all_drafts[selected_draft].get("text", "")
                draft_photo = all_drafts[selected_draft].get("photo", "")
                status = f"📂 '{selected_draft}' başlıklı taslak başarıyla panele yüklendi."
            else:
                status = "❌ Hata: Lütfen yüklemek için listeden bir taslak seçin."

        # 🗑️ Seçilen Taslağı Silme Butonu
        elif action == "delete":
            if selected_draft in all_drafts:
                del all_drafts[selected_draft]
                with open(DRAFT_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_drafts, f, ensure_ascii=False, indent=4)
                status = f"🗑️ '{selected_draft}' başlıklı taslak sistemden silindi."
            else:
                status = "❌ Hata: Silmek için geçerli bir taslak seçmelisin."

        # ⏰ ZAMANLANMIŞ DUYURU EKLEME (SCHEDULE_SEND)
        elif action == "schedule_send":
            msg_content = msg_content.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
            scheduled_time = request.form.get("scheduled_time", "").strip()

            if not scheduled_time:
                status = "❌ Hata: Lütfen duyurunun gönderileceği tarih ve saati seçin."
                draft_text = msg_content
                draft_photo = photo_url
            elif not msg_content and not photo_url:
                status = "❌ Hata: Gönderilecek duyuru metni veya görsel boş olamaz!"
            else:
                scheduled_items = load_scheduled_broadcasts()
                new_item = {
                    "id": f"sched_{int(datetime.now().timestamp())}",
                    "send_time": scheduled_time,
                    "message": msg_content,
                    "photo": photo_url,
                    "status": "pending",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                scheduled_items.append(new_item)
                save_scheduled_broadcasts(scheduled_items)
                
                status = f"⏰ Duyuru {scheduled_time.replace('T', ' ')} tarihine başarıyla zamanlandı!"
                draft_text = msg_content
                draft_photo = photo_url

        # 🗑️ ZAMANLANMIŞ DUYURU İPTAL ETME / SİLME
        elif action == "delete_scheduled":
            sched_id = request.form.get("sched_id")
            scheduled_items = load_scheduled_broadcasts()
            scheduled_items = [item for item in scheduled_items if item.get("id") != sched_id]
            save_scheduled_broadcasts(scheduled_items)
            status = "🗑️ Zamanlanmış duyuru kaydı silindi."

        # 🚀 TOPLU DUYURUYU BAŞLAT (SEND) BLOĞU
        elif action == "send":
            msg_content = msg_content.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
            draft_text = msg_content
            draft_photo = photo_url
            
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    all_users = json.load(f)
                
                u_list = [u for u in all_users if isinstance(u, dict) and u.get("status") != "blocked"]
                for u in all_users:
                    if not isinstance(u, dict):
                        u_list.append(u)
                        
            except Exception: 
                u_list = []

            if not u_list:
                status = "❌ Gönderilecek aktif kullanıcı bulunamadı (users.json boş veya herkes engelli)."
            else:
                if telegram_app is not None and telegram_loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        send_bulk_message(u_list, msg_content, photo_url), 
                        telegram_loop
                    )
                    status = f"🚀 Toplu mesaj gönderimi {len(u_list)} AKTİF abone için arka planda başarıyla başlatıldı!"
                else:
                    status = "❌ Bot motoru veya loop senkronizasyonu henüz hazır değil."

    return render_template_string(
        PANEL_TEMPLATE, 
        stats=get_user_counts(), 
        status=status, 
        draft_text=draft_text, 
        draft_photo=draft_photo,
        all_drafts=list(all_drafts.keys()),
        bonus_config=bonus_config,
        scheduled_list=load_scheduled_broadcasts()
    )

async def send_bulk_message(user_ids, text, photo_url=None):
    print(f"[PANEL DUYURU] Gönderim işlemi arka planda başlatılıyor...")
    
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            current_users = json.load(f)
    except Exception:
        print("❌ Kullanıcı listesi okunamadı.")
        return

    photo_file = None
    if photo_url and photo_url.startswith("data:image"):
        try:
            format_str, imgstr = photo_url.split(';base64,') 
            ext = format_str.split('/')[-1]
            photo_file = BytesIO(base64.b64decode(imgstr))
            photo_file.name = f"broadcast_img.{ext}"
        except Exception as e:
            print(f"❌ Resim çözme hatası: {e}")

    blocked_detected = []

    for u in current_users:
        if isinstance(u, dict):
            if u.get("status") == "blocked":
                continue
            uid = u.get("id")
        else:
            uid = u

        try:
            if photo_file:
                photo_file.seek(0)
                await telegram_app.bot.send_photo(chat_id=uid, photo=photo_file, caption=text, parse_mode="HTML")
            elif photo_url and photo_url.strip() and photo_url.startswith("http"):
                await telegram_app.bot.send_photo(chat_id=uid, photo=photo_url, caption=text, parse_mode="HTML")
            else:
                await telegram_app.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            
            await asyncio.sleep(0.05)

        except Exception as e:
            error_msg = str(e).lower()
            if "blocked" in error_msg or "chat not found" in error_msg or "user is deactivated" in error_msg:
                print(f"🚫 Kullanıcının engellediği tespit edildi, listeye işaretleniyor: {uid}")
                blocked_detected.append(uid)
            else:
                print(f"⚠️ Mesaj iletilemedi ({uid}), geçici hata: {e}")

    if blocked_detected:
        for u in current_users:
            if isinstance(u, dict) and u.get("id") in blocked_detected:
                u["status"] = "blocked"
        
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_users, f, ensure_ascii=False, indent=4)
        print(f"💾 Toplam {len(blocked_detected)} engelli kullanıcı veritabanında güncellendi.")

    print("[PANEL DUYURU] Gönderim tamamlandı.")

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

async def post_init(application):
    global telegram_loop
    telegram_loop = asyncio.get_running_loop()
    asyncio.create_task(scheduled_broadcast_task(application))
    print("⏰ Zamanlanmış Duyuru motoru arka planda başlatıldı.")

# ================== Runner / Başlatıcı ==================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    telegram_app = app 

    try:
        app.job_queue.run_repeating(token_reminder_task, interval=3600, first=0, name="token_reminder_task")
    except AttributeError:
        print("⚠️ JobQueue aktif değil.")

    app.add_handler(CallbackQueryHandler(bonus_button_handler, pattern="^bonus_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("settoken", set_token)) 
    app.add_handler(CommandHandler("panel", admin_panel_command)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username))
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("Bot ve Mini App altyapısı aktif!")
    app.run_polling(drop_pending_updates=True)