import os
import time
import requests
import matplotlib.pyplot as plt
import numpy as np
import json
import pandas as pd
import math
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import matplotlib
matplotlib.use('Agg')

# ============================================================================
# YAPILANDIRMA AYARLARI - BURAYA KENDİ BİLGİLERİNİZİ GİRİN
# ============================================================================

BOT_TOKEN = "8259780486:AAFfQa1fHpxtKo9rpNrWlD8A6gzco3jrzao"
TARGET_GROUP_ID = -1003644658251
SCHEDULE_HOUR = 9
SCHEDULE_MINUTE = 0
AUTHORIZED_USERS = [5695472914]

# ============================================================================
# TRADINGVIEW TARAMA AYARLARI
# ============================================================================

TRADINGVIEW_PAYLOAD_BIST_DIP = {
    "columns": [
        "name", "description", "logoid", "update_mode", "type", "typespecs",
        "close", "pricescale", "minmov", "fractional", "minmove2", "currency",
        "change", "volume", "relative_volume_10d_calc", "market_cap_basic",
        "fundamental_currency_code", "price_earnings_ttm",
        "earnings_per_share_diluted_ttm", "earnings_per_share_diluted_yoy_growth_ttm",
        "dividends_yield_current", "sector.tr", "market", "sector",
        "AnalystRating", "AnalystRating.tr", "exchange"
    ],
    "filter": [
        {"left": "RSI", "operation": "less", "right": 30},
        {"left": "Stoch.RSI.K", "operation": "less", "right": 20}
    ],
    "markets": ["turkey"],
    "options": {"lang": "en"},
    "range": [0, 5000],
    "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"}
}

# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================

def add_watermark(fig, text="@BISTDipTarayici_Bot"):
    """Grafiğe filigran ekler"""
    try:
        fig.text(
            0.5, 0.90, 
            text, 
            fontsize=30, 
            color='gray', 
            alpha=0.3, 
            ha='right', 
            va='top', 
            rotation=15,
            transform=fig.transFigure
        )
    except Exception as e:
        print(f"Filigran ekleme hatası: {e}")

def get_screener_data_from_payload(payload, url):
    """TradingView'dan tarama verilerini çeker"""
    data_json = json.dumps(payload)
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/100.0 Safari/537.36'
    }

    try:
        response = requests.post(url, headers=headers, data=data_json, timeout=15)
        response.raise_for_status()
        result = response.json()

        df_data = []
        column_names = payload["columns"]

        for item in result.get("data", []):
            symbol_pro_name = item.get("s", "")
            symbol = symbol_pro_name.split(":")[-1]
            values_list = item.get("d", [])

            row_dict = {"Symbol": symbol}
            for i, col_name in enumerate(column_names):
                row_dict[col_name] = values_list[i] if i < len(values_list) else None
            df_data.append(row_dict)

        df = pd.DataFrame(df_data)
        return df, result.get("totalCount", 0)

    except Exception as e:
        print(f"❌ TradingView Veri Çekme Hatası: {e}")
        return pd.DataFrame(), 0

