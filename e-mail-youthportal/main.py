import os
import logging
import smtplib
import time
import warnings
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv

# SELENIUM GEREKSİNİMLERİ
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Pandas uyarılarını sessize al
warnings.simplefilter(action='ignore', category=FutureWarning)

# 1. LOGGING YAPILANDIRMASI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Metnin içinden e-posta adresini ayıklayan yardımcı fonksiyon (Regex)
def extract_email(text: str) -> str:
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else ""

# 2. HEDEFE YÖNELİK WEB SCRAPING MODÜLÜ
def scrape_actual_institution_names() -> set:
    base_url = "https://youth.europa.eu"
    start_url = f"{base_url}/go-abroad/volunteering/opportunities_en"
    actual_institutions = set()
    
    logging.info("Selenium ile ana sayfa yükleniyor: %s", start_url)
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(start_url)
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "card-title"))
        )
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        detail_links = set()
        btn_links = soup.select("a.btn[href*='/opportunity/']")
        
        for btn in btn_links:
            href = btn.get('href')
            if href:
                full_url = href if href.startswith("http") else base_url + href
                detail_links.add(full_url)
                
        logging.info("Ana sayfadan toplam %d adet 'Read more' detay linki yakalandı.", len(detail_links))
        
        for index, detail_url in enumerate(detail_links, 1):
            try:
                logging.info("[%d/%d] Detay sayfasına giriliyor: %s", index, len(detail_links), detail_url)
                driver.get(detail_url)
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "org-box"))
                )
                
                detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
                org_box = detail_soup.find("div", class_="org-box")
                
                if org_box:
                    h3_tag = org_box.find("h3")
                    if h3_tag:
                        institution_name = h3_tag.get_text(strip=True)
                        if institution_name:
                            logging.info("-> Başarıyla Çekilen Kurum Adı: %s", institution_name)
                            actual_institutions.add(institution_name)
            except Exception as e:
                logging.error("Detay sayfası taranırken pas geçildi: %s", e)
                continue

        return actual_institutions
    except Exception as e:
        logging.error("Scraping hatası: %s", e)
        return actual_institutions
    finally:
        if driver:
            driver.quit()

# 3. GOOGLE SHEETS MODÜLÜ (DÜZENSİZ VERİ İÇİN OPTİMİZE EDİLDİ)
def get_google_sheet_data() -> pd.DataFrame:
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    logging.info("Herkese açık Google Sheet verisi indiriliyor...")
    try:
        response = requests.get(csv_url, timeout=15)
        response.raise_for_status()
        
        from io import StringIO
        csv_data = StringIO(response.text)
        pd.set_option('mode.copy_on_write', True)
        df = pd.read_csv(csv_data)
        
        logging.info("Google Sheet verileri başarıyla indirildi. Satır sayısı: %d", len(df))
        return df
    except Exception as e:
        logging.error("Google Sheet hatası: %s", e)
        return pd.DataFrame()

# 4. SMTP E-POSTA GÖNDERİM MODÜLÜ
def send_email(to_email: str, institution_name: str):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, sender_email, sender_password, to_email]):
        logging.error("E-posta gönderimi için eksik yapılandırma.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = f"Avrupa Gençlik Portalı Aktivasyon Takibi - {institution_name}"

    body = f"""
    Merhaba {institution_name} Yetkilisi,
    
    Kurumunuzun Avrupa Gençlik Portalı üzerindeki güncel durum listeleri sistemimiz tarafından başarıyla taranmıştır. 
    İletişim bilgileriniz veri tabanımızda güncel olarak yer almaktadır. Süreçlerinize kesintisiz devam edebilirsiniz.
    
    İyi çalışmalar dileriz.
    """
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        logging.info("%s kurumuna e-posta gönderiliyor (%s)...", institution_name, to_email)
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        logging.info("%s kurumuna e-posta başarıyla gönderildi.", institution_name)
    except Exception as e:
        logging.error("%s e-posta hatası: %s", institution_name, e)

# 5. TELEGRAM BİLDİRİM MODÜLÜ
def send_telegram_notification(institution_name: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    message_text = f"⚠️ Kanka, {institution_name} portalda mevcut ancak Google Sheet dosyasında iletişim bilgisi bulunamadı. Lütfen manuel olarak kontrol sağlar mısınız?"
    
    payload = {"chat_id": chat_id, "text": message_text}
    try:
        logging.info("Telegram bildirimi gönderiliyor: %s", institution_name)
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logging.error("Telegram hatası: %s", e)

# 6. ANA AKIŞ ORKESTRASYONU
def main():
    logging.info("=== Otomasyon Süreci Başladı ===")
    
    scraped_institutions = scrape_actual_institution_names()
    if not scraped_institutions:
        logging.error("Web sitesinden hiçbir kurum adı çekilemedi. Süreç sonlandırılıyor.")
        return

    sheet_df = get_google_sheet_data()
    if sheet_df.empty:
        logging.error("Google Sheet verisi okunamadı. Süreç askıya alınıyor.")
        return

    # Excel'deki tüm satırları birleştirilmiş tek bir düz metin sütununa çeviriyoruz.
    # Böylece kolon kayması olsa bile arama tüm satır genelinde yapılacak.
    sheet_df['combined_row'] = sheet_df.astype(str).apply(lambda x: ' '.join(x), axis=1)
    sheet_df['clean_combined_row'] = sheet_df['combined_row'].str.strip().str.lower()

    # Eşleşme ve Bildirim Döngüsü
    for inst_name in scraped_institutions:
        clean_scraped_name = inst_name.strip().lower()
        
        # Birebir eşitlik yerine, "Excel satırının İÇİNDE geçiyor mu?" kontrolü yapıyoruz (Arama Genişletildi)
        match_rows = sheet_df[sheet_df['clean_combined_row'].str.contains(clean_scraped_name, regex=False)]
        
        if not match_rows.empty:
            # Kurum adı satırda bulundu!
            matched_text = match_rows.iloc[0]['combined_row']
            # Satırdaki karmaşık metinden e-postayı Regex ile çekiyoruz
            found_email = extract_email(matched_text)
            
            if found_email:
                send_email(found_email, inst_name)
            else:
                logging.warning("%s Excel'de var ama satırda geçerli bir e-posta bulunamadı.", inst_name)
                send_telegram_notification(inst_name)
        else:
            # Kurum adı Excel satırlarının hiçbirinde geçmiyor!
            logging.info("%s Excel dosyasında bulunamadı. Bildirim tetikleniyor.", inst_name)
            send_telegram_notification(inst_name)

    logging.info("=== Otomasyon Süreci Tamamlandı ===")

if __name__ == "__main__":
    main()