import base64
from io import BytesIO
import os
import json
import asyncio
import threading
import aiohttp
from datetime import datetime, timedelta
from datetime import datetime
import mariadb
import mysql.connector  # Artık kullanılmasa da korunuyor
from unittest import result
# Flask (Telegram Mini App İçeriğini Barındırmak İçin)
from flask import Flask, render_template_string, request, jsonify

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest

# ================== Telegram ==================
TOKEN = "8461667958:AAGO0ra90HDractX-MWMA30IsQAgLKgKmAk" 
CHANNEL_USERNAME = "@diorresminew"

# 🌐 TELEGRAM MINI APP PANEL LİNKİNİZ
# (Telegram içi açılacağı için buranın MUTLAKA 'https://' olması gerekir. Lokal testlerde ngrok kullanabilirsiniz)
WEB_APP_URL = "https://bdd6-94-55-17-89.ngrok-free.app"

# ================== Betco API ==================
BETCO_TOKEN = "caa44f6274c3479fc69f8f1219227053c0e19492ff63f6f3a0194eb51661f234"
BETCO_GET_CLIENTS_URL = "https://backofficewebadmin.betcostatic.com/api/tr/Client/GetClients"
BETCO_ADD_CLIENT_BONUS_URL = "https://backofficewebadmin.betcostatic.com/api/tr/Client/AddClientToBonus"

BONUS_MAP = {
    "freespin": {"PartnerBonusId": 604382, "Amount": "500"},
    "freebet": {"PartnerBonusId": 604383, "Amount": "50"}
}

# ================== Token Yönetimi ve DB Config ==================
ADMIN_IDS = [5695472914, 5947341902, 805254965, 1782604827, 8423465949]
SPECIAL_GROUP_ID = -4876211377 

last_token_change = None

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "101m"
}

BONUS_USERS_FILE = "bonus_users.json"
USERS_FILE = "users.json"
DRAFT_FILE = "drafts.json"  # Eski tekil taslak yerine artık çoklu taslak tutacak
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print("🚀 Sistem ve Telegram Mini App paneli başlatılıyor...")

# ---- Global Bot Referansı ----
telegram_app = None
# Global event loop referansı
telegram_loop = None
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
            # Eski yapıdaki düz ID'leri de sayalım (çökme olmasın)
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
    last_token_change = datetime.utcnow()
    await update.message.reply_text("✅ Betco token başarıyla güncellendi!")

# ================== 10 Saat Sonra Hatırlatma Task ==================
async def token_reminder_task(app):
    global last_token_change
    while True:
        if last_token_change:
            now = datetime.utcnow()
            if now - last_token_change >= timedelta(hours=10):
                for admin_id in ADMIN_IDS:
                    try:
                        await app.bot.send_message(admin_id, "⚠️ Betco token 10 saat oldu, güncellemeniz gerekebilir!")
                    except Exception as e:
                        print(f"Mesaj gönderilemedi: {e}")
                last_token_change = None 
        await asyncio.sleep(60 * 60) 

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
    
    # Mevcut kullanıcı listesini yükle
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            u_list = json.load(f)
    except Exception:
        u_list = []

    # Kullanıcı zaten kayıtlı mı kontrol et
    user_exists = False
    for u in u_list:
        if isinstance(u, dict) and u.get("id") == uid:
            user_exists = True
            # Eğer kullanıcı daha önce engellediyse ve şimdi tekrar start verdiyse durumunu aktife çekiyoruz
            u["status"] = "active"
            u["username"] = username
            break
        elif isinstance(u, (int, str)) and str(u) == str(uid):
            # Eski düz int listesi yapısı varsa onu yeni sözlük (dict) yapısına taşıyoruz
            u_list.remove(u)
            break

    if not user_exists:
        # 🚀 YENİLİK: Kullanıcıyı detaylı verileriyle (tarih ve durum) kaydediyoruz
        new_user = {
            "id": uid,
            "username": username,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active"  # active veya blocked
        }
        u_list.append(new_user)
        print(f"🆕 Yeni kullanıcı kaydedildi: {uid} (@{username})")

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(u_list, f, ensure_ascii=False, indent=4)

    await update.message.reply_text("Merhaba! Botumuza hoş geldiniz.")