def create_table_png_bist_dip(df, filename_prefix="TR_tablo_dip"):
    """Tarama sonuçlarından PNG tablo oluşturur"""
    try:
        tablo_df = df[["Symbol", "close"]].copy()
        col_fiyat = "Fiyat (₺)"
        tablo_df.rename(columns={"Symbol": "Hisse", "close": col_fiyat}, inplace=True)

        total_rows = len(tablo_df)
        PAGE_SIZE = 20
        total_pages = math.ceil(total_rows / PAGE_SIZE)

        created_files = []

        for page in range(total_pages):
            start = page * PAGE_SIZE
            end = min(start + PAGE_SIZE, total_rows)
            chunk = tablo_df.iloc[start:end]

            mid = len(chunk) // 2 + len(chunk) % 2
            left = chunk.iloc[:mid].reset_index(drop=True)
            right = chunk.iloc[mid:].reset_index(drop=True)

            while len(right) < mid:
                right = pd.concat([right, pd.DataFrame([["", ""]] * (mid - len(right)), columns=right.columns)], ignore_index=True)
                
            combined = pd.DataFrame({
                "Hisse": left["Hisse"],
                col_fiyat: left[col_fiyat],
                "Hisse_2": right["Hisse"],
                f"{col_fiyat}_2": right[col_fiyat]
            })

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.axis("off")
            fig.patch.set_facecolor("#1e1e1e")

            ax.text(
                0.5, 1.05,
                f"Dip Taraması BIST (Sayfa {page+1}/{total_pages})",
                color="white", fontsize=13, fontweight="bold", ha="center", transform=ax.transAxes
            )

            table = ax.table(
                cellText=combined.values,
                colLabels=["Hisse", col_fiyat, "Hisse", col_fiyat],
                cellLoc="center",
                loc="center"
            )

            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 1.4)

            for (row, col), cell in table.get_celld().items():
                if row == 0:
                    cell.set_facecolor("#333333")
                    cell.set_text_props(color="white", fontweight="bold")
                else:
                    cell.set_facecolor("#1e1e1e")
                    cell.set_text_props(color="white")
                cell.set_edgecolor("#444444")

            add_watermark(fig)

            plt.tight_layout()
            file_name = f"{filename_prefix}_{page + 1}.png"
            plt.savefig(file_name, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            created_files.append(file_name)
            print(f"🖼️ {file_name} oluşturuldu.")
        
        return created_files
    except Exception as e:
        print(f"❌ PNG oluşturma hatası: {e}")
        return []

def format_text_results(df, total_count):
    """Tarama sonuçlarını yazı formatına dönüştürür"""
    try:
        if df.empty:
            return "❌ Tarama sonucu bulunamadı."
        
        message = f"📊 **BIST Dip Taraması Sonuçları**\n"
        message += f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        message += f"🔢 Toplam Bulunan: **{total_count}** hisse\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        display_df = df[["Symbol", "close"]].head(50)
        
        for idx, row in display_df.iterrows():
            symbol = row["Symbol"]
            price = row["close"]
            message += f"🔹 **{symbol}**: {price:.2f} ₺\n"
            
            if len(message) > 3500:
                message += f"\n... ve {total_count - idx - 1} hisse daha\n"
                break
        
        message += "\n━━━━━━━━━━━━━━━━━━━━\n"
        message += "⚠️ Bu tarama bilgilendirme amaçlıdır, yatırım tavsiyesi değildir."
        
        return message
    except Exception as e:
        print(f"❌ Metin formatlama hatası: {e}")
        return "❌ Sonuçlar formatlanırken hata oluştu."

# ============================================================================
# TARAMA VE GÖNDERME FONKSİYONU
# ============================================================================

async def send_daily_scan(context: ContextTypes.DEFAULT_TYPE):
    """Günlük taramayı yapar ve gruba gönderir"""
    print(f"\n{'='*60}")
    print(f"🔄 Günlük tarama başlatıldı: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    scanner_url = "https://scanner.tradingview.com/turkey/scan"
    
    try:
        status_msg = await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text="⏳ Günlük BIST Dip Taraması başlatılıyor..."
        )
        
        df_result, total_count = get_screener_data_from_payload(
            TRADINGVIEW_PAYLOAD_BIST_DIP, 
            scanner_url
        )
        
        if df_result.empty:
            await status_msg.edit_text("❌ Tarama sonucu bulunamadı veya veri çekme hatası oluştu.")
            return
        
        filename_prefix = f"daily_scan_{datetime.now().strftime('%Y%m%d')}"
        png_files = create_table_png_bist_dip(df_result, filename_prefix)
        
        if png_files:
            await status_msg.edit_text("📤 Tarama tamamlandı, resimler gönderiliyor...")
            
            for idx, file_name in enumerate(png_files):
                try:
                    with open(file_name, "rb") as img:
                        caption = f"📈 **Günlük BIST Dip Taraması** ({idx+1}/{len(png_files)})\n"
                        caption += f"📅 {datetime.now().strftime('%d.%m.%Y')}\n"
                        caption += f"🔢 Toplam: {total_count} hisse"
                        
                        await context.bot.send_photo(
                            chat_id=TARGET_GROUP_ID,
                            photo=img,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                    print(f"✅ {file_name} gönderildi.")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"❌ PNG gönderme hatası ({file_name}): {e}")
                finally:
                    if os.path.exists(file_name):
                        try:
                            os.remove(file_name)
                        except:
                            pass
        
        text_results = format_text_results(df_result, total_count)
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=text_results,
            parse_mode='Markdown'
        )
        
        await status_msg.edit_text(
            f"✅ Günlük tarama tamamlandı!\n"
            f"📊 {total_count} hisse bulundu"
        )
        
        print(f"\n✅ Tarama başarıyla tamamlandı ve gruba gönderildi.")
        print(f"📊 Toplam bulunan hisse: {total_count}")
        print(f"🖼️ Gönderilen resim sayısı: {len(png_files)}\n")
        
    except Exception as e:
        error_msg = f"❌ Günlük tarama hatası: {e}"
        print(error_msg)
        try:
            await context.bot.send_message(
                chat_id=TARGET_GROUP_ID,
                text=error_msg
            )
        except:
            pass