async def send_invite_message(update: Update):
    user_name = update.effective_user.first_name
    photo_url = "https://r.resimlink.com/wcgRmJG.jpg"
    caption_text = f"Sayın {user_name}, Telegram kanalımızı henüz takibe almadığınız için etkinliğimizden yararlanamamaktasınız.\n\n📢 Kanalımıza katılmak için lütfen aşağıdaki butona tıklayınız"
    keyboard = [
        [InlineKeyboardButton("🎯 Kanala katılmak için hemen tıkla", url="https://t.me/diorresminew")],
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

async def give_bonus(client_id: int, bonus_type: str):
    bonus_cfg = BONUS_MAP.get(bonus_type)
    if not bonus_cfg: return {"HasError": True, "AlertMessage": f"Bilinmeyen bonus tipi: {bonus_type}"}
    payload = {"ClientId": client_id, "MessageChannel": None, "Amount": bonus_cfg["Amount"], "MessageSubject": None, "MessageContent": None, "Count": None, "PartnerBonusId": bonus_cfg["PartnerBonusId"]}
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
    if not username: return

    save_user(tg_user_id)
    await update.message.reply_text("🔍 Kullanıcı adı sorgulanıyor, lütfen bekleyin...")

    try: api_result = await betco_find_user(username)
    except Exception: api_result = None

    user = (api_result.get("user") if api_result else {}) or {}
    client_id = user.get("Id")
    detail = {}
    if client_id:
        try:
            detail_resp = await betco_get_user_by_id(client_id)
            if detail_resp and not detail_resp.get("HasError"): detail = detail_resp.get("Data") or {}
        except Exception: pass

    FirstName = detail.get("FirstName") or user.get("FirstName") or ""
    MiddleName = detail.get("MiddleName") or user.get("MiddleName") or ""
    LastName = detail.get("LastName") or user.get("LastName") or ""
    DocNumber = detail.get("DocNumber") or user.get("DocNumber") or ""
    BirthDate = detail.get("BirthDate") or user.get("BirthDate") or ""

    try:
        if not DocNumber:
            await update.message.reply_text("❌ Kullanıcının TC bilgisi bulunamadı, doğrulama yapılamıyor.")
            return
        if not BirthDate:
            await update.message.reply_text("❌ Kullanıcının doğum tarihi bulunamadı, doğrulama yapılamıyor.")
            return
        birth_year = datetime.fromisoformat(BirthDate.split("T")[0]).year
        
        conn = mariadb.connect(**DB_CONFIG)
        cursor = conn.cursor()
        clauses, params = ["TC = %s", "DOGUMTARIHI LIKE %s"], [DocNumber, f"%{birth_year}"]

        full_name = f"{FirstName} {MiddleName}".strip()
        if full_name: clauses.append("UPPER(ADI) = %s"); params.append(full_name.upper())
        if LastName: clauses.append("UPPER(SOYADI) = %s"); params.append(LastName.upper())

        cursor.execute("SELECT * FROM 101m WHERE " + " AND ".join(clauses), tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"❌ Doğrulama hatası oluştu: {e}")
        return

    if not rows:
        await update.message.reply_text("❌ TC veya diğer bilgiler doğrulanmadı. \n\nEğer yanlış kullanıcı adı yazdıysanız tekrar deneyin.")
        return

    await update.message.reply_text("✅ TC doğrulandı, diğer filtrelere geçiliyor...")
    
    # Filtre Kontrolleri (Kayıt Tarihi, Casino, Yatırım, Bonus Geçmişi)
    created_date_str = detail.get("CreatedLocalDate") or user.get("CreatedLocalDate")
    if created_date_str:
        c_date = datetime.fromisoformat(created_date_str.split("T")[0])
        if c_date < datetime.combine(datetime.now().date() - timedelta(days=7), datetime.min.time()):
            await update.message.reply_text("❌ Son 7 gün içinde kayıt olmadığınız için bonus hakkınız yoktur.")
            return

    if detail.get("LastCasinoBetLocalDate") or detail.get("LastCasinoBetTime"):
        await update.message.reply_text("⚠️ Daha önceden casino oynamış olduğunuz için bonus hakkınız bulunmamaktadır.")
        return
    if detail.get("FirstDepositLocalDate") or detail.get("FirstDepositTime"):
        await update.message.reply_text("⚠️ Daha önceden yatırım yaptığınız için bonus hakkınız bulunmamaktadır.")
        return

    if client_id:
        last_ip = await betco_get_last_login_ip(client_id)
        if last_ip:
            ip_conflict, _ = await check_ip_conflict(last_ip)
            if ip_conflict:
                await update.message.reply_text("❌ IP çakışması tespit edildi! Bu nedenle bonus alamazsınız.")
                return

        keyboard = [
            [InlineKeyboardButton("🎰 500 FreeSpin", callback_data=f"bonus_freespin_{client_id}")],
            [InlineKeyboardButton("⚽ 50 FreeBet", callback_data=f"bonus_freebet_{client_id}")]
        ]
        await update.message.reply_text("🎉 Bonusunuzu seçiniz:", reply_markup=InlineKeyboardMarkup(keyboard))

async def bonus_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id 

    if has_taken_bonus(user_id):
        await query.answer("⚠️ Bu Telegram hesabı üzerinden daha önce bonus alındı!", show_alert=True)
        return

    if query.data.startswith("bonus_"):
        _, bonus_type, client_id_str = query.data.split("_")
        resp = await give_bonus(int(client_id_str), bonus_type)
        if resp.get("HasError"):
            await query.edit_message_text(f"❌ {bonus_type} yüklenemedi: {resp.get('AlertMessage')}")
        else:
            await query.edit_message_text(f"✅ {bonus_type.upper()} hesabınıza başarıyla yüklendi!")
            mark_bonus_given(user_id)

# ================== 🔐 Sadece Adminlerin Görebileceği Panel Komutu ==================
async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Admin kontrolü
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bu paneli açmaya yetkiniz bulunmamaktadır!")
        return

    # WebAppInfo ile butona basıldığında Telegram içinden açılmasını tetikliyoruz
    keyboard = [
        [InlineKeyboardButton("📱 Toplu Mesaj Panelini Aç", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    await update.message.reply_text(
        "🛠 **DiorResmi Yönetim Arayüzü**\n\nAşağıdaki butona tıklayarak toplu duyuru panelini doğrudan bot ekranından yönetebilirsiniz.",
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
    <title>Gelişmiş Duyuru Paneli</title>
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
            max-width: 600px;
            background: #1e1e1e;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        h2 { text-align: center; color: #ffffff; margin-bottom: 20px; font-weight: 600; }
        .stats-box {
            display: flex;
            justify-content: space-between;
            background: #252525;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
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
        label { display: block; margin-bottom: 8px; font-weight: 500; font-size: 14px; color: #aaaaaa; }
        
        /* Sürükle Bırak ve Yapıştır Alanı */
        .drop-zone {
            width: 100%;
            height: 150px;
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
        .drop-zone img { max-height: 130px; max-width: 100%; border-radius: 6px; display: none; }
        
        textarea {
            width: 100%;
            height: 140px;
            background: #252525;
            border: 1px solid #333333;
            border-radius: 8px;
            color: #ffffff;
            padding: 12px;
            box-sizing: border-box;
            resize: vertical;
            font-size: 15px;
            margin-bottom: 5px;
        }
        textarea:focus { border-color: #00adb5; outline: none; }
        
        /* Gelişmiş Metin Editörü Araçları */
        .editor-tools {
            display: flex;
            gap: 6px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .tool-btn {
            background-color: #2d2d2d;
            border: 1px solid #444444;
            color: #eeeeee;
            padding: 6px 14px;
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
            padding: 12px;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 14px;
            text-align: center;
        }
        .btn-primary { background: #00adb5; color: white; width: 100%; margin-top: 10px; font-size: 16px; }
        .btn-primary:hover { background: #008c9e; }
        .btn-secondary { background: #393e46; color: #eeeeee; }
        .btn-secondary:hover { background: #4b525d; }
        .btn-danger { background: #ff4141; color: white; }
        .btn-danger:hover { background: #dd3333; }
        
        /* Taslak Yönetim Bölümü */
        .draft-section {
            background: #252525;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #333;
        }
        select {
            width: 100%;
            padding: 10px;
            background: #1e1e1e;
            border: 1px solid #444;
            color: white;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            background: #1e1e1e;
            border: 1px solid #444;
            color: white;
            border-radius: 6px;
            box-sizing: border-box;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>

<div class="container">
    <h2>📢 DiorResmi Yönetim Paneli</h2>
    
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

    <div class="draft-section">
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

    <div class="draft-section" style="background: transparent; border: none; padding: 0;">
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
            
            <button type="submit" name="action" value="send" class="btn btn-primary" onclick="return confirm('Tüm kullanıcılara duyuru gönderilecektir. Onaylıyor musunuz?')">🚀 Toplu Duyuruyu Başlat</button>
        </form>
    </div>
</div>

<script>
    // 🛠️ Metin Biçimlendirme JavaScript Fonksiyonları
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

    // Sürükle bırak efektleri
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('drag-over'); });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if(files.length > 0) { handleImage(files[0]); }
    });

    // Tıklayarak dosya seçme alternatifi
    dropZone.addEventListener('click', () => {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.onchange = (e) => { if(e.target.files.length > 0) handleImage(e.target.files[0]); };
        fileInput.click();
    });

    // CTRL+V ile Resim Yakalama
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
        if (!file.type.match('image.*')) { alert('Lütfen sadece resim dosyası yükleyin kanka!'); return; }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = function() {
                // 🚀 ÇÖZÜM: Resmin maksimum genişliğini 1024px ile sınırlıyoruz
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

                // 🚀 ÇÖZÜM: Resmi JPEG formatına çevirip %60 oranında sıkıştırıyoruz (KB seviyesine düşer)
                const dataUrl = canvas.toDataURL('image/jpeg', 0.6); 
                
                previewImg.src = dataUrl;
                previewImg.style.display = 'block';
                dropText.style.display = 'none';
                photoUrlInput.value = dataUrl; // Artık çok hafif bir veri gönderilecek
                console.log("Resim başarıyla sıkıştırıldı, ngrok sınırından kurtuldu!");
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

    # 1. Aşama: drafts.json dosyasından tüm kayıtlı taslakların başlıklarını yükle
    all_drafts = {}
    if os.path.exists(DRAFT_FILE):
        try:
            with open(DRAFT_FILE, "r", encoding="utf-8") as f:
                all_drafts = json.load(f)
        except Exception:
            all_drafts = {}

    # 2. Aşama: POST istekleri (Arayüz buton işlemleri)
    if request.method == "POST":
        action = request.form.get("action")
        msg_content = request.form.get("message", "")
        photo_url = request.form.get("photo_url", "")  # Sıkıştırılmış hafif Base64 verisi buraya gelir
        draft_title = request.form.get("draft_title", "").strip()
        selected_draft = request.form.get("selected_draft", "")

        # 💾 Başlıkla Taslak Kaydetme Butonu
        if action == "save":
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

        # 🚀 🚀 İNCE AYARLI DUYURUYU BAŞLAT (SEND) BLOĞU 🚀 🚀
        elif action == "send":
            # KORUMA: Arayüzden veya eski taslaklardan gelebilecek tüm <br> etiketlerini \n yapıyoruz
            msg_content = msg_content.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
            
            draft_text = msg_content
            draft_photo = photo_url
            
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    all_users = json.load(f)
                
                # OPTİMİZASYON: Engelli kullanıcıları listeden eliyoruz, sadece aktif kullanıcıları kuyruğa alıyoruz
                u_list = [u for u in all_users if isinstance(u, dict) and u.get("status") != "blocked"]
                
                # Eğer listede eski düz int ID'ler kalmışsa onları da kuyruğa ekle (Veri kaybı olmaması için)
                for u in all_users:
                    if not isinstance(u, dict):
                        u_list.append(u)
                        
            except Exception: 
                u_list = []

            if not u_list:
                status = "❌ Gönderilecek aktif kullanıcı bulunamadı (users.json boş veya herkes engelli)."
            else:
                # Thread'ler arası asenkron döngüye görevi güvenle teslim ediyoruz
                if telegram_app is not None and telegram_loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        send_bulk_message(u_list, msg_content, photo_url), 
                        telegram_loop
                    )
                    status = f"🚀 Toplu mesaj gönderimi {len(u_list)} AKTİF abone için arka planda başarıyla başlatıldı!"
                else:
                    status = "❌ Bot motoru veya loop senkronizasyonu henüz hazır değil."

    # 3. Aşama: Şablonu render etme ve dinamik taslak listesini gönderme
    return render_template_string(
        PANEL_TEMPLATE, 
        stats=get_user_counts(), 
        status=status, 
        draft_text=draft_text, 
        draft_photo=draft_photo,
        all_drafts=list(all_drafts.keys())
    )
async def send_bulk_message(user_ids, text, photo_url=None):
    print(f"[PANEL DUYURU] Gönderim işlemi arka planda başlatılıyor...")
    
    # 1. Aşama: Güncel kullanıcı listesini oku
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            current_users = json.load(f)
    except Exception:
        print("❌ Kullanıcı listesi okunamadı.")
        return

    # 2. Aşama: Resmi hazırla
    photo_file = None
    if photo_url and photo_url.startswith("data:image"):
        try:
            format, imgstr = photo_url.split(';base64,') 
            ext = format.split('/')[-1]
            photo_file = BytesIO(base64.b64decode(imgstr))
            photo_file.name = f"broadcast_img.{ext}"
        except Exception as e:
            print(f"❌ Resim çözme hatası: {e}")

    # 3. Aşama: Sadece aktif olan kullanıcılara döngü kur
    blocked_detected = []  # Bu gönderimde yeni engellediğini fark ettiğimiz kişiler

    for u in current_users:
        # Eğer kullanıcı bilgisi dict ise ve daha önce engellediyse DİREKT GEÇ (Zaman kazancı 🚀)
        if isinstance(u, dict):
            if u.get("status") == "blocked":
                continue
            uid = u.get("id")
        else:
            uid = u # Eski düz ID yapısı için uyumluluk

        try:
            if photo_file:
                photo_file.seek(0)
                await telegram_app.bot.send_photo(chat_id=uid, photo=photo_file, caption=text, parse_mode="HTML")
            elif photo_url and photo_url.strip() and photo_url.startswith("http"):
                await telegram_app.bot.send_photo(chat_id=uid, photo=photo_url, caption=text, parse_mode="HTML")
            else:
                await telegram_app.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            
            # Telegram rate limitlerine takılmamak için minik bir nefes payı
            await asyncio.sleep(0.05)

        except Exception as e:
            error_msg = str(e).lower()
            # 🚀 KESİN KORUMA: Eğer kullanıcı botu engellediyse veya hesap kapandıysa tetiklenir
            if "blocked" in error_msg or "chat not found" in error_msg or "user is deactivated" in error_msg:
                print(f"🚫 Kullanıcının engellediği tespit edildi, listeye işaretleniyor: {uid}")
                blocked_detected.append(uid)
            else:
                print(f"⚠️ Mesaj iletilemedi ({uid}), geçici hata: {e}")

    # 4. Aşama: Yeni engellemiş kullanıcıları veritabanına (users.json) işle
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

# ================== Runner / Başlatıcı ==================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    telegram_app = app 

    # 🚀 ÇÖZÜM: Python'ın güncel yapısına uygun olarak ana asenkron loop'u güvenle bağlıyoruz
    telegram_loop = asyncio.get_event_loop_policy().get_event_loop()

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
    app.run_polling()