# ============================================================================
# MANUEL TARAMA KOMUTU
# ============================================================================

async def manual_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manuel tarama komutu (/tarama)"""
    await send_daily_scan(context)

# ============================================================================
# DUYURU SİSTEMİ
# ============================================================================

async def duyuru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yetkililer için duyuru gönderme komutu"""
    user_id = update.effective_user.id
    
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Bu komutu kullanma yetkiniz yok.")
        return
    
    try:
        if update.message.photo:
            caption = update.message.caption or ""
            announcement_text = caption.replace('/duyuru', '').strip()
            photo = update.message.photo[-1]
            
            if announcement_text:
                await context.bot.send_photo(
                    chat_id=TARGET_GROUP_ID,
                    photo=photo.file_id,
                    caption=announcement_text,
                    parse_mode='Markdown'
                )
            else:
                await context.bot.send_photo(
                    chat_id=TARGET_GROUP_ID,
                    photo=photo.file_id
                )
            
            await update.message.reply_text("✅ Resimli duyuru başarıyla gruba gönderildi!")
            return
        
        if update.message.reply_to_message and update.message.reply_to_message.photo:
            announcement_text = update.message.text.replace('/duyuru', '').strip()
            photo = update.message.reply_to_message.photo[-1]
            
            if announcement_text:
                await context.bot.send_photo(
                    chat_id=TARGET_GROUP_ID,
                    photo=photo.file_id,
                    caption=announcement_text,
                    parse_mode='Markdown'
                )
            else:
                await context.bot.send_photo(
                    chat_id=TARGET_GROUP_ID,
                    photo=photo.file_id
                )
            
            await update.message.reply_text("✅ Resimli duyuru başarıyla gruba gönderildi!")
            return
        
        announcement_text = update.message.text.partition(' ')[2]
        
        if not announcement_text:
            help_text = (
                "📢 **Duyuru Gönderme Kılavuzu**\n\n"
                "**Sadece Metin:**\n"
                "`/duyuru Buraya mesajınızı yazın`\n\n"
                "**Resimli:**\n"
                "1️⃣ Resmi yükleyin ve caption'a `/duyuru` ekleyin\n"
                "2️⃣ VEYA resme reply yapıp `/duyuru mesajınız` yazın\n\n"
                "💡 **Özellikler:**\n"
                "• Markdown formatı desteklenir (**kalın**, *italik*)\n\n"
                "⚠️ Bu komutu sadece yetkili kullanıcılar kullanabilir."
            )
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        await context.bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text=announcement_text,
            parse_mode='Markdown'
        )
        await update.message.reply_text("✅ Duyuru başarıyla gruba gönderildi!")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Duyuru gönderme hatası: {e}")
        print(f"Duyuru hatası: {e}")

# ============================================================================
# BOT BAŞLATMA
# ============================================================================

async def run_initial_scan(app):
    """Bot başladığında ilk taramayı yapar"""
    await asyncio.sleep(5)  # Bot tam olarak başlaması için bekle
    try:
        await send_daily_scan(app)
    except Exception as e:
        print(f"❌ İlk tarama hatası: {e}")

def main():
    print("\n" + "="*60)
    print("🤖 BIST Günlük Dip Taraması Botu Başlatılıyor...")
    print("="*60 + "\n")
    
    print(f"📌 Hedef Grup ID: {TARGET_GROUP_ID}")
    print(f"⏰ Zamanlanmış Saat: {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}")
    print(f"🔄 Bot başladıktan 5 saniye sonra ilk tarama yapılacak\n")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("tarama", manual_scan))
    app.add_handler(CommandHandler("duyuru", duyuru))
    
    scheduler = AsyncIOScheduler()
    
    scheduler.add_job(
        send_daily_scan,
        'cron',
        hour=SCHEDULE_HOUR,
        minute=SCHEDULE_MINUTE,
        args=[app]
    )
    
    scheduler.start()
    
    # İlk taramayı ayrı bir task olarak çalıştır
    asyncio.get_event_loop().create_task(run_initial_scan(app))
    
    print("✅ Bot çalışıyor ve görevler zamanlandı!")
    print("💡 Manuel tarama için gruba /tarama yazabilirsiniz")
    print("🛑 Durdurmak için Ctrl+C tuşlarına basın\n")
    print("="*60 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
