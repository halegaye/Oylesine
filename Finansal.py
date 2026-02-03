import os
import time
import requests
import matplotlib.pyplot as plt
import numpy as np
import json
import pandas as pd
import math
from scipy.signal import find_peaks
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from yahooquery import Ticker
from thefuzz import process
from bs4 import BeautifulSoup # Web scraping için eklendi
import re # Haber başlıklarını temizlemek için eklendi
import sys # Hata çıkışları için eklendi
import matplotlib
matplotlib.use('Agg')


# Lütfen bu TOKEN'ı kendi bot tokeniniz ile değiştirin
BOT_TOKEN = "7932037979:AAHyz8Lay8tDl7nwb4L4WFXfPihn3NjTRW4" 

# --- YÖNETİM DEĞİŞKENLERİ ---
USER_LOG_FILE = "users.txt"
CHANNEL_LOG_FILE = "channel_logs.txt" # Kanal Kayıt Dosyası

# DUYURU VE KANAL YÖNETİMİ İÇİN YETKİLİ KULLANICILARIN TELEGRAM ID'leri
# LÜTFEN KENDİ ID'NİZİ BURAYA YAZINIZ! (Örn: 123456789)
AUTHORIZED_USERS = [5695472914, 5624868688] 
# ----------------------------

BILINEN_HISSELER = {
    "QNBTR": "QNB Bank AS",
    "ASELS": "ASELSAN ELEKTRONİK SANAYİ VE TİCARET A.Ş.",
    "GARAN": "TÜRKİYE GARANTİ BANKASI A.Ş.",
    "ENKAI": "ENKA İNŞAAT VE SANAYİ A.Ş.",
    "KCHOL": "KOÇ HOLDİNG A.Ş.",
    "THYAO": "TÜRK HAVA YOLLARI A.O.",
    "TUPRS": "TÜPRAŞ-TÜRKİYE PETROL RAFİNERİLERİ A.Ş.",
    "ISCTR": "TÜRKİYE İŞ BANKASI A.Ş.",
    "FROTO": "FORD OTOMOTİV SANAYİ A.Ş.",
    "AKBNK": "AKBANK T.A.Ş.",
    "BIMAS": "BİM BİRLEŞİK MAĞAZALAR A.Ş.",
    "YKBNK": "YAPI VE KREDİ BANKASI A.Ş.",
    "VAKBN": "TÜRKİYE VAKIFLAR BANKASI T.A.O.",
    "KLRHO": "KİLER HOLDİNG A.Ş.",
    "DSTKF": "DESTEK FAKTORİNG A.Ş.",
    "TCELL": "TURKCELL İLETİŞİM HİZMETLERİ A.Ş.",
    "EREGL": "EREĞLİ DEMİR VE ÇELİK FABRİKALARI T.A.Ş.",
    "HALKB": "TÜRKİYE HALK BANKASI A.Ş.",
    "TTKOM": "TÜRK TELEKOMÜNİKASYON A.Ş.",
    "SAHOL": "HACI ÖMER SABANCI HOLDİNG A.Ş.",
    "HEDEF": "HEDEF HOLDİNG A.Ş.",
    "TERA": "TERA YATIRIM MENKUL DEĞERLER A.Ş.",
    "CCOLA": "COCA-COLA İÇECEK A.Ş.",
    "SASA": "SASA POLYESTER SANAYİ A.Ş.",
    "TURSG": "TÜRKİYE SİGORTA A.Ş.",
    "KLNMA": "TÜRKİYE KALKINMA VE YATIRIM BANKASI A.Ş.",
    "TOASO": "TOFAŞ TÜRK OTOMOBİL FABRİKASI A.Ş.",
    "QNBFK": "QNB Finansal Kiralama A.S.",
    "ISDMR": "İSKENDERUN DEMİR VE ÇELİK A.Ş.",
    "SISE": "TÜRKİYE ŞİŞE VE CAM FABRİKALARI A.Ş.",
    "ZRGYO": "ZİRAAT GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "PGSUS": "PEGASUS HAVA TAŞIMACILIĞI A.Ş.",
    "OYAKC": "OYAK ÇİMENTO FABRİKALARI A.Ş.",
    "ASTOR": "ASTOR ENERJİ A.Ş.",
    "GUBRF": "GÜBRE FABRİKALARI T.A.Ş.",
    "TAVHL": "TAV HAVALİMANLARI HOLDİNG A.Ş.",
    "UFUK": "UFUK YATIRIM YÖNETİM VE GAYRİMENKUL A.Ş.",
    "PASEU": "Pasifik Eurasia Lojistik dis Ticaret AS",
    "ENJSA": "ENERJİSA ENERJİ A.Ş.",
    "ENERY": "Enerya Enerji A.S.",
    "KOZAL": "KOZA ALTIN İŞLETMELERİ A.Ş.",
    "AEFES": "ANADOLU EFES BİRACILIK VE MALT SANAYİİ A.Ş.",
    "MAGEN": "MARGÜN ENERJİ ÜRETİM SANAYİ VE TİCARET A.Ş.",
    "MGROS": "MİGROS TİCARET A.Ş.",
    "ARCLK": "ARÇELİK A.Ş.",
    "AHGAZ": "AHLATCI DOĞAL GAZ DAĞITIM ENERJİ VE YATIRIM A.Ş.",
    "DMLKT": "Emlak Konut Gayrimenkul Yatirim Ortakligi A.S. 0 % Certificates 2025-31.12.2199",
    "AKSEN": "AKSA ENERJİ ÜRETİM A.Ş.",
    "BRSAN": "BORUSAN MANNESMANN BORU SANAYİ VE TİCARET A.Ş.",
    "TBORG": "TÜRK TUBORG BİRA VE MALT SANAYİİ A.Ş.",
    "BRYAT": "BORUSAN YATIRIM VE PAZARLAMA A.Ş.",
    "RALYH": "RAL YATIRIM HOLDİNG A.Ş.",
    "ISMEN": "İŞ YATIRIM MENKUL DEĞERLER A.Ş.",
    "MPARK": "MLP SAĞLIK HİZMETLERİ A.Ş.",
    "GLRMK": "Gulermak Agir Sanayi Insaat Ve Taahhut A.S.",
    "TABGD": "TAB Gida Sanayi ve Ticaret A.S.",
    "AGHOL": "AG ANADOLU GRUBU HOLDİNG A.Ş.",
    "ECILC": "EİS ECZACIBAŞI İLAÇ SINAİ VE FİNANSAL YATIRIMLAR SANAYİ VE TİCARET A.Ş.",
    "INVES": "INVESTCO HOLDİNG A.Ş.",
    "PEKGY": "PEKER GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "GENIL": "GEN İLAÇ VE SAĞLIK ÜRÜNLERİ SANAYİ VE TİCARET A.Ş.",
    "OTKAR": "OTOKAR OTOMOTİV VE SAVUNMA SANAYİ A.Ş.",
    "TTRAK": "TÜRK TRAKTÖR VE ZİRAAT MAKİNELERİ A.Ş.",
    "LIDER": "LDR TURİZM A.Ş.",
    "EFOR": "Efor Yatirim Sanayi Ticaret A.S.",
    "RGYAS": "RÖNESANS GAYRİMENKUL YATIRIM A.Ş.",
    "GRTHO": "Grainturk Holding A.S.",
    "SELEC": "SELÇUK ECZA DEPOSU TİCARET VE SANAYİ A.Ş.",
    "ANSGR": "ANADOLU ANONİM TÜRK SİGORTA ŞİRKETİ",
    "AKSA": "AKSA AKRİLİK KİMYA SANAYİİ A.Ş.",
    "ANHYT": "ANADOLU HAYAT EMEKLİLİK A.Ş.",
    "DOHOL": "DOĞAN ŞİRKETLER GRUBU HOLDİNG A.Ş.",
    "PETKM": "PETKİM PETROKİMYA HOLDİNG A.Ş.",
    "AYGAZ": "AYGAZ A.Ş.",
    "SMRVA": "Sumer Varlik Yonetim A.S.",
    "RAYSG": "RAY SİGORTA A.Ş.",
    "CIMSA": "ÇİMSA ÇİMENTO SANAYİ VE TİCARET A.Ş.",
    "LYDHO": "Lydia Holding A.S.",
    "ULKER": "ÜLKER BİSKÜVİ SANAYİ A.Ş.",
    "CLEBI": "ÇELEBİ HAVA SERVİSİ A.Ş.",
    "AGESA": "AGESA HAYAT VE EMEKLİLİK A.Ş.",
    "NUHCM": "NUH ÇİMENTO SANAYİ A.Ş.",
    "DOAS": "DOĞUŞ OTOMOTİV SERVİS VE TİCARET A.Ş.",
    "TSKB": "TÜRKİYE SINAİ KALKINMA BANKASI A.Ş.",
    "ALARK": "ALARKO HOLDİNG A.Ş.",
    "GRSEL": "GÜR-SEL TURİZM TAŞIMACILIK VE SERVİS TİCARET A.Ş.",
    "DAPGM": "DAP GAYRİMENKUL GELİŞTİRME A.Ş.",
    "ECZYT": "ECZACIBAŞI YATIRIM HOLDİNG ORTAKLIĞI A.Ş.",
    "POLTK": "POLİTEKNİK METAL SANAYİ VE TİCARET A.Ş.",
    "KOZAA": "KOZA ANADOLU METAL MADENCİLİK İŞLETMELERİ A.Ş.",
    "YGGYO": "YENİ GİMAT GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "MAVI": "MAVİ GİYİM SANAYİ VE TİCARET A.Ş.",
    "LYDYE": "Lydia Yesil Enerji kaynaklari A.S.",
    "HEKTS": "HEKTAŞ TİCARET T.A.Ş.",
    "KRDMD": "KARDEMİR KARABÜK DEMİR ÇELİK SANAYİ VE TİCARET A.Ş.",
    "KRDMA": "KARDEMİR KARABÜK DEMİR ÇELİK SANAYİ VE TİCARET A.Ş.",
    "KRDMB": "KARDEMİR KARABÜK DEMİR ÇELİK SANAYİ VE TİCARET A.Ş.",
    "TKFEN": "TEKFEN HOLDİNG A.Ş.",
    "RYSAS": "REYSAŞ TAŞIMACILIK VE LOJİSTİK TİCARET A.Ş.",
    "CVKMD": "CVK MADEN İŞLETMELERİ SANAYİ VE TİCARET A.Ş.",
    "KTLEV": "KATILIMEVIM TASARRUF FINANSMAN A.S.",
    "BASGZ": "BAŞKENT DOĞALGAZ DAĞITIM GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "BRISA": "BRİSA BRIDGESTONE SABANCI LASTİK SANAYİ VE TİCARET A.Ş.",
    "CWENE": "CW ENERJİ MÜHENDİSLİK TİCARET VE SANAYİ A.Ş.",
    "BSOKE": "BATISÖKE SÖKE ÇİMENTO SANAYİİ T.A.Ş.",
    "SOKM": "ŞOK MARKETLER TİCARET A.Ş.",
    "KCAER": "KOCAER ÇELİK SANAYİ VE TİCARET A.Ş.",
    "BTCIM": "BATIÇİM BATI ANADOLU ÇİMENTO SANAYİİ A.Ş.",
    "EGEEN": "EGE ENDÜSTRİ VE TİCARET A.Ş.",
    "AKCNS": "AKÇANSA ÇİMENTO SANAYİ VE TİCARET A.Ş.",
    "KONYA": "KONYA ÇİMENTO SANAYİİ A.Ş.",
    "IZENR": "Izdemir Enerji Elektrik Uretim A.S.",
    "KLYPV": "Kalyon Gunes Teknolojileri Uretim Anonim Sirketi",
    "NTHOL": "NET HOLDİNG A.Ş.",
    "ODINE": "Odine Solutions Teknoloji Ticaret ve Sanayi AS",
    "MOGAN": "Mogan Enerji Yatirim Holding",
    "QUAGR": "QUA GRANITE HAYAL YAPI VE ÜRÜNLERİ SANAYİ TİCARET A.Ş.",
    "AVPGY": "Avrupakent Gayrimenkul Yatirim Ortakligi SA",
    "TATEN": "Tatlipinar Enerji Uretim A.S.",
    "VERUS": "VERUSA HOLDİNG A.Ş.",
    "BALSU": "Balsu Gida Sanayi ve Ticaret Anonim Sirketi",
    "GESAN": "GİRİŞİM ELEKTRİK SANAYİ TAAHHÜT VE TİCARET A.Ş.",
    "GLYHO": "GLOBAL YATIRIM HOLDİNG A.Ş.",
    "ENTRA": "IC Enterra Yenilenebilir Enerji AS",
    "OBAMS": "Oba Makarnacilik Sanayi Ve Ticaret A. S.",
    "AKFYE": "AKFEN YENİLENEBİLİR ENERJİ A.Ş.",
    "ALBRK": "ALBARAKA TÜRK KATILIM BANKASI A.Ş.",
    "BFREN": "BOSCH FREN SİSTEMLERİ SANAYİ VE TİCARET A.Ş.",
    "KONTR": "KONTROLMATİK TEKNOLOJİ ENERJİ VE MÜHENDİSLİK A.Ş.",
    "SKBNK": "ŞEKERBANK T.A.Ş.",
    "SUNTK": "SUN TEKSTİL SANAYİ VE TİCARET A.Ş.",
    "CEMZY": "CEM ZEYTIN ANONIM SIRKETI",
    "GSRAY": "GALATASARAY SPORTİF SINAİ VE TİCARİ YATIRIMLAR A.Ş.",
    "BINBN": "Bin Ulasim Ve Akilli Sehir Teknolojileri AS",
    "IPEKE": "İPEK DOĞAL ENERJİ KAYNAKLARI ARAŞTIRMA VE ÜRETİM A.Ş.",
    "MRSHL": "MARSHALL BOYA VE VERNİK SANAYİİ A.Ş.",
    "GZNMI": "GEZİNOMİ SEYAHAT TURİZM TİCARET A.Ş.",
    "MIATK": "MİA TEKNOLOJİ A.Ş.",
    "KZBGY": "KIZILBÜK GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "EUPWR": "EUROPOWER ENERJİ VE OTOMASYON TEKNOLOJİLERİ SANAYİ TİCARET A.Ş.",
    "PATEK": "Pasifik Teknoloji AS",
    "ADESE": "ADESE GAYRİMENKUL YATIRIM A.Ş.",
    "BMSTL": "BMS BİRLEŞİK METAL SANAYİ VE TİCARET A.Ş.",
    "ZOREN": "ZORLU ENERJİ ELEKTRİK ÜRETİM A.Ş.",
    "BANVT": "BANVİT BANDIRMA VİTAMİNLİ YEM SANAYİİ A.Ş.",
    "OYYAT": "OYAK YATIRIM MENKUL DEĞERLER A.Ş.",
    "FZLGY": "FUZUL GAYRIMENKUL YATIRIM ORTAKLIGI A.S.",
    "CANTE": "ÇAN2 TERMİK A.Ş.",
    "LILAK": "Lila Kagit Sanayi Ve Ticaret Anonim Sirketi",
    "IEYHO": "IŞIKLAR ENERJİ VE YAPI HOLDİNG A.Ş.",
    "DOFRB": "DOF Robotik Sanayi Anonim Sirketi",
    "BORLS": "Borlease Otomotiv AS",
    "AKFIS": "Akfen insaat Turizm ve Ticaret AS",
    "EUREN": "EUROPEN ENDÜSTRİ İNŞAAT SANAYİ VE TİCARET A.Ş.",
    "SMRTG": "SMART GÜNEŞ ENERJİSİ TEKNOLOJİLERİ ARAŞTIRMA GELİŞTİRME ÜRETİM SANAYİ VE TİCARET A.Ş.",
    "KLSER": "Kaleseramik Canakkale Kalebodur Seramik A.S.",
    "KLKIM": "KALEKİM KİMYEVİ MADDELER SANAYİ VE TİCARET A.Ş.",
    "ULUSE": "ULUSOY ELEKTRİK İMALAT TAAHHÜT VE TİCARET A.Ş.",
    "ALFAS": "ALFA SOLAR ENERJİ SANAYİ VE TİCARET A.Ş.",
    "SARKY": "SARKUYSAN ELEKTROLİTİK BAKIR SANAYİ VE TİCARET A.Ş.",
    "VSNMD": "Visne Madencilik Uretim Sanayi ve Ticaret AS",
    "ALTNY": "Altinay Savunma Teknolojileri A.S.",
    "LOGO": "LOGO YAZILIM SANAYİ VE TİCARET A.Ş.",
    "OZATD": "OZATA DENIZCILIK SANAYI VE TICARET AS",
    "EGPRO": "EGE PROFİL TİCARET VE SANAYİ A.Ş.",
    "ADGYO": "Adra Gayrimenkul Yatirim Ortakligi A.S.",
    "LMKDC": "Limak Dogu Anadolu Cimento Sanayi Ve Ticaret AS",
    "JANTS": "JANTSA JANT SANAYİ VE TİCARET A.Ş.",
    "KOTON": "KOTON MAĞAZACILIK TEKSTİL SANAYİ VE TİCARET A.Ş.",
    "HTTBT": "HİTİT BİLGİSAYAR HİZMETLERİ A.Ş.",
    "CRFSA": "CARREFOURSA CARREFOUR SABANCI TİCARET MERKEZİ A.Ş.",
    "ISKPL": "IŞIK PLASTİK SANAYİ VE DIŞ TİCARET PAZARLAMA A.Ş.",
    "BIENY": "BİEN YAPI ÜRÜNLERİ SANAYİ TURİZM VE TİCARET A.Ş.",
    "ARASE": "DOĞU ARAS ENERJİ YATIRIMLARI A.Ş.",
    "ASUZU": "ANADOLU ISUZU OTOMOTİV SANAYİ VE TİCARET A.Ş.",
    "VESBE": "VESTEL BEYAZ EŞYA SANAYİ VE TİCARET A.Ş.",
    "BINHO": "1000 Yatirimlar Holding AS",
    "POLHO": "POLİSAN HOLDİNG A.Ş.",
    "DEVA": "DEVA HOLDİNG A.Ş.",
    "ISFIN": "İŞ FİNANSAL KİRALAMA A.Ş.",
    "GWIND": "GALATA WIND ENERJİ A.Ş.",
    "TRHOL": "Tera Financial Investments Holding A.S.",
    "AYDEM": "AYDEM YENİLENEBİLİR ENERJİ A.Ş.",
    "TUKAS": "TUKAŞ GIDA SANAYİ VE TİCARET A.Ş.",
    "ENSRI": "ENSARİ DERİ GIDA SANAYİ VE TİCARET A.Ş.",
    "KAYSE": "KAYSERİ ŞEKER FABRİKASI A.Ş.",
    "ESEN": "ESENBOĞA ELEKTRİK ÜRETİM A.Ş.",
    "ICBCT": "ICBC TURKEY BANK A.Ş.",
    "FENER": "FENERBAHÇE FUTBOL A.Ş.",
    "BERA": "BERA HOLDİNG A.Ş.",
    "TMSN": "TÜMOSAN MOTOR VE TRAKTÖR SANAYİ A.Ş.",
    "YYLGD": "YAYLA AGRO GIDA SANAYİ VE TİCARET A.Ş.",
    "YEOTK": "YEO TEKNOLOJİ ENERJİ VE ENDÜSTRİ A.Ş.",
    "BULGS": "Bulls Girisim Sermayesi Yatirim Ortakligi Anonim Sirketi",
    "GEDIK": "GEDİK YATIRIM MENKUL DEĞERLER A.Ş.",
    "GIPTA": "Gipta Ofis Kirtasiye ve Promosyon Urunleri Imalat Sanayi A.S.",
    "AKGRT": "AKSİGORTA A.Ş.",
    "VESTL": "VESTEL ELEKTRONİK SANAYİ VE TİCARET A.Ş.",
    "BIOEN": "BİOTREND ÇEVRE VE ENERJİ YATIRIMLARI A.Ş.",
    "AHSGY": "Ahes Gayrimenkul Yatirim Ortakligi AS",
    "AYCES": "ALTIN YUNUS ÇEŞME TURİSTİK TESİSLER A.Ş.",
    "SDTTR": "SDT UZAY VE SAVUNMA TEKNOLOJİLERİ A.Ş.",
    "VAKKO": "VAKKO TEKSTİL VE HAZIR GİYİM SANAYİ İŞLETMELERİ A.Ş.",
    "INVEO": "INVEO YATIRIM HOLDİNG A.Ş.",
    "EGGUB": "EGE GÜBRE SANAYİİ A.Ş.",
    "SRVGY": "SERVET GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "KORDS": "KORDSA TEKNİK TEKSTİL A.Ş.",
    "MEGMT": "Mega Metal Sanayi Ve Ticaret A.S.",
    "INGRM": "INGRAM MİCRO BİLİŞİM SİSTEMLERİ A.Ş.",
    "GARFA": "GARANTİ FAKTORİNG A.Ş.",
    "HATSN": "Hat-San Gemi Insaa Bakim Onarim Deniz Nakliyat Sanayi ve Ticaret A.S.",
    "OFSYM": "Ofis Yem Gida Sanayi ve Ticaret A.S.",
    "SONME": "SÖNMEZ FİLAMENT SENTETİK İPLİK VE ELYAF SANAYİ A.Ş.",
    "ESCAR": "ESCAR FİLO KİRALAMA HİZMETLERİ A.Ş.",
    "ALCAR": "ALARKO CARRIER SANAYİ VE TİCARET A.Ş.",
    "VAKFN": "VAKIF FİNANSAL KİRALAMA A.Ş.",
    "SNPAM": "SÖNMEZ PAMUKLU SANAYİİ A.Ş.",
    "TRCAS": "TURCAS PETROL A.Ş.",
    "ALKLC": "Altinkilic Gida ve Sut Sanayi Ticaret AS",
    "TSPOR": "TRABZONSPOR SPORTİF YATIRIM VE FUTBOL İŞLETMECİLİĞİ TİCARET A.Ş.",
    "IZMDC": "İZMİR DEMİR ÇELİK SANAYİ A.Ş.",
    "GLCVY": "GELECEK VARLIK YÖNETİMİ A.Ş.",
    "BUCIM": "BURSA ÇİMENTO FABRİKASI A.Ş.",
    "MOPAS": "Mopas Marketcilik Gida Sanayi Ve Ticaret A.S.",
    "BASCM": "BAŞTAŞ BAŞKENT ÇİMENTO SANAYİ VE TİCARET A.Ş.",
    "BESLR": "Besler Gida Ve Kimya Sanayi Ve Ticaret AS",
    "KAPLM": "KAPLAMİN AMBALAJ SANAYİ VE TİCARET A.Ş.",
    "ARMGD": "Armada Gida Ticaret ve Sanayi Anonim Sirketi",
    "BLUME": "Blume Metal Kimya Anonim Sirketi",
    "REEDR": "Reeder Teknoloji Sanayi ve Ticaret A.S.",
    "KARSN": "KARSAN OTOMOTİV SANAYİİ VE TİCARET A.Ş.",
    "KMPUR": "KİMTEKS POLİÜRETAN SANAYİ VE TİCARET A.Ş.",
    "BOSSA": "BOSSA TİCARET VE SANAYİ İŞLETMELERİ T.A.Ş.",
    "AGROT": "Agrotech Yuksek Teknoloji ve Yatirim AS",
    "EMKEL": "EMEK ELEKTRİK ENDÜSTRİSİ A.Ş.",
    "KBORU": "Kuzey Boru A.S.",
    "ATATP": "ATP YAZILIM VE TEKNOLOJİ A.Ş.",
    "KOPOL": "KOZA POLYESTER SANAYİ VE TİCARET A.Ş.",
    "A1CAP": "A1 Capital Yatitim Menkul Degerler A.S.",
    "MNDTR": "MONDİ TURKEY OLUKLU MUKAVVA KAĞIT VE AMBALAJ SANAYİ A.Ş.",
    "PRKAB": "TÜRK PRYSMİAN KABLO VE SİSTEMLERİ A.Ş.",
    "TUREX": "TUREKS TURİZM TAŞIMACILIK A.Ş.",
    "TNZTP": "TAPDİ OKSİJEN ÖZEL SAĞLIK VE EĞİTİM HİZMETLERİ SANAYİ TİCARET A.Ş.",
    "HRKET": "Hareket Proje Tasimaciligi ve Yuk Muhendisligi AS",
    "EBEBK": "EBEBEK MAGAZACILIK ANONIM SIRKETI",
    "GOZDE": "GÖZDE GİRİŞİM SERMAYESİ YATIRIM ORTAKLIĞI A.Ş.",
    "AKENR": "AKENERJİ ELEKTRİK ÜRETİM A.Ş.",
    "BJKAS": "BEŞİKTAŞ FUTBOL YATIRIMLARI SANAYİ VE TİCARET A.Ş.",
    "ADEL": "ADEL KALEMCİLİK TİCARET VE SANAYİ A.Ş.",
    "SURGY": "Sur Tatil Evleri Gayrimenkul Yatirim Ortakligi A.S.",
    "TCKRC": "Kirac Galvaniz Telekominikasyon Metal Makine Insaat Elektrik Sanayi Ve Ticaret AS",
    "IZFAS": "İZMİR FIRÇA SANAYİ VE TİCARET A.Ş.",
    "DOKTA": "DÖKTAŞ DÖKÜMCÜLÜK TİCARET VE SANAYİ A.Ş.",
    "PARSN": "PARSAN MAKİNA PARÇALARI SANAYİİ A.Ş.",
    "MOBTL": "MOBİLTEL İLETİŞİM HİZMETLERİ SANAYİ VE TİCARET A.Ş.",
    "TARKM": "Tarkim Bitki Koruma Sanayi ve Ticaret A.S.",
    "ODAS": "ODAŞ ELEKTRİK ÜRETİM SANAYİ TİCARET A.Ş.",
    "PAGYO": "PANORA GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "YIGIT": "Yigit Aku Malzemeleri Nakliyat Turizm Insaat Sanayi Ve Ticaret",
    "KAREL": "KAREL ELEKTRONİK SANAYİ VE TİCARET A.Ş.",
    "AYEN": "AYEN ENERJİ A.Ş.",
    "GOKNR": "GÖKNUR GIDA MADDELERİ ENERJİ İMALAT İTHALAT İHRACAT TİCARET VE SANAYİ A.Ş.",
    "NTGAZ": "NATURELGAZ SANAYİ VE TİCARET A.Ş.",
    "ALKA": "ALKİM KAĞIT SANAYİ VE TİCARET A.Ş.",
    "EKOS": "Ekos Teknoloji ve Elektrik AS",
    "BOBET": "BOĞAZİÇİ BETON SANAYİ VE TİCARET A.Ş.",
    "KATMR": "KATMERCİLER ARAÇ ÜSTÜ EKİPMAN SANAYİ VE TİCARET A.Ş.",
    "ATAKP": "Atakey Patates Gida Sanayi ve Ticaret AS",
    "BIGCH": "BÜYÜK ŞEFLER GIDA TURİZM TEKSTİL DANIŞMANLIK ORGANİZASYON EĞİTİM SANAYİ VE TİCARET A.Ş.",
    "YBTAS": "YİBİTAŞ YOZGAT İŞÇİ BİRLİĞİ İNŞAAT MALZEMELERİ TİCARET VE SANAYİ A.Ş.",
    "MERIT": "MERİT TURİZM YATIRIM VE İŞLETME A.Ş.",
    "GENTS": "GENTAŞ DEKORATİF YÜZEYLER SANAYİ VE TİCARET A.Ş.",
    "NATEN": "NATUREL YENİLENEBİLİR ENERJİ TİCARET A.Ş.",
    "DESA": "DESA DERİ SANAYİ VE TİCARET A.Ş.",
    "ENDAE": "Enda Enerji Holding Anonim Sirketi",
    "MAALT": "MARMARİS ALTINYUNUS TURİSTİK TESİSLER A.Ş.",
    "GEREL": "GERSAN ELEKTRİK TİCARET VE SANAYİ A.Ş.",
    "KOCMT": "Koc Metalurji AS",
    "PKENT": "PETROKENT TURİZM A.Ş.",
    "IHAAS": "İHLAS HABER AJANSI A.Ş.",
    "LINK": "LİNK BİLGİSAYAR SİSTEMLERİ YAZILIMI VE DONANIMI SANAYİ VE TİCARET A.Ş.",
    "SUWEN": "SUWEN TEKSTİL SANAYİ PAZARLAMA A.Ş.",
    "TEZOL": "EUROPAP TEZOL KAĞIT SANAYİ VE TİCARET A.Ş.",
    "PLTUR": "PLATFORM TURİZM TAŞIMACILIK GIDA İNŞAAT TEMİZLİK HİZMETLERİ SANAYİ VE TİCARET A.Ş.",
    "CGCAM": "Cagdas Cam Sanayi ve Ticaret AS",
    "BIGEN": "Birlesim Grup Enerji Yatirimlari AS",
    "GMTAS": "GİMAT MAĞAZACILIK SANAYİ VE TİCARET A.Ş.",
    "KARTN": "KARTONSAN KARTON SANAYİ VE TİCARET A.Ş.",
    "INDES": "İNDEKS BİLGİSAYAR SİSTEMLERİ MÜHENDİSLİK SANAYİ VE TİCARET A.Ş.",
    "PENTA": "PENTA TEKNOLOJİ ÜRÜNLERİ DAĞITIM TİCARET A.Ş.",
    "KONKA": "KONYA KAĞIT SANAYİ VE TİCARET A.Ş.",
    "DARDL": "DARDANEL ÖNENTAŞ GIDA SANAYİ A.Ş.",
    "HDFGS": "HEDEF GİRİŞİM SERMAYESİ YATIRIM ORTAKLIĞI A.Ş.",
    "INTEM": "İNTEMA İNŞAAT VE TESİSAT MALZEMELERİ YATIRIM VE PAZARLAMA A.Ş.",
    "GOLTS": "GÖLTAŞ GÖLLER BÖLGESİ ÇİMENTO SANAYİ VE TİCARET A.Ş.",
    "ERCB": "ERCİYAS ÇELİK BORU SANAYİ A.Ş.",
    "CATES": "Cates Elektrik Uretim Anonim Sirketi",
    "ULUUN": "ULUSOY UN SANAYİ VE TİCARET A.Ş.",
    "BORSK": "Bor Seker Anonim Sirketi",
    "ALKIM": "ALKİM ALKALİ KİMYA A.Ş.",
    "KRVGD": "KERVAN GIDA SANAYİ VE TİCARET A.Ş.",
    "CEMTS": "ÇEMTAŞ ÇELİK MAKİNA SANAYİ VE TİCARET A.Ş.",
    "HOROZ": "Horoz Lojistik Kargo Hizmetleri Ve Ticaret AS",
    "EGEGY": "Egeyapi Avrupa Gayrimenkul Yatirim Ortakligi A.S.",
    "ORGE": "ORGE ENERJİ ELEKTRİK TAAHHÜT A.Ş.",
    "TKNSA": "TEKNOSA İÇ VE DIŞ TİCARET A.Ş.",
    "KZGYO": "Kuzugrup Gayrimenkul Yatirim Ortakligi AS",
    "YATAS": "YATAŞ YATAK VE YORGAN SANAYİ TİCARET A.Ş.",
    "SAFKR": "SAFKAR EGE SOĞUTMACILIK KLİMA SOĞUK HAVA TESİSLERİ İHRACAT İTHALAT SANAYİ VE TİCARET A.Ş.",
    "BARMA": "BAREM AMBALAJ SANAYİ VE TİCARET A.Ş.",
    "ARSAN": "ARSAN TEKSTİL TİCARET VE SANAYİ A.Ş.",
    "AFYON": "AFYON ÇİMENTO SANAYİ T.A.Ş.",
    "IMASM": "İMAŞ MAKİNA SANAYİ A.Ş.",
    "ALCTL": "ALCATEL LUCENT TELETAŞ TELEKOMÜNİKASYON A.Ş.",
    "AZTEK": "AZTEK TEKNOLOJİ ÜRÜNLERİ TİCARET A.Ş.",
    "FMIZP": "FEDERAL-MOGUL İZMİT PİSTON VE PİM ÜRETİM TESİSLERİ A.Ş.",
    "DMRGD": "DMR Unlu Mamuller Uretim Gida Toptan Perakende Ihracat A.S.",
    "ONRYT": "Onur Yuksek Teknoloji AS",
    "ONCSM": "ONCOSEM ONKOLOJİK SİSTEMLER SANAYİ VE TİCARET A.Ş.",
    "FORTE": "FORTE BILGI ILETISIM TEKNOLOJILERI VE SAVUNMA SANAYI A.S.",
    "BVSAN": "BÜLBÜLOĞLU VİNÇ SANAYİ VE TİCARET A.Ş.",
    "YYAPI": "YEŞİL YAPI ENDÜSTRİSİ A.Ş.",
    "BRKVY": "BİRİKİM VARLIK YÖNETİM A.Ş.",
    "ORMA": "ORMA ORMAN MAHSULLERİ İNTEGRE SANAYİ VE TİCARET A.Ş.",
    "MHRGY": "MHR Gayrimenkul Yatirim Ortakligi Anonim Sirketi",
    "ARDYZ": "ARD GRUP BİLİŞİM TEKNOLOJİLERİ A.Ş.",
    "IHLAS": "İHLAS HOLDİNG A.Ş.",
    "NETAS": "NETAŞ TELEKOMÜNİKASYON A.Ş.",
    "BEGYO": "Bati Ege Gayrimenkul Yatirim Ortakligi A.S.",
    "TEKTU": "TEK-ART İNŞAAT TİCARET TURİZM SANAYİ VE YATIRIMLAR A.Ş.",
    "INFO": "İNFO YATIRIM MENKUL DEĞERLER A.Ş.",
    "LRSHO": "Loras Holding Anonim Sirketi",
    "ELITE": "ELİTE NATUREL ORGANİK GIDA SANAYİ VE TİCARET A.Ş.",
    "ALVES": "Alves Kablo Sanayi ve Ticaret A. S.",
    "CRDFA": "CREDITWEST FAKTORİNG A.Ş.",
    "BAGFS": "BAGFAŞ BANDIRMA GÜBRE FABRİKALARI A.Ş.",
    "SEGYO": "ŞEKER GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "GSDHO": "GSD HOLDİNG A.Ş.",
    "DUNYH": "Dunya Holding Anonim Sirketi",
    "SOKE": "SÖKE DEĞİRMENCİLİK SANAYİ VE TİCARET A.Ş.",
    "MERCN": "MERCAN KİMYA SANAYİ VE TİCARET A.Ş.",
    "KUTPO": "KÜTAHYA PORSELEN SANAYİ A.Ş.",
    "USAK": "UŞAK SERAMİK SANAYİ A.Ş.",
    "GOODY": "GOODYEAR LASTİKLERİ T.A.Ş.",
    "CEMAS": "ÇEMAŞ DÖKÜM SANAYİ A.Ş.",
    "DYOBY": "DYO BOYA FABRİKALARI SANAYİ VE TİCARET A.Ş.",
    "FORMT": "FORMET METAL VE CAM SANAYİ A.Ş.",
    "DCTTR": "DCT Trading Dis Ticaret Anonim Sirketi",
    "SERNT": "Seranit Granit Seramik Sanayi ve Ticaret A.S.",
    "ANELE": "ANEL ELEKTRİK PROJE TAAHHÜT VE TİCARET A.Ş.",
    "KUVVA": "KUVVA GIDA TİCARET VE SANAYİ YATIRIMLARI A.Ş.",
    "MACKO": "MACKOLİK İNTERNET HİZMETLERİ TİCARET A.Ş.",
    "SAYAS": "SAY YENİLENEBİLİR ENERJİ EKİPMANLARI SANAYİ VE TİCARET A.Ş.",
    "CMBTN": "ÇİMBETON HAZIRBETON VE PREFABRİK YAPI ELEMANLARI SANAYİ VE TİCARET A.Ş.",
    "RUZYE": "Ruzy Madencilik Ve Enerji Yatirimlari Sanayi Ve Ticaret A.S.",
    "OSMEN": "OSMANLI YATIRIM MENKUL DEĞERLER A.Ş.",
    "MNDRS": "MENDERES TEKSTİL SANAYİ VE TİCARET A.Ş.",
    "PINSU": "PINAR SU VE İÇECEK SANAYİ VE TİCARET A.Ş.",
    "YUNSA": "YÜNSA YÜNLÜ SANAYİ VE TİCARET A.Ş.",
    "ERBOS": "ERBOSAN ERCİYAS BORU SANAYİİ VE TİCARET A.Ş.",
    "YAPRK": "YAPRAK SÜT VE BESİ ÇİFTLİKLERİ SANAYİ VE TİCARET A.Ş.",
    "PETUN": "PINAR ENTEGRE ET VE UN SANAYİİ A.Ş.",
    "HUNER": "HUN YENİLENEBİLİR ENERJİ ÜRETİM A.Ş.",
    "MEKAG": "Meka Global Makine Imalat Sanayi Ve Ticaret A.S.",
    "EGEPO": "NASMED ÖZEL SAĞLIK HİZMETLERİ TİCARET A.Ş.",
    "PNSUT": "PINAR SÜT MAMULLERİ SANAYİİ A.Ş.",
    "SEGMN": "Segmen Kardesler Gida Uretim ve Ambalaj Sanayi AS",
    "EKSUN": "EKSUN GIDA TARIM SANAYİ VE TİCARET A.Ş.",
    "KIMMR": "ERSAN ALIŞVERİŞ HİZMETLERİ VE GIDA SANAYİ TİCARET A.Ş.",
    "TURGG": "TÜRKER PROJE GAYRİMENKUL VE YATIRIM GELİŞTİRME A.Ş.",
    "GUNDG": "Gundogdu Gida Sut Urunleri Sanayi Ve Dis Ticaret AS",
    "OZYSR": "Ozyasar Tel ve Galvanizleme Sanayi Anonim Sirketi",
    "KNFRT": "KONFRUT GIDA SANAYİ VE TİCARET A.Ş.",
    "HURGZ": "HÜRRİYET GAZETECİLİK VE MATBAACILIK A.Ş.",
    "LKMNH": "LOKMAN HEKİM ENGÜRÜSAĞ SAĞLIK TURİZM EĞİTİM HİZMETLERİ VE İNŞAAT TAAHHÜT A.Ş.",
    "PAPIL": "PAPİLON SAVUNMA TEKNOLOJİ VE TİCARET A.Ş.",
    "TATGD": "TAT GIDA SANAYİ A.Ş.",
    "MEDTR": "MEDİTERA TIBBİ MALZEME SANAYİ VE TİCARET A.Ş.",
    "SANKO": "SANKO PAZARLAMA İTHALAT İHRACAT A.Ş.",
    "TRILC": "TURK İLAÇ VE SERUM SANAYİ A.Ş.",
    "LUKSK": "LÜKS KADİFE TİCARET VE SANAYİİ A.Ş.",
    "OTTO": "OTTO HOLDİNG A.Ş.",
    "ISSEN": "İŞBİR SENTETİK DOKUMA SANAYİ A.Ş.",
    "TMPOL": "TEMAPOL POLİMER PLASTİK VE İNŞAAT SANAYİ TİCARET A.Ş.",
    "KTSKR": "KÜTAHYA ŞEKER FABRİKASI A.Ş.",
    "DOFER": "Dofer Yapi Maizemeleri Sanayi ve Ticaret A.S.",
    "BRLSM": "BİRLEŞİM MÜHENDİSLİK ISITMA SOĞUTMA HAVALANDIRMA SANAYİ VE TİCARET A.Ş.",
    "BEYAZ": "BEYAZ FİLO OTO KİRALAMA A.Ş.",
    "ARTMS": "Artemis Hali A. S.",
    "DERHL": "DERLÜKS YATIRIM HOLDİNG A.Ş.",
    "DAGI": "DAGİ GİYİM SANAYİ VE TİCARET A.Ş.",
    "BURCE": "BURÇELİK BURSA ÇELİK DÖKÜM SANAYİİ A.Ş.",
    "PNLSN": "PANELSAN ÇATI CEPHE SİSTEMLERİ SANAYİ VE TİCARET A.Ş.",
    "MARBL": "Tureks Turunc Madencilik Ic ve Dis Ticaret A.S.",
    "METRO": "METRO TİCARİ VE MALİ YATIRIMLAR HOLDİNG A.Ş.",
    "ARENA": "ARENA BİLGİSAYAR SANAYİ VE TİCARET A.Ş.",
    "MAKTK": "MAKİNA TAKIM ENDÜSTRİSİ A.Ş.",
    "TGSAS": "TGS DIŞ TİCARET A.Ş.",
    "KLMSN": "KLİMASAN KLİMA SANAYİ VE TİCARET A.Ş.",
    "PAMEL": "PAMEL YENİLENEBİLİR ELEKTRİK ÜRETİM A.Ş.",
    "BAHKM": "Bahadir Kimya Sanayi Ve Ticaret Anonim Sirketi",
    "SNICA": "SANİCA ISI SANAYİ A.Ş.",
    "KRONT": "KRON TELEKOMÜNİKASYON HİZMETLERİ A.Ş.",
    "FONET": "FONET BİLGİ TEKNOLOJİLERİ A.Ş.",
    "BAKAB": "BAK AMBALAJ SANAYİ VE TİCARET A.Ş.",
    "IHLGM": "İHLAS GAYRİMENKUL PROJE GELİŞTİRME VE TİCARET A.Ş.",
    "GLRYH": "GÜLER YATIRIM HOLDİNG A.Ş.",
    "INTEK": "Innosa Teknoloji Anonim Sirketi",
    "MTRKS": "MATRİKS BİLGİ DAĞITIM HİZMETLERİ A.Ş.",
    "VRGYO": "Vera Konsept Gayrimenkul Yatirim Ortakligi A.S.",
    "DZGYO": "DENİZ GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "PCILT": "PC İLETİŞİM VE MEDYA HİZMETLERİ SANAYİ TİCARET A.Ş.",
    "UNLU": "ÜNLÜ YATIRIM HOLDİNG A.Ş.",
    "SANFM": "SANİFOAM ENDÜSTRİ VE TÜKETİM ÜRÜNLERİ SANAYİ TİCARET A.Ş.",
    "CELHA": "ÇELİK HALAT VE TEL SANAYİİ A.Ş.",
    "ANGEN": "ANATOLİA TANI VE BİYOTEKNOLOJİ ÜRÜNLERİ ARAŞTIRMA GELİŞTİRME SANAYİ VE TİCARET A.Ş.",
    "PRKME": "PARK ELEKTRİK ÜRETİM MADENCİLİK SANAYİ VE TİCARET A.Ş.",
    "CONSE": "CONSUS ENERJİ İŞLETMECİLİĞİ VE HİZMETLERİ A.Ş.",
    "SKTAS": "SÖKTAŞ TEKSTİL SANAYİ VE TİCARET A.Ş.",
    "ISBIR": "İŞBİR HOLDİNG A.Ş.",
    "DNISI": "DİNAMİK ISI MAKİNA YALITIM MALZEMELERİ SANAYİ VE TİCARET A.Ş.",
    "KLSYN": "KOLEKSİYON MOBİLYA SANAYİ A.Ş.",
    "EGSER": "EGE SERAMİK SANAYİ VE TİCARET A.Ş.",
    "DGATE": "DATAGATE BİLGİSAYAR MALZEMELERİ TİCARET A.Ş.",
    "BLCYT": "BİLİCİ YATIRIM SANAYİ VE TİCARET A.Ş.",
    "ESCOM": "ESCORT TEKNOLOJİ YATIRIM A.Ş.",
    "LIDFA": "LİDER FAKTORİNG A.Ş.",
    "DITAS": "DİTAŞ DOĞAN YEDEK PARÇA İMALAT VE TEKNİK A.Ş.",
    "OZSUB": "ÖZSU BALIK ÜRETİM A.Ş.",
    "EDATA": "E-DATA TEKNOLOJİ PAZARLAMA A.Ş.",
    "EDIP": "EDİP GAYRİMENKUL YATIRIM SANAYİ VE TİCARET A.Ş.",
    "BIZIM": "BİZİM TOPTAN SATIŞ MAĞAZALARI A.Ş.",
    "ULUFA": "ULUSAL FAKTORİNG A.Ş.",
    "BURVA": "BURÇELİK VANA SANAYİ VE TİCARET A.Ş.",
    "KRSTL": "KRİSTAL KOLA VE MEŞRUBAT SANAYİ TİCARET A.Ş.",
    "TLMAN": "TRABZON LİMAN İŞLETMECİLİĞİ A.Ş.",
    "VBTYZ": "VBT YAZILIM A.Ş.",
    "DGNMO": "DOĞANLAR MOBİLYA GRUBU İMALAT SANAYİ VE TİCARET A.Ş.",
    "SELVA": "SELVA GIDA SANAYİ A.Ş.",
    "DERIM": "DERİMOD KONFEKSİYON AYAKKABI DERİ SANAYİ VE TİCARET A.Ş.",
    "AYES": "AYES ÇELİK HASIR VE ÇİT SANAYİ A.Ş.",
    "EUHOL": "EURO YATIRIM HOLDİNG A.Ş.",
    "BAYRK": "BAYRAK EBT TABAN SANAYİ VE TİCARET A.Ş.",
    "MARTI": "MARTI OTEL İŞLETMELERİ A.Ş.",
    "BMSCH": "BMS ÇELİK HASIR SANAYİ VE TİCARET A.Ş.",
    "RTALB": "RTA LABORATUVARLARI BİYOLOJİK ÜRÜNLER İLAÇ VE MAKİNE SANAYİ TİCARET A.Ş.",
    "DENGE": "DENGE YATIRIM HOLDİNG A.Ş.",
    "DURKN": "Durukan Sekerleme Sanayi ve Ticaret AS",
    "SKYMD": "Seker Yatirim Menkul Degerler A.S.",
    "DOGUB": "DOĞUSAN BORU SANAYİİ VE TİCARET A.Ş.",
    "MAKIM": "MAKİM MAKİNA TEKNOLOJİLERİ SANAYİ VE TİCARET A.Ş.",
    "AVGYO": "AVRASYA GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "YESIL": "YEŞİL YATIRIM HOLDİNG A.Ş.",
    "DURDO": "DURAN DOĞAN BASIM VE AMBALAJ SANAYİ A.Ş.",
    "OSTIM": "OSTİM ENDÜSTRİYEL YATIRIMLAR VE İŞLETME A.Ş.",
    "KFEIN": "KAFEİN YAZILIM HİZMETLERİ TİCARET A.Ş.",
    "ATEKS": "AKIN TEKSTİL A.Ş.",
    "TDGYO": "TREND GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
    "SODSN": "SODAŞ SODYUM SANAYİİ A.Ş.",
    "DMSAS": "DEMİSAŞ DÖKÜM EMAYE MAMÜLLERİ SANAYİİ A.Ş.",
    "ARZUM": "ARZUM ELEKTRİKLİ EV ALETLERİ SANAYİ VE TİCARET A.Ş.",
    "BYDNR": "Baydoner Restoranlari A.S.",
    "CUSAN": "ÇUHADAROĞLU METAL SANAYİ VE PAZARLAMA A.Ş.",
    "OBASE": "OBASE BİLGİSAYAR VE DANIŞMANLIK HİZMETLERİ TİCARET A.Ş.",
    "PKART": "PLASTİKKART AKILLI KART İLETİŞİM SİSTEMLERİ SANAYİ VE TİCARET A.Ş.",
    "TUCLK": "TUĞÇELİK ALÜMİNYUM VE METAL MAMÜLLERİ SANAYİ VE TİCARET A.Ş.",
    "SKYLP": "Skyalp Finansal Teknolojiler ve Danismanlik A.S",
    "FRIGO": "FRİGO-PAK GIDA MADDELERİ SANAYİ VE TİCARET A.Ş.",
    "A1YEN": "A1 Yenilenebilir Enerji Uretim AS",
    "MERKO": "MERKO GIDA SANAYİ VE TİCARET A.Ş.",
    "RUBNS": "RUBENİS TEKSTİL SANAYİ TİCARET A.Ş.",
    "AVHOL": "AVRUPA YATIRIM HOLDİNG A.Ş.",
    "SNKRN": "SENKRON SİBER GÜVENLİK YAZILIM VE BİLİŞİM ÇÖZÜMLERİ A.Ş.",
    "BNTAS": "BANTAŞ BANDIRMA AMBALAJ SANAYİ TİCARET A.Ş.",
    "GLBMD": "GLOBAL MENKUL DEĞERLER A.Ş.",
    "ZEDUR": "ZEDUR ENERJİ ELEKTRİK ÜRETİM A.Ş.",
    "GSDDE": "GSD DENİZCİLİK GAYRİMENKUL İNŞAAT SANAYİ VE TİCARET A.Ş.",
    "PENGD": "PENGUEN GIDA SANAYİ A.Ş.",
    "YKSLN": "YÜKSELEN ÇELİK A.Ş.",
    "YAYLA": "YAYLA ENERJİ ÜRETİM TURİZM VE İNŞAAT TİCARET A.Ş.",
    "KRPLS": "KOROPLAST TEMİZLİK AMBALAJ ÜRÜNLERİ SANAYİ VE DIŞ TİCARET A.Ş.",
    "IHGZT": "İHLAS GAZETECİLİK A.Ş.",
    "KERVN": "KERVANSARAY YATIRIM HOLDİNG A.Ş.",
    "VKING": "VİKİNG KAĞIT VE SELÜLOZ A.Ş.",
    "PRDGS": "PARDUS GİRİŞİM SERMAYESİ YATIRIM ORTAKLIĞI A.Ş.",
    "MMCAS": "MMC SANAYİ VE TİCARİ YATIRIMLAR A.Ş.",
    "DESPC": "DESPEC BİLGİSAYAR PAZARLAMA VE TİCARET A.Ş.",
    "NIBAS": "NİĞBAŞ NİĞDE BETON SANAYİ VE TİCARET A.Ş.",
    "GEDZA": "GEDİZ AMBALAJ SANAYİ VE TİCARET A.Ş.",
    "HKTM": "HİDROPAR HAREKET KONTROL TEKNOLOJİLERİ MERKEZİ SANAYİ VE TİCARET A.Ş.",
    "PSDTC": "PERGAMON STATUS DIŞ TİCARET A.Ş.",
    "AVOD": "A.V.O.D. KURUTULMUŞ GIDA VE TARIM ÜRÜNLERİ SANAYİ TİCARET A.Ş.",
    "FADE": "FADE GIDA YATIRIM SANAYİ TİCARET A.Ş.",
    "MEGAP": "MEGA POLİETİLEN KÖPÜK SANAYİ VE TİCARET A.Ş.",
    "SEYKM": "SEYİTLER KİMYA SANAYİ A.Ş.",
    "IZINV": "İZ YATIRIM HOLDİNG A.Ş.",
    "MEPET": "MEPET METRO PETROL VE TESİSLERİ SANAYİ TİCARET A.Ş.",
    "ACSEL": "ACISELSAN ACIPAYAM SELÜLOZ SANAYİ VE TİCARET A.Ş.",
    "CEOEM": "CEO EVENT MEDYA A.Ş.",
    "RNPOL": "RAİNBOW POLİKARBONAT SANAYİ TİCARET A.Ş.",
    "MANAS": "MANAS ENERJİ YÖNETİMİ SANAYİ VE TİCARET A.Ş.",
    "COSMO": "COSMOS YATIRIM HOLDİNG A.Ş.",
    "EPLAS": "EGEPLAST EGE PLASTİK TİCARET VE SANAYİ A.Ş.",
    "AKSUE": "AKSU ENERJİ VE TİCARET A.Ş.",
    "ICUGS": "ICU Girisim Sermayesi Yatirim Ortakligi A.S.",
    "IHYAY": "İHLAS YAYIN HOLDİNG A.Ş.",
    "ETILR": "ETİLER GIDA VE TİCARİ YATIRIMLAR SANAYİ VE TİCARET A.Ş.",
    "YONGA": "YONGA MOBİLYA SANAYİ VE TİCARET A.Ş.",
    "BRKO": "BİRKO BİRLEŞİK KOYUNLULULAR MENSUCAT TİCARET VE SANAYİ A.Ş.",
    "SILVR": "SİLVERLİNE ENDÜSTRİ VE TİCARET A.Ş.",
    "ORCAY": "ORÇAY ORTAKÖY ÇAY SANAYİ VE TİCARET A.Ş.",
    "HUBVC": "HUB GİRİŞİM SERMAYESİ YATIRIM ORTAKLIĞI A.Ş.",
    "VANGD": "VANET GIDA SANAYİ İÇ VE DIŞ TİCARET A.Ş.",
    "KRTEK": "KARSU TEKSTİL SANAYİİ VE TİCARET A.Ş.",
    "BRMEN": "BİRLİK MENSUCAT TİCARET VE SANAYİ İŞLETMESİ A.Ş.",
    "PRZMA": "PRİZMA PRES MATBAACILIK YAYINCILIK SANAYİ VE TİCARET A.Ş.",
    "HATEK": "HATEKS HATAY TEKSTİL İŞLETMELERİ A.Ş.",
    "BALAT": "BALATACILAR BALATACILIK SANAYİ VE TİCARET A.Ş.",
    "MARKA": "MARKA YATIRIM HOLDİNG A.Ş.",
    "OYAYO": "OYAK YATIRIM ORTAKLIĞI A.Ş.",
    "FLAP": "FLAP KONGRE TOPLANTI HİZMETLERİ OTOMOTİV VE TURİZM A.Ş.",
    "IHEVA": "İHLAS EV ALETLERİ İMALAT SANAYİ VE TİCARET A.Ş.",
    "OYLUM": "OYLUM SINAİ YATIRIMLAR A.Ş.",
    "SEKFK": "ŞEKER FİNANSAL KİRALAMA A.Ş.",
    "SMART": "SMARTİKS YAZILIM A.Ş.",
    "OZRDN": "ÖZERDEN PLASTİK SANAYİ VE TİCARET A.Ş.",
    "ULAS": "ULAŞLAR TURİZM YATIRIMLARI VE DAYANIKLI TÜKETİM MALLARI TİCARET PAZARLAMA A.Ş.",
    "AKYHO": "AKDENİZ YATIRIM HOLDİNG A.Ş.",
    "EKIZ": "EKİZ KİMYA SANAYİ VE TİCARET A.Ş.",
    "BRKSN": "BERKOSAN YALITIM VE TECRİT MADDELERİ ÜRETİM VE TİCARET A.Ş.",
    "SEKUR": "SEKURO PLASTİK AMBALAJ SANAYİ A.Ş.",
    "SAMAT": "SARAY MATBAACILIK KAĞITÇILIK KIRTASİYECİLİK TİCARET VE SANAYİ A.Ş.",
    "ERSU": "ERSU MEYVE VE GIDA SANAYİ A.Ş.",
    "MZHLD": "MAZHAR ZORLU HOLDİNG A.Ş.",
    "VKFYO": "VAKIF MENKUL KIYMET YATIRIM ORTAKLIĞI A.Ş.",
    "RODRG": "RODRİGO TEKSTİL SANAYİ VE TİCARET A.Ş.",
    "ATSYH": "ATLANTİS YATIRIM HOLDİNG A.Ş.",
    "GRNYO": "GARANTİ YATIRIM ORTAKLIĞI A.Ş.",
    "SANEL": "SAN-EL MÜHENDİSLİK ELEKTRİK TAAHHÜT SANAYİ VE TİCARET A.Ş.",
    "ETYAT": "EURO TREND YATIRIM ORTAKLIĞI A.Ş.",
    "CASA": "CASA EMTİA PETROL KİMYEVİ VE TÜREVLERİ SANAYİ TİCARET A.Ş.",
    "ATLAS": "ATLAS MENKUL KIYMETLER YATIRIM ORTAKLIĞI A.Ş.",
    "MTRYO": "METRO YATIRIM ORTAKLIĞI A.Ş.",
    "EUKYO": "EURO KAPİTAL YATIRIM ORTAKLIĞI A.Ş.",
    "EUYO": "EURO MENKUL KIYMET YATIRIM ORTAKLIĞI A.Ş.",
    "DIRIT": "DİRİTEKS DİRİLİŞ TEKSTİL SANAYİ VE TİCARET A.Ş.",
    "ALTIN": "DARPHANE ALTIN SERTİFİKASI",
    "MARMR": "Marmara Holding AS"
}

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}.IS"
# YENİ HABER KAYNAĞI
MIDAS_NEWS_URL = "https://www.getmidas.com/midas-kulaklari/haberleri/"
MIDAS_CONTAINER_CLASS = "daily-newsletters-block-body-item"


# --- TRADINGVIEW TARAMA AYARLARI (1/4: BIST Dip) ---
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

# --- TRADINGVIEW TARAMA AYARLARI (2/4: NASDAQ Dip - Gelişmiş Filtre) ---
TRADINGVIEW_PAYLOAD_NASDAQ_DIP = {
    "columns": [
        "name", "close", "description", "logoid", "update_mode", "type", "typespecs", 
        "TechRating_1D", "TechRating_1D.tr", "MARating_1D", "MARating_1D.tr", 
        "OsRating_1D", "OsRating_1D.tr", "RSI", "Mom", "pricescale", "minmov", 
        "fractional", "minmove2", "AO", "CCI20", "Stoch.K", "Stoch.D", 
        "Candle.3BlackCrows", "Candle.3WhiteSoldiers", "Candle.AbandonedBaby.Bearish", 
        "Candle.AbandonedBaby.Bullish", "Candle.Doji", "Candle.Doji.Dragonfly", 
        "Candle.Doji.Gravestone", "Candle.Engulfing.Bearish", "Candle.Engulfing.Bullish", 
        "Candle.EveningStar", "Candle.Hammer", "Candle.HangingMan", 
        "Candle.Harami.Bearish", "Candle.Harami.Bullish", "Candle.InvertedHammer", 
        "Candle.Kicking.Bearish", "Candle.Kicking.Bullish", "Candle.LongShadow.Lower", 
        "Candle.LongShadow.Upper", "Candle.Marubozu.Black", "Candle.Marubozu.White", 
        "Candle.MorningStar", "Candle.ShootingStar", "Candle.SpinningTop.Black", 
        "Candle.SpinningTop.White", "Candle.TriStar.Bearish", "Candle.TriStar.Bullish", 
        "exchange"
    ],
    "filter": [
        {"left": "RSI", "operation": "less", "right": 35},
        {"left": "Stoch.RSI.K", "operation": "less", "right": 20},
        {"left": "Stoch.RSI.K", "operation": "greater", "right": "Stoch.RSI.D"},
        {"left": "SMA50", "operation": "greater", "right": "close"},
        {"left": "close", "operation": "greater", "right": 10},
        {"left": "average_volume_30d_calc", "operation": "greater", "right": 1000000},
        {"left": "OsRating_1D", "operation": "in_range", "right": ["Buy", "StrongBuy", "Neutral"]}
    ],
    "filter2": {
        "operator": "and",
        "operands": [
            {
                "operation": {
                    "operator": "or",
                    "operands": [
                        { "operation": { "operator": "and", "operands": [{"expression": {"left": "type", "operation": "equal", "right": "stock"}}, {"expression": {"left": "typespecs", "operation": "has", "right": ["common"]}}]}},
                        { "operation": { "operator": "and", "operands": [{"expression": {"left": "type", "operation": "equal", "right": "stock"}}, {"expression": {"left": "typespecs", "operation": "has", "right": ["preferred"]}}]}},
                        { "operation": { "operator": "and", "operands": [{"expression": {"left": "type", "operation": "equal", "right": "dr"}}]}},
                        { "operation": { "operator": "and", "operands": [{"expression": {"left": "type", "operation": "equal", "right": "fund"}}, {"expression": {"left": "typespecs", "operation": "has_none_of", "right": ["etf"]}}]}}
                    ]
                }
            },
            {"expression": {"left": "typespecs", "operation": "has_none_of", "right": ["pre-ipo"]}}
        ]
    },
    "ignore_unknown_fields": False, 
    "markets": ["america"],
    "options": {"lang": "en"},
    "range": [0, 5000],
    "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
    "symbols": {}
}

# --- TRADINGVIEW TARAMA AYARLARI (3/4: BIST Düşen Trend Kırılımı) ---
TRADINGVIEW_PAYLOAD_BIST_TREND = {
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
        {"left": "EMA12|1M", "operation": "greater", "right": "EMA26|1M"},
        {"left": "MACD.macd|1M", "operation": "greater", "right": 0},
        {"left": "MACD.signal|1M", "operation": "greater", "right": "MACD.macd|1M"},
        {"left": "RSI|1M", "operation": "greater", "right": 60},
        {"left": "EMA20|1M", "operation": "greater", "right": "EMA50|1M"},
        {"left": "AnalystRating", "operation": "in_range", "right": ["Buy", "StrongBuy"]}
    ],
    "filter2": {
        "operator": "and",
        "operands": [
            {
                "operation": {
                    "operator": "or",
                    "operands": [
                        {"operation": {"operator": "and", "operands": [
                            {"expression": {"left": "type", "operation": "equal", "right": "stock"}},
                            {"expression": {"left": "typespecs", "operation": "has", "right": ["common"]}}
                        ]}},
                        {"operation": {"operator": "and", "operands": [
                            {"expression": {"left": "type", "operation": "equal", "right": "stock"}},
                            {"expression": {"left": "typespecs", "operation": "has", "right": ["preferred"]}}
                        ]}},
                        {"operation": {"operator": "and", "operands": [
                            {"expression": {"left": "type", "operation": "equal", "right": "dr"}}
                        ]}},
                        {"operation": {"operator": "and", "operands": [
                            {"expression": {"left": "type", "operation": "equal", "right": "fund"}},
                            {"expression": {"left": "typespecs", "operation": "has_none_of", "right": ["etf"]}}
                        ]}}
                    ]
                }
            },
            {"expression": {"left": "typespecs", "operation": "has_none_of", "right": ["pre-ipo"]}}
        ]
    },
    "ignore_unknown_fields": False,
    "markets": ["turkey"],
    "options": {"lang": "en"},
    "range": [0, 5000],
    "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
    "symbols": {}
}

# --- TRADINGVIEW TARAMA AYARLARI (4/4: BIST Potansiyelli Kağıtlar) ---
TRADINGVIEW_PAYLOAD_BIST_POTANSIYEL = {
    "columns": [
        "name", "description", "logoid", "update_mode", "type", "typespecs", "close",
        "pricescale", "minmov", "fractional", "minmove2", "currency", "change",
        "volume", "relative_volume_10d_calc", "market_cap_basic", "fundamental_currency_code",
        "price_earnings_ttm", "earnings_per_share_diluted_ttm", "earnings_per_share_diluted_yoy_growth_ttm",
        "dividends_yield_current", "sector.tr", "market", "sector", "AnalystRating",
        "AnalystRating.tr", "exchange"
    ],
    "filter": [
        {"left": "EMA20", "operation": "greater", "right": "EMA50"},
        {"left": "EMA50", "operation": "less", "right": "close"},
        {"left": "EMA200", "operation": "less", "right": "close"},
        {"left": "RSI", "operation": "greater", "right": 60},
        {"left": "MACD.macd", "operation": "greater", "right": 1},
        {"left": "TechRating_1M", "operation": "in_range", "right": ["StrongBuy"]},
        {"left": "AnalystRating", "operation": "in_range", "right": ["Buy", "StrongBuy"]}
    ],
    "filter2": {
        "operator": "and",
        "operands": [
            {
                "operation": {
                    "operator": "or",
                    "operands": [
                        {"operation": {"operator": "and", "operands": [
                            {"expression": {"left": "type", "operation": "equal", "right": "stock"}},
                            {"expression": {"left": "typespecs", "operation": "has", "right": ["common"]}}
                        ]}},
                        {"operation": {"operator": "and", "operands": [
                            {"expression": {"left": "type", "operation": "equal", "right": "stock"}},
                            {"expression": {"left": "typespecs", "operation": "has", "right": ["preferred"]}}
                        ]}},
                        {"operation": {"operator": "and", "operands": [
                            {"expression": {"left": "type", "operation": "equal", "right": "dr"}}
                        ]}},
                        {"operation": {"operator": "and", "operands": [
                            {"expression": {"left": "type", "operation": "equal", "right": "fund"}},
                            {"expression": {"left": "typespecs", "operation": "has_none_of", "right": ["etf"]}}
                        ]}}
                    ]
                }
            },
            {"expression": {"left": "typespecs", "operation": "has_none_of", "right": ["pre-ipo"]}}
        ]
    },
    "ignore_unknown_fields": False,
    "markets": ["turkey"],
    "options": {"lang": "en"},
    "range": [0, 5000], 
    "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
    "symbols": {}
}

TRADINGVIEW_PAYLOAD_NASDAQ_POTANSIYEL = {
    "columns": [
        "name", "description", "logoid", "update_mode", "type", "typespecs", "close", "pricescale", 
        "minmov", "fractional", "minmove2", "currency", "change", "volume", "relative_volume_10d_calc", 
        "market_cap_basic", "fundamental_currency_code", "price_earnings_ttm", "earnings_per_share_diluted_ttm", 
        "earnings_per_share_diluted_yoy_growth_ttm", "dividends_yield_current", "sector.tr", "market", 
        "sector", "AnalystRating", "AnalystRating.tr", "exchange", 
        "RSI|1M", "Perf.Y", "debt_to_asset_fy", "average_volume_90d_calc", "OsRating_1M", "MARating_1M", "TechRating_1M"
    ],
    "filter": [
        {"left": "market_cap_basic", "operation": "in_range", "right": [1000000000, 100000000000]},
        {"left": "close", "operation": "greater", "right": 9},
        {"left": "RSI|1M", "operation": "egreater", "right": 60},
        {"left": "Perf.Y", "operation": "greater", "right": 20},
        {"left": "earnings_per_share_diluted_yoy_growth_ttm", "operation": "greater", "right": 10},
        {"left": "debt_to_asset_fy", "operation": "less", "right": 1},
        {"left": "average_volume_90d_calc", "operation": "greater", "right": 500000},
        {"left": "OsRating_1M", "operation": "in_range", "right": ["StrongBuy", "Buy"]},
        {"left": "AnalystRating", "operation": "in_range", "right": ["StrongBuy"]},
        {"left": "MARating_1M", "operation": "in_range", "right": ["StrongBuy"]},
        {"left": "TechRating_1M", "operation": "in_range", "right": ["StrongBuy"]}
    ],
    "filter2": {
        "operator": "and",
        "operands": [
            {
                "operation": {
                    "operator": "or",
                    "operands": [
                        {"operation": {"operator": "and", "operands": [{"expression": {"left": "type", "operation": "equal", "right": "stock"}}, {"expression": {"left": "typespecs", "operation": "has", "right": ["common"]}}]}},
                        {"operation": {"operator": "and", "operands": [{"expression": {"left": "type", "operation": "equal", "right": "stock"}}, {"expression": {"left": "typespecs", "operation": "has", "right": ["preferred"]}}]}},
                        {"operation": {"operator": "and", "operands": [{"expression": {"left": "type", "operation": "equal", "right": "dr"}}]}},
                        {"operation": {"operator": "and", "operands": [{"expression": {"left": "type", "operation": "equal", "right": "fund"}}, {"expression": {"left": "typespecs", "operation": "has_none_of", "right": ["etf"]}}]}}
                    ]
                }
            },
            {"expression": {"left": "typespecs", "operation": "has_none_of", "right": ["pre-ipo"]}}
        ]
    },
    "ignore_unknown_fields": False,
    "markets": ["america"], 
    "options": {"lang": "en"},
    "range": [0, 5000],
    "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
    "symbols": {}
}

# ------------------- Yardımcı Fonksiyonlar (Dosya Yönetimi & Utility) -------------------

def clear():
    """Konsolu temizler."""
    os.system("cls" if os.name == "nt" else "clear")

def log_user(user_id, username, first_name):
    """Kullanıcı bilgilerini users.txt dosyasına kaydeder (benzersiz kayıt)."""
    user_data = f"{user_id},{username if username else 'N/A'},{first_name if first_name else 'N/A'}\n"
    try:
        with open(USER_LOG_FILE, 'r') as f:
            existing_users = f.readlines()
    except FileNotFoundError:
        existing_users = []
        
    if not any(line.startswith(str(user_id) + ',') for line in existing_users):
        with open(USER_LOG_FILE, 'a') as f:
            f.write(user_data)
        print(f"Yeni kullanıcı kaydedildi: {user_id}")

def get_all_user_ids():
    """Kayıtlı tüm kullanıcı ID'lerini döndürür."""
    user_ids = []
    try:
        with open(USER_LOG_FILE, 'r') as f:
            for line in f:
                try:
                    user_id = int(line.split(',')[0])
                    user_ids.append(user_id)
                except ValueError:
                    continue
    except FileNotFoundError:
        pass
    return user_ids

def get_required_channels():
    """Zorunlu kanal ID'lerini channels.txt dosyasından okur."""
    channels = []
    try:
        with open(CHANNEL_LOG_FILE, 'r') as f:
            channels = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        pass
    return list(set(channels))

def add_channel_to_file(channel_id: str):
    """Yeni kanalı listeye ekler."""
    channels = get_required_channels()
    if channel_id not in channels:
        with open(CHANNEL_LOG_FILE, 'a') as f:
            f.write(f"\n{channel_id.strip()}")
        return True
    return False

def remove_channel_from_file(channel_id: str):
    """Kanalları listeden siler."""
    channels = get_required_channels()
    if channel_id in channels:
        channels.remove(channel_id)
        with open(CHANNEL_LOG_FILE, 'w') as f:
            f.write('\n'.join(channels))
        return True
    return False

# --- YENİ EKLENEN FİLİGRAN FONKSİYONU ---
def add_watermark(fig, text="@Finansalgucbot"):
    """
    Matplotlib figürüne silik bir filigran (watermark) ekler.
    Sağ üst çapraz konumlandırma kullanır.
    """
    # Filigranı figürün içine yerleştirmek için fig.text kullanılır
    # 0.95: X ekseninde sağa yakın (sağ üst)
    # 0.95: Y ekseninde yukarı yakın (sağ üst)
    # rotation=15: Hafif çapraz eğim
    # fontsize=30: Büyük font boyutu
    # color='gray': Gri renk
    # alpha=0.3: Silik görünmesi için şeffaflık
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

# ------------------- Finansal Veri Çekme Fonksiyonları (Yahooquery) -------------------

def get_val(data, key):
    """Yahoo JSON içinden veriyi güvenli çeker."""
    if not data or not isinstance(data, dict): return None
    v = data.get(key)
    return v.get("raw") if isinstance(v, dict) else v

def fetch_chart_data(symbol: str):
    """2 yıllık veriyi Heikin-Ashi için OHLC formatında çeker."""
    params = {"range": "2y", "interval": "1d"} 
    try:
        pure_symbol = symbol.split('.')[0].upper()
        url = YAHOO_CHART_URL.format(pure_symbol)
        resp = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200: return None
        
        data = resp.json()["chart"]["result"][0]
        quotes = data["indicators"]["quote"][0]
        df = pd.DataFrame({
            'time': [datetime.fromtimestamp(t) for t in data["timestamp"]],
            'open': quotes.get('open'), 'high': quotes.get('high'),
            'low': quotes.get('low'), 'close': quotes.get('close')
        }).dropna()
        return df if not df.empty else None
    except: return None

def fetch_fundamentals(symbol: str):
    """Cari Oran ve Borç verilerini Yahoo API'den garantili çeker."""
    try:
        ticker = f"{symbol.split('.')[0].upper()}.IS"
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,summaryDetail,defaultKeyStatistics"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).json()
        data = res.get("quoteSummary", {}).get("result", [{}])[0]
        
        f_d = data.get("financialData", {})
        s_d = data.get("summaryDetail", {})
        k_s = data.get("defaultKeyStatistics", {})

        return {
            "Fiyat (TRY)": get_val(f_d, "currentPrice"),
            "Ort. Hacim (10 gün)": get_val(s_d, "averageDailyVolume10Day"),
            "Piyasa Değeri": get_val(s_d, "marketCap"),
            "Geriye Dönük F/K": get_val(s_d, "trailingPE"),
            "İleriye Dönük F/K": get_val(s_d, "forwardPE"),
            "Fiyat/Satış (P/S)": get_val(s_d, "priceToSalesTrailing12Months"),
            "Brüt Kar Marjı (%)": get_val(f_d, "grossMargins") * 100 if get_val(f_d, "grossMargins") else None,
            "Faaliyet Kar Marjı (%)": get_val(f_d, "operatingMargins") * 100 if get_val(f_d, "operatingMargins") else None,
            "Net Kar Marjı (%)": get_val(f_d, "profitMargins") * 100 if get_val(f_d, "profitMargins") else None,
            "Özkaynak Karlılığı (ROE) (%)": get_val(f_d, "returnOnEquity") * 100 if get_val(f_d, "returnOnEquity") else None,
            "Varlık Karlılığı (ROA) (%)": get_val(f_d, "returnOnAssets") * 100 if get_val(f_d, "returnOnAssets") else None,
            "Cari Oran": get_val(f_d, "currentRatio"),
            "Borç/Özkaynak": get_val(f_d, "debtToEquity") if get_val(f_d, "debtToEquity") else get_val(k_s, "debtToEquity")
        }
    except: return None

def fetch_fundamentals(symbol: str):
    """Cari Oran ve Borç verilerini Yahoo API'den garantili çeker."""
    try:
        ticker = f"{symbol.split('.')[0].upper()}.IS"
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,summaryDetail,defaultKeyStatistics"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).json()
        data = res.get("quoteSummary", {}).get("result", [{}])[0]
        
        f_d = data.get("financialData", {})
        s_d = data.get("summaryDetail", {})
        k_s = data.get("defaultKeyStatistics", {})

        return {
            "Fiyat (TRY)": get_val(f_d, "currentPrice"),
            "Ort. Hacim (10 gün)": get_val(s_d, "averageDailyVolume10Day"),
            "Piyasa Değeri": get_val(s_d, "marketCap"),
            "Geriye Dönük F/K": get_val(s_d, "trailingPE"),
            "İleriye Dönük F/K": get_val(s_d, "forwardPE"),
            "Fiyat/Satış (P/S)": get_val(s_d, "priceToSalesTrailing12Months"),
            "Brüt Kar Marjı (%)": get_val(f_d, "grossMargins") * 100 if get_val(f_d, "grossMargins") else None,
            "Faaliyet Kar Marjı (%)": get_val(f_d, "operatingMargins") * 100 if get_val(f_d, "operatingMargins") else None,
            "Net Kar Marjı (%)": get_val(f_d, "profitMargins") * 100 if get_val(f_d, "profitMargins") else None,
            "Özkaynak Karlılığı (ROE) (%)": get_val(f_d, "returnOnEquity") * 100 if get_val(f_d, "returnOnEquity") else None,
            "Varlık Karlılığı (ROA) (%)": get_val(f_d, "returnOnAssets") * 100 if get_val(f_d, "returnOnAssets") else None,
            "Cari Oran": get_val(f_d, "currentRatio"),
            "Borç/Özkaynak": get_val(f_d, "debtToEquity") if get_val(f_d, "debtToEquity") else get_val(k_s, "debtToEquity")
        }
    except: return None
def plot_advanced_chart(symbol, df):
    # Kritik kontrol: DataFrame boş mu veya None mı?
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    
    try:
        # --- HEIKIN-ASHI HESAPLAMA ---
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = np.zeros(len(df))
        ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
        for i in range(1, len(df)):
            ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
        
        ha_high = np.maximum.reduce([df['high'], ha_open, ha_close])
        ha_low = np.minimum.reduce([df['low'], ha_open, ha_close])
        
        # --- TASARIM ---
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(15, 8))
        fig.patch.set_facecolor('#131722')
        ax.set_facecolor('#131722')
        
        # Sağ tarafa fiyat etiketi için %15'lik bir boşluk bırakıyoruz
        plt.subplots_adjust(top=0.88, bottom=0.08, right=0.85, left=0.05)

        # Mumları Çiz
        for i in range(len(df)):
            color = '#089981' if ha_close.iloc[i] >= ha_open[i] else '#f23645'
            ax.vlines(df['time'].iloc[i], ha_low[i], ha_high[i], color=color, linewidth=0.8, alpha=0.6)
            ax.vlines(df['time'].iloc[i], ha_open[i], ha_close.iloc[i], color=color, linewidth=3, alpha=1)

        # Teknik Analiz (Trendler)
        closes_np = ha_close.values
        peaks, _ = find_peaks(closes_np, distance=35, prominence=0.05)
        troughs, _ = find_peaks(-closes_np, distance=35, prominence=0.05)
        
        x = np.arange(len(closes_np))
        if len(peaks) >= 2:
            p_idx = peaks[-2:].astype(int)
            ax.plot(df['time'], np.poly1d(np.polyfit(p_idx, closes_np[p_idx], 1))(x), color='white', ls='--', alpha=0.5)
        if len(troughs) >= 2:
            t_idx = troughs[-2:].astype(int)
            ax.plot(df['time'], np.poly1d(np.polyfit(t_idx, closes_np[t_idx], 1))(x), color='white', ls='--', alpha=0.5)

        # --- SAĞ TARAF FİYAT ETİKETİ (TRADINGVIEW STYLE) ---
        last_price = ha_close.iloc[-1]
        ax.annotate(f"{last_price:.2f}", 
                    xy=(1, last_price), 
                    xycoords=('axes fraction', 'data'),
                    xytext=(10, 0), 
                    textcoords='offset points',
                    bbox=dict(boxstyle="round,pad=0.5", fc="#2962ff", ec="none", alpha=0.9),
                    color="white", 
                    weight="bold", 
                    va="center", 
                    fontsize=11)

        # Güncel fiyat hizasında silik bir yatay çizgi
        ax.axhline(last_price, color='#2962ff', linestyle=':', linewidth=1, alpha=0.3)

        # Ayarlar
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.grid(True, color="#e1e4ec", alpha=0.2)
        
        # Limitleri ayarla (Etiketin taşmaması için biraz pay ekledik)
        y_min, y_max = min(ha_low), max(ha_high)
        y_range = y_max - y_min
        ax.set_ylim(y_min - (y_range * 0.05), y_max + (y_range * 0.10))

        ax.text(0.01, 1.10, f"{symbol} - 2Y HEIKIN-ASHI", transform=ax.transAxes, fontsize=18, fontweight='bold')
        
        add_watermark(fig)
        filename = f"chart_{symbol}_final.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight', facecolor='#131722')
        plt.close(fig)
        return filename
    except Exception as e:
        print(f"Çizim hatası: {e}")
        return None

# YENİDEN EKLEMEK İSTEDİĞİNİZ TEMEL VERİ PNG TABLOSU FONKSİYONU
def generate_fundamentals_image(symbol, fundamentals):
    if not fundamentals:
        return None

    # Veri hazırlığı (metin tablosu için)
    data = []
    
    sections = {
        "📊 Piyasa ve Değerleme Oranları": [
            "Fiyat (TRY)", "Piyasa Değeri", "Ort. Hacim (10 gün)",
            "Geriye Dönük F/K", "İleriye Dönük F/K", "Fiyat/Satış (P/S)", 
        ],
        "📈 Karlılık ve Marjlar": [
            "Özkaynak Karlılığı (ROE) (%)", "Varlık Karlılığı (ROA) (%)",
            "Brüt Kar Marjı (%)", "Faaliyet Kar Marjı (%)", "Net Kar Marjı (%)"
        ],
        "⚖️ Likidite ve Borçluluk": [
            "Cari Oran", "Borç/Özkaynak"
        ]
    }
    
    # Tüm veriyi tek bir listeye toplayalım (başlıkları ayırmak için)
    current_section = None
    for section_title, keys in sections.items():
        data.append((section_title, "---"))
        for k in keys:
            value = fundamentals.get(k)
            is_percentage = "%" in k
            formatted_value = format_value(value, is_percentage)
            data.append((k, formatted_value))

    # Matplotlib ile tablo oluşturma
    fig, ax = plt.subplots(figsize=(6, 10))
    ax.axis('off')
    ax.set_title(f"{symbol} ({BILINEN_HISSELER.get(symbol, 'Bilinmeyen Hisse')}) Kapsamlı Veriler", 
                 fontsize=16, fontweight='bold', pad=20)
    
    # Tablo verisi ve renk ayarları
    cell_text = []
    cell_colors = []
    
    for key, val in data:
        if val == "---":
            cell_text.append([key.split(" ")[1], ""]) # Sadece başlık emojisiz
            cell_colors.append(['#D3D3D3', '#D3D3D3']) # Gri tonu başlık
        else:
            cell_text.append([key, val])
            cell_colors.append(['#f8f8f8', '#ffffff']) # Beyaz tonları veri

    # Eğer veri yoksa boş tabloyu önle
    if not data:
             return None

    table = ax.table(cellText=cell_text, 
                      colLabels=["Gösterge", "Değer"], 
                      cellLoc='left', 
                      loc='center', 
                      cellColours=cell_colors)

    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.5)
    
    # Başlık hücrelerini kalınlaştırma
    for i in range(len(cell_text)):
        if cell_text[i][1] == "":
            table[i, 0].set_text_props(weight='bold', color='black')
            table[i, 1].set_text_props(weight='bold', color='black')

    # FİLİGRAN EKLEME
    add_watermark(fig)
    
    filename = f"fundamentals_{symbol}_comprehensive.png"
    plt.savefig(filename, bbox_inches='tight', dpi=150)
    plt.close(fig)
    return filename


# --- TRADINGVIEW TARZI GRAFİK VE GARANTİLİ YAHOO TEMEL ANALİZ ---

def get_val(data, key):
    """Veriyi hem dict hem de raw formatında kontrol eden güvenli fonksiyon."""
    if not data or not isinstance(data, dict):
        return None
    val = data.get(key)
    if isinstance(val, dict):
        return val.get("raw", val.get("fmt", None))
    return val

def fetch_fundamentals(symbol: str):
    """
    Yahoo API'den Cari Oran ve Borç verilerini garantili çeker.
    """
    try:
        ticker_symbol = f"{symbol}.IS" if not symbol.endswith(".IS") else symbol
        
        # Manuel API isteği (En sağlam yöntem)
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker_symbol}?modules=financialData,summaryDetail,defaultKeyStatistics"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        
        if response.status_code != 200: return None
            
        res = response.json().get("quoteSummary", {}).get("result", [{}])[0]
        fin = res.get("financialData", {})
        sd = res.get("summaryDetail", {})
        ks = res.get("defaultKeyStatistics", {})

        info = {}
        # Piyasa Verileri
        info["Fiyat (TRY)"] = get_val(fin, "currentPrice")
        info["Ort. Hacim (10 gün)"] = get_val(sd, "averageDailyVolume10Day")
        info["Piyasa Değeri"] = get_val(sd, "marketCap")
        info["Geriye Dönük F/K"] = get_val(sd, "trailingPE")
        info["İleriye Dönük F/K"] = get_val(sd, "forwardPE")
        info["Fiyat/Satış (P/S)"] = get_val(sd, "priceToSalesTrailing12Months")
        
        # Marjlar
        info["Brüt Kar Marjı (%)"] = get_val(fin, "grossMargins") * 100 if get_val(fin, "grossMargins") else None
        info["Faaliyet Kar Marjı (%)"] = get_val(fin, "operatingMargins") * 100 if get_val(fin, "operatingMargins") else None
        info["Net Kar Marjı (%)"] = get_val(fin, "profitMargins") * 100 if get_val(fin, "profitMargins") else None
        info["Özkaynak Karlılığı (ROE) (%)"] = get_val(fin, "returnOnEquity") * 100 if get_val(fin, "returnOnEquity") else None
        info["Varlık Karlılığı (ROA) (%)"] = get_val(fin, "returnOnAssets") * 100 if get_val(fin, "returnOnAssets") else None
        
        # ⚖️ Cari Oran ve Borçluluk (Kurtarılmış Veriler)
        info["Cari Oran"] = get_val(fin, "currentRatio")
        info["Borç/Özkaynak"] = get_val(fin, "debtToEquity")
        if info["Borç/Özkaynak"] is None:
            info["Borç/Özkaynak"] = get_val(ks, "debtToEquity")

        return info
    except Exception as e:
        print(f"Temel veri hatası: {e}")
        return None

def get_val(data, key):
    if not data or not isinstance(data, dict): return None
    v = data.get(key)
    return v.get("raw") if isinstance(v, dict) else v
# get_val fonksiyonunu da bu yapıya uygun hale getirelim:
def get_val(data, key):
    """Yahoo ham JSON içinden raw veriyi çeken güvenli fonksiyon."""
    if not data or not isinstance(data, dict):
        return None
    target = data.get(key)
    if isinstance(target, dict):
        return target.get("raw")
    return target
# ------------------- TradingView Tarama Fonksiyonları -------------------

def get_screener_data_from_payload(payload, url):
    """TradingView scanner API'sinden veri çeker."""
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

# --- PNG Tablo Oluşturma Fonksiyonları (Tarama için) ---

def create_table_png_base(df, filename_prefix, title, currency_symbol):
    """Ortak PNG oluşturma mantığı."""
    tablo_df = df[["Symbol", "close"]].copy()
    col_fiyat = f"Fiyat ({currency_symbol})"
    tablo_df.rename(columns={"Symbol": "Hisse", "close": col_fiyat}, inplace=True)

    total_rows = len(tablo_df)
    PAGE_SIZE = 20
    total_pages = math.ceil(total_rows / PAGE_SIZE)

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
            f"{title} (Sayfa {page+1}/{total_pages})",
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

        # FİLİGRAN EKLEME
        add_watermark(fig)

        plt.tight_layout()
        file_name = f"{filename_prefix}_{page + 1}.png"
        plt.savefig(file_name, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"🖼️ {file_name} kaydedildi.")
        
def create_table_png_bist_dip(df, filename_prefix="TR_tablo_dip"):
    return create_table_png_base(df, filename_prefix, "Dip Taraması BIST", "₺")

def create_table_png_nasdaq_dip(df, filename_prefix="US_tablo_dip"):
    return create_table_png_base(df, filename_prefix, "Dip Taraması NASDAQ", "$")

def create_table_png_bist_trend(df, filename_prefix="TR_trend_kirilimi"):
    return create_table_png_base(df, filename_prefix, "Düşen Trend Kırılımı BIST", "₺")

def create_table_png_bist_potansiyel(df, filename_prefix="TR_potansiyelli"):
    return create_table_png_base(df, filename_prefix, "Potansiyelli Kağıtlar BIST", "₺")
    
def create_table_png_nasdaq_potansiyel(df, filename_prefix="US_potansiyelli"):
    return create_table_png_base(df, filename_prefix, "Potansiyelli Kağıtlar NASDAQ", "$")


# ------------------- TRADINGVIEW ASENKRON TARAMA HANDLER'LARI -------------------

async def send_dip_tarama_bist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """BIST RSI<30 & StochRSI.K<20 sonuçlarını çeker ve PNG olarak gönderir."""
    
    query = update.callback_query
    await query.answer("Tarama başlatılıyor...")
    
    bist_payload = TRADINGVIEW_PAYLOAD_BIST_DIP.copy() 
    scanner_url_bist = "https://scanner.tradingview.com/turkey/scan" 

    await query.edit_message_text("⏳ **Dip Taraması BIST** sonuçları alınıyor ve tablo oluşturuluyor...")
    
    df_sonuc, toplam_adet = get_screener_data_from_payload(bist_payload, scanner_url_bist)
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if not df_sonuc.empty:
        filename_prefix = "TR_tablo_dip"
        create_table_png_bist_dip(df_sonuc, filename_prefix=filename_prefix)
        
        all_files = os.listdir('.')
        png_files = sorted([f for f in all_files if f.startswith(filename_prefix) and f.endswith('.png')])
        
        sent_files = 0
        
        if png_files:
            for file_name in png_files:
                try:
                    with open(file_name, "rb") as img:
                        caption = f"📈 **Dip Taraması BIST** Sonuçları ({file_name.split('_')[-1].replace('.png', '')}) - Toplam Hisse: {toplam_adet}"
                        await context.bot.send_photo(chat_id=query.message.chat_id, photo=img, caption=caption)
                    sent_files += 1
                except Exception as e:
                    print(f"PNG gönderme hatası ({file_name}): {e}")
                finally:
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    
            if sent_files > 0:
                await query.message.reply_text(f"✅ Tarama tamamlandı. Toplam **{toplam_adet}** hisse bulundu ve **{sent_files}** görsel gönderildi.", reply_markup=reply_markup)
            else:
                await query.message.reply_text("❌ Tarama sonuçları alındı ancak görsel gönderme hatası oluştu.", reply_markup=reply_markup)
                
        else:
            await query.message.reply_text("❌ Kurala uyan hisse bulunamadı, tablo oluşturulamadı.", reply_markup=reply_markup)

    else:
        await query.message.reply_text("❌ Veri çekme başarısız oldu veya kurala uyan sembol bulunamadı.", reply_markup=reply_markup)


async def send_dip_tarama_nasdaq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nasdaq gelişmiş dip filtresi sonuçlarını çeker ve PNG olarak gönderir."""
    
    query = update.callback_query
    await query.answer("Tarama başlatılıyor...")
    
    nasdaq_payload = TRADINGVIEW_PAYLOAD_NASDAQ_DIP.copy()
    scanner_url_nasdaq = "https://scanner.tradingview.com/america/scan" 

    await query.edit_message_text("⏳ **Dip Taraması NASDAQ** sonuçları alınıyor ve tablo oluşturuluyor...")
    
    df_sonuc, toplam_adet = get_screener_data_from_payload(nasdaq_payload, scanner_url_nasdaq)
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if not df_sonuc.empty:
        filename_prefix = "US_tablo_dip"
        create_table_png_nasdaq_dip(df_sonuc, filename_prefix=filename_prefix)
        
        all_files = os.listdir('.')
        png_files = sorted([f for f in all_files if f.startswith(filename_prefix) and f.endswith('.png')])
        
        sent_files = 0
        
        if png_files:
            for file_name in png_files:
                try:
                    with open(file_name, "rb") as img:
                        caption_parts = file_name.split('_')
                        page_info = f"Sayfa {caption_parts[-1].replace('.png', '')}"
                        caption = f"📈 **Dip Taraması NASDAQ** Sonuçları ({page_info}) - Toplam Hisse: {toplam_adet}"
                        await context.bot.send_photo(chat_id=query.message.chat_id, photo=img, caption=caption)
                    sent_files += 1
                except Exception as e:
                    print(f"PNG gönderme hatası ({file_name}): {e}")
                finally:
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    
            if sent_files > 0:
                await query.message.reply_text(f"✅ Tarama tamamlandı. Toplam **{toplam_adet}** hisse bulundu ve **{sent_files}** görsel gönderildi.", reply_markup=reply_markup)
            else:
                await query.message.reply_text("❌ Tarama sonuçları alındı ancak görsel gönderme hatası oluştu.", reply_markup=reply_markup)
                
        else:
            await query.message.reply_text("❌ Kurala uyan hisse bulunamadı, tablo oluşturulamadı.", reply_markup=reply_markup)

    else:
        await query.message.reply_text("❌ Veri çekme başarısız oldu veya kurala uyan sembol bulunamadı.", reply_markup=reply_markup)

async def Derinlik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    query = update.callback_query
    
    await query.edit_message_text("Derinlik/Akd şuanda aktif değil en yakın zamanda eklenecektir...")
    

async def send_dusen_trend_bist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Düşen Trend Kırılımı BIST (EMA, MACD, RSI bazlı) sonuçlarını çeker ve PNG olarak gönderir."""
    
    query = update.callback_query
    await query.answer("Tarama başlatılıyor...")
    
    trend_payload = TRADINGVIEW_PAYLOAD_BIST_TREND.copy()
    scanner_url_bist = "https://scanner.tradingview.com/turkey/scan" 

    await query.edit_message_text("⏳ **Düşen Trend Kırılımı BIST** sonuçları alınıyor ve tablo oluşturuluyor...")
    
    df_sonuc, toplam_adet = get_screener_data_from_payload(trend_payload, scanner_url_bist)
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if not df_sonuc.empty:
        filename_prefix = "TR_trend_kirilimi"
        create_table_png_bist_trend(df_sonuc, filename_prefix=filename_prefix)
        
        all_files = os.listdir('.')
        png_files = sorted([f for f in all_files if f.startswith(filename_prefix) and f.endswith('.png')])
        
        sent_files = 0
        
        if png_files:
            for file_name in png_files:
                try:
                    with open(file_name, "rb") as img:
                        caption_parts = file_name.split('_')
                        page_info = f"Sayfa {caption_parts[-1].replace('.png', '')}"
                        caption = f"🚀 **Düşen Trend Kırılımı BIST** Sonuçları ({page_info}) - Toplam Hisse: {toplam_adet}"
                        await context.bot.send_photo(chat_id=query.message.chat_id, photo=img, caption=caption)
                    sent_files += 1
                except Exception as e:
                    print(f"PNG gönderme hatası ({file_name}): {e}")
                finally:
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    
            if sent_files > 0:
                await query.message.reply_text(f"✅ Tarama tamamlandı. Toplam **{toplam_adet}** hisse bulundu ve **{sent_files}** görsel gönderildi.", reply_markup=reply_markup)
            else:
                await query.message.reply_text("❌ Tarama sonuçları alındı ancak görsel gönderme hatası oluştu.", reply_markup=reply_markup)
                
        else:
            await query.message.reply_text("❌ Kurala uyan hisse bulunamadı, tablo oluşturulamadı.", reply_markup=reply_markup)

    else:
        await query.message.reply_text("❌ Veri çekme başarısız oldu veya kurala uyan sembol bulunamadı.", reply_markup=reply_markup)


async def send_potansiyelli_kagitlar_bist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Potansiyelli Kağıtlar BIST taraması sonuçlarını çeker ve PNG olarak gönderir."""
    
    query = update.callback_query
    await query.answer("Tarama başlatılıyor...")
    
    potansiyel_payload = TRADINGVIEW_PAYLOAD_BIST_POTANSIYEL.copy()
    scanner_url_bist = "https://scanner.tradingview.com/turkey/scan" 

    await query.edit_message_text("⏳ **Potansiyelli Kağıtlar BIST** sonuçları alınıyor ve tablo oluşturuluyor...")
    
    df_sonuc, toplam_adet = get_screener_data_from_payload(potansiyel_payload, scanner_url_bist)
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if not df_sonuc.empty:
        filename_prefix = "TR_potansiyelli"
        create_table_png_bist_potansiyel(df_sonuc, filename_prefix=filename_prefix)
        
        all_files = os.listdir('.')
        png_files = sorted([f for f in all_files if f.startswith(filename_prefix) and f.endswith('.png')])
        
        sent_files = 0
        
        if png_files:
            for file_name in png_files:
                try:
                    with open(file_name, "rb") as img:
                        caption_parts = file_name.split('_')
                        page_info = f"Sayfa {caption_parts[-1].replace('.png', '')}"
                        caption = f"💰 **Potansiyelli Kağıtlar BIST** Sonuçları ({page_info}) - Toplam Hisse: {toplam_adet}"
                        await context.bot.send_photo(chat_id=query.message.chat_id, photo=img, caption=caption)
                    sent_files += 1
                except Exception as e:
                    print(f"PNG gönderme hatası ({file_name}): {e}")
                finally:
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    
            if sent_files > 0:
                await query.message.reply_text(f"✅ Tarama tamamlandı. Toplam **{toplam_adet}** hisse bulundu ve **{sent_files}** görsel gönderildi.", reply_markup=reply_markup)
            else:
                await query.message.reply_text("❌ Tarama sonuçları alındı ancak görsel gönderme hatası oluştu.", reply_markup=reply_markup)
                
        else:
            await query.message.reply_text("❌ Kurala uyan hisse bulunamadı, tablo oluşturulamadı.", reply_markup=reply_markup)

    else:
        await query.message.reply_text("❌ Veri çekme başarısız oldu veya kurala uyan sembol bulunamadı.", reply_markup=reply_markup)


async def send_potansiyelli_kagitlar_nasdaq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Potansiyelli Kağıtlar NASDAQ taraması sonuçlarını çeker ve PNG olarak gönderir."""
    
    query = update.callback_query
    await query.answer("Tarama başlatılıyor...")
    
    potansiyel_payload = TRADINGVIEW_PAYLOAD_NASDAQ_POTANSIYEL.copy()
    scanner_url_nasdaq = "https://scanner.tradingview.com/america/scan" # URL düzeltildi

    await query.edit_message_text("⏳ **Potansiyelli Kağıtlar NASDAQ** sonuçları alınıyor ve tablo oluşturuluyor...")
    
    df_sonuc, toplam_adet = get_screener_data_from_payload(potansiyel_payload, scanner_url_nasdaq)
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if not df_sonuc.empty:
        # HATA DÜZELTMESİ: Doğru PNG oluşturma fonksiyonu ve dosya öneki kullanılıyor
        filename_prefix = "US_potansiyelli" 
        create_table_png_nasdaq_potansiyel(df_sonuc, filename_prefix=filename_prefix)
        
        all_files = os.listdir('.')
        png_files = sorted([f for f in all_files if f.startswith(filename_prefix) and f.endswith('.png')])
        
        sent_files = 0
        
        if png_files:
            for file_name in png_files:
                try:
                    with open(file_name, "rb") as img:
                        caption_parts = file_name.split('_')
                        page_info = f"Sayfa {caption_parts[-1].replace('.png', '')}"
                        # HATA DÜZELTMESİ: Başlıkta "NASDAQ" kullanılıyor
                        caption = f"💰 **Potansiyelli Kağıtlar NASDAQ** Sonuçları ({page_info}) - Toplam Hisse: {toplam_adet}"
                        await context.bot.send_photo(chat_id=query.message.chat_id, photo=img, caption=caption)
                    sent_files += 1
                except Exception as e:
                    print(f"PNG gönderme hatası ({file_name}): {e}")
                finally:
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    
            if sent_files > 0:
                await query.message.reply_text(f"✅ Tarama tamamlandı. Toplam **{toplam_adet}** hisse bulundu ve **{sent_files}** görsel gönderildi.", reply_markup=reply_markup)
            else:
                await query.message.reply_text("❌ Tarama sonuçları alındı ancak görsel gönderme hatası oluştu.", reply_markup=reply_markup)
                
        else:
            await query.message.reply_text("❌ Kurala uyan hisse bulunamadı, tablo oluşturulamadı.", reply_markup=reply_markup)

    else:
        await query.message.reply_text("❌ Veri çekme başarısız oldu veya kurala uyan sembol bulunamadı.", reply_markup=reply_markup)


# ------------------- YENİ HABER FONKSİYONLARI (MIDAS) -------------------

def fetch_midas_news(limit=5):
    """
    Midas 'Midas Kulakları' sayfasından belirtilen class'taki son haberleri çeker.
    """
    URL = MIDAS_NEWS_URL
    CONTAINER_CLASS = MIDAS_CONTAINER_CLASS
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    news_list = []
    
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tüm haber kapsayıcılarını bul
        all_containers = soup.find_all(class_=CONTAINER_CLASS, limit=limit)

        for container in all_containers:
            # Her kapsayıcı içindeki ana linki bul
            main_link = container.find('a')
            
            if main_link and main_link.has_attr('href'):
                href = main_link.get('href')
                full_href = f"https://www.getmidas.com{href}" if href.startswith('/') else href
                
                # Başlık metnini temizleme (verdiğiniz mantığa göre)
                full_text = main_link.get_text(strip=True)
                
                # "okuma süresi" ifadesinden sonraki kısmı başlık olarak alalım.
                clean_title = full_text.split("okuma süresi", 1)[-1] 
                clean_title = clean_title.strip()
                
                # Başlık içinde bazen sadece tarih/süre bilgisi kalabiliyor.
                # Tekrar kontrol edelim: Eğer çok kısa veya sadece rakamlardan oluşuyorsa geç.
                if clean_title and len(clean_title) > 10: 
                    news_list.append({
                        "title": clean_title,
                        "url": full_href
                    })
                
                if len(news_list) >= limit:
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"❌ Midas Haber Çekme Hatası (Bağlantı/Timeout/HTTP): {e}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Midas Haber Çekme Hatası (Parsing): {e}", file=sys.stderr)
    
    return news_list

async def send_midas_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Midas'tan çekilen son 5 haberi Telegram'a mesaj olarak gönderir."""
    
    query = update.callback_query
    await query.answer("Son haberler çekiliyor...")
    
    await query.edit_message_text("⏳ **Midas Kulakları Haberleri** alınıyor...")
    
    # YENİ FONKSİYONU ÇAĞIR
    news_data = fetch_midas_news(limit=5)
    
    keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if news_data:
        message_text = "📰 **Midas Kulakları Haberleri**\n"
        message_text += "--------------------------------------\n"
        
        for i, news in enumerate(news_data):
            # Telegram'ın Markdown V2 formatına uygun başlık ve link formatı
            # Başlıkta özel karakter olabileceği için kaçış karakterleri uygulayalım.
            def escape_markdown(text):
                # Sadece temel karakterleri kaçır
                return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
                
            title_escaped = news['title'].replace('\n', ' ').strip()
            
            # Markdown link yapısını kullan
            message_text += f"{i+1}. **{title_escaped} **\n"
            message_text += f"[Haberi Oku]({news['url']})\n"
            message_text += "--------------------------------------\n"
            
        await query.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        # Bu mesajı silmek yerine yeni mesaj attık, geri dönülecek yer silinmemeli.
        # İlk '⏳ alınıyor...' mesajını sil:
        await query.message.delete()
        
    else:
        await query.message.reply_text("❌ Haberler şu anda Midas'tan alınamıyor. Lütfen daha sonra tekrar deneyin.", reply_markup=reply_markup)


# ------------------- KANAL ABONELİĞİ KONTROLÜ -------------------

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının zorunlu kanallara abone olup olmadığını kontrol eder (Mesaj/Start için)."""
    user_id = update.effective_user.id
    required_channels = get_required_channels() 

    if not required_channels:
        return True 

    missing_channels = []
    
    for channel_id in required_channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                missing_channels.append(channel_id)
        except Exception as e:
            print(f"Kanal kontrol hatası ({channel_id}): {e}")
            missing_channels.append(channel_id) 

    if not missing_channels:
        return True 
    else:
        keyboard = []
        for channel in missing_channels:
            if channel.startswith('@'):
                link_url = f"https://t.me/{channel.replace('@', '')}"
                link_name = channel
            else:
                # Varsayım: Sayısal ID yerine davet linki hash'i kullanıldı.
                link_url = f"https://t.me/joinchat/{channel}"
                link_name = f"ID: {channel}"


            keyboard.append([InlineKeyboardButton(f"➡️ Kanal: {link_name}", url=link_url)])
        
        keyboard.append([InlineKeyboardButton("✅ Kontrol Et (Abone Oldum)", callback_data="CHECK_SUBSCRIPTION")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.effective_message:
            await update.effective_message.reply_text(
                "🛑 **Devam etmek için aşağıdaki kanallara abone olmanız gerekmektedir.**\n"
                "Abone olduktan sonra 'Kontrol Et' butonuna tıklayınız.", 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        return False

async def check_subscription_for_callback(user_id, context, message):
    """Callback sorgularından gelen kullanıcılar için abonelik kontrolü ve mesaj güncellemesi yapar."""
    required_channels = get_required_channels()
    missing_channels = []
    
    if not required_channels:
        return True 

    for channel_id in required_channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                missing_channels.append(channel_id)
        except Exception as e:
            print(f"Kanal kontrol hatası ({channel_id}): {e}")
            missing_channels.append(channel_id)

    if not missing_channels:
        return True
    else:
        keyboard = []
        for channel in required_channels:
            if channel.startswith('@'):
                link_url = f"https://t.me/{channel.replace('@', '')}"
                link_name = channel
            else:
                link_url = f"https://t.me/joinchat/{channel}"
                link_name = f"ID: {channel}"
            
            keyboard.append([InlineKeyboardButton(f"➡️ Kanal: {link_name}", url=link_url)])
        
        keyboard.append([InlineKeyboardButton("✅ Kontrol Et (Abone Oldum)", callback_data="CHECK_SUBSCRIPTION")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.edit_text(
            "🛑 **Devam etmek için aşağıdaki kanallara abone olmanız gerekmektedir.**\n"
            "Abone olduktan sonra 'Kontrol Et' butonuna tıklayınız.", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return False

# ------------------- KLAVYE & MENÜ FONKSİYONLARI -------------------

def main_menu_keyboard():
    """Ana menü için InlineKeyboardMarkup döndürür."""
    keyboard = [
        [
            InlineKeyboardButton("📈 Hisse Analizi (Teknik+Temel)", callback_data="HISSE"),
        ],
        [
            InlineKeyboardButton("📈 Derinlik/AKD", callback_data="Derinlik"),
        ],
        [
            InlineKeyboardButton("📰 Haberler", callback_data="HABERLER"), # YENİ HABER BUTONU
        ],
        [
            InlineKeyboardButton("📊 Tarama Listeleri BIST", callback_data="TARAMA"),
        ],
        [
            InlineKeyboardButton("📊 Tarama Listeleri NASDAQ", callback_data="TARAMANASDAQ"),
        ],
        [
            InlineKeyboardButton("📣 Reklam/İletişim", callback_data="REKLAM"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ------------------- Komutlar -------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_user(user.id, user.username, user.first_name)
    
    if not await check_subscription(update, context):
        return
        
    await update.message.reply_text("Hoşgeldiniz! Menüden bir seçenek seçin:", reply_markup=main_menu_keyboard())

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Abonelikler kontrol ediliyor...")
    
    await query.edit_message_text("⏳ Abonelikler tekrar kontrol ediliyor...")
    
    is_subscribed = await check_subscription_for_callback(query.from_user.id, context, query.message)

    if is_subscribed:
        await query.edit_message_text("✅ Abonelik kontrolü başarılı. Menüden bir seçenek seçin:", 
                                     reply_markup=main_menu_keyboard())

# --- YETKİLİ KANAL YÖNETİM KOMUTLARI ---
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Bu komutu kullanmaya yetkiniz yok.")
        return

    if not context.args:
        await update.message.reply_text("➕ Lütfen eklenecek kanalın ID'sini veya @kullanıcıadını girin. Örn: `/addchannel @kanal_ismi`")
        return

    channel_id = context.args[0].strip()
    
    if not channel_id.startswith('@') and not channel_id.startswith('-100'):
        await update.message.reply_text("⚠️ Geçersiz kanal ID formatı. Lütfen '@kanal_adı' veya '-100...' sayısal ID kullanın.")
        return

    if add_channel_to_file(channel_id):
        await update.message.reply_text(f"✅ Kanal **{channel_id}** zorunlu abonelik listesine eklendi. Botun bu kanalda yönetici olduğundan emin olun.")
    else:
        await update.message.reply_text(f"ℹ️ Kanal **{channel_id}** zaten listede bulunuyor.")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Bu komutu kullanmaya yetkiniz yok.")
        return

    if not context.args:
        await update.message.reply_text("➖ Lütfen kaldırılacak kanalın ID'sini veya @kullanıcıadını girin. Örn: `/removechannel @eski_kanal`")
        return

    channel_id = context.args[0].strip()

    if remove_channel_from_file(channel_id):
        await update.message.reply_text(f"✅ Kanal **{channel_id}** zorunlu abonelik listesinden kaldırıldı.")
    else:
        await update.message.reply_text(f"ℹ️ Kanal **{channel_id}** listede bulunamadı.")
        
async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Bu komutu kullanmaya yetkiniz yok.")
        return

    channels = get_required_channels()
    if channels:
        channel_list = "\n".join(channels)
        await update.message.reply_text(f"📢 Zorunlu Abonelik Kanalları:\n\n{channel_list}")
    else:
        await update.message.reply_text("📢 Zorunlu abonelik kanalı bulunmamaktadır.")

async def duyuru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Yetki kontrolü
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Bu komutu kullanmaya yetkiniz yok.")
        return
    
    # Komutun kendisini (/duyuru) metinden çıkarıp geri kalan mesajı olduğu gibi alıyoruz
    # Bu yöntem context.args kullanımından daha sağlıklıdır çünkü tüm boşlukları korur.
    announcement_text_raw = update.message.text.partition(' ')[2]

    if not announcement_text_raw:
        await update.message.reply_text("📢 Lütfen duyuru metnini girin. Örn:\n`/duyuru` mesajın buraya...")
        return

    # Başına sabit başlık ekliyoruz (Markdown formatında)
    final_message = f"📣 **DUYURU** 📣\n\n{announcement_text_raw}"
    
    user_ids = get_all_user_ids()
    sent_count = 0
    failed_count = 0

    status_msg = await update.message.reply_text(f"⏳ Duyuru {len(user_ids)} kullanıcıya gönderiliyor...")

    for user_id in user_ids:
        try:
            # Markdown yerine HTML kullanmak genellikle boşluk ve karakter hatalarını azaltır
            # Ama senin tercihin Markdown ise 'Markdown' olarak bırakabiliriz.
            await context.bot.send_message(
                chat_id=user_id, 
                text=final_message, 
                parse_mode='Markdown'
            )
            sent_count += 1
            # Çok hızlı gönderip Telegram limitlerine takılmamak için kısa bir bekleme (opsiyonel)
            # time.sleep(0.05) 
        except Exception as e:
            print(f"Duyuru gönderilemedi (ID: {user_id}): {e}")
            failed_count += 1
            
    await status_msg.edit_text(f"✅ Duyuru tamamlandı.\nBaşarılı: **{sent_count}**\nBaşarısız: **{failed_count}**")
# ------------------- Mesaj ve Callback Handler'ları -------------------

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "CHECK_SUBSCRIPTION":
        await check_subscription_callback(update, context)
        return

    if data == "BACK_MAIN":
        is_subscribed = await check_subscription_for_callback(query.from_user.id, context, query.message)
        
        if not is_subscribed:
             return 
             
        await query.edit_message_text("Ana menüye dönüldü.", reply_markup=main_menu_keyboard())
        return

    # Abonelik kontrolü her zaman başta yapılmalı
    is_subscribed = await check_subscription_for_callback(query.from_user.id, context, query.message)
    if not is_subscribed:
        return 

    if data == "HISSE":
        await query.edit_message_text("📈 Lütfen analiz yapmak istediğiniz hisse kodunu yazınız:")
        context.user_data['waiting_for_stock'] = True
        return

    if data == "HABERLER": # YENİ HABER YÖNLENDİRMESİ
        # Haber gönderme fonksiyonunu çağır
        await send_midas_news(update, context) 
        return

    if data == "TARAMA":
        keyboard = [
            [InlineKeyboardButton("✅ Dip Taraması  BIST (Günlük)", callback_data="Dip_Taramasi_BIST")],
            [InlineKeyboardButton("✅ Düşen Trend Kırılımı BIST (Aylık)", callback_data="Dusen_Trend_Kirilimi_BIST")],
            [InlineKeyboardButton("✅ Potansiyelli Kağıtlar BIST (Aylık)", callback_data="Potansiyelli_Kagitlar_BIST")], 
            [InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📊 Tarama seçeneklerinden birini seçin:", reply_markup=reply_markup)
        return
    
    if data == "TARAMANASDAQ":
        keyboard = [
            [InlineKeyboardButton("✅ Dip Taraması NASDAQ (Günlük)", callback_data="Dip_Taramasi_NASDAQ")],
            [InlineKeyboardButton("✅ Potansiyelli Kağıtlar NASDAQ (Aylık)", callback_data="Potansiyelli_Kagitlar_NASDAQ")], 
            [InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📊 Tarama seçeneklerinden birini seçin:", reply_markup=reply_markup)
        return

    if data == "REKLAM":
        keyboard = [[InlineKeyboardButton("⬅️ Geri Dön", callback_data="BACK_MAIN")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📢 Yardım, sorun bildir veya reklam ver seçenekleri için mesaj atın.\n @Finansalguc1 @UHYborsaumut", reply_markup=reply_markup)
        return

    # --- TARAMA BUTONLARI YÖNLENDİRMELERİ ---
    if data == "Dip_Taramasi_BIST":
        await send_dip_tarama_bist(update, context)
        return

    if data == "Dip_Taramasi_NASDAQ":
        await send_dip_tarama_nasdaq(update, context)
        return

    if data == "Derinlik":
        await Derinlik(update, context)
        return

    if data == "Dusen_Trend_Kirilimi_BIST":
        await send_dusen_trend_bist(update, context)
        return

    if data == "Potansiyelli_Kagitlar_BIST": 
        await send_potansiyelli_kagitlar_bist(update, context)
        return
    if data == "Potansiyelli_Kagitlar_NASDAQ": 
        await send_potansiyelli_kagitlar_nasdaq(update, context)
        return

# ------------------- YENİ EKLENEN YAPAY ZEKA YORUM FONKSİYONU -------------------

# ------------------- GÜNCELLENMİŞ YAPAY ZEKA KAPSAMLI YORUM FONKSİYONU -------------------

# ------------------- GÜNCELLENMİŞ YAPAY ZEKA KAPSAMLI YORUM FONKSİYONU (HATA GİDERİLDİ) -------------------

# ------------------- GÜNCELLENMİŞ YAPAY ZEKA KAPSAMLI YORUM FONKSİYONU (HATALAR GİDERİLDİ) -------------------

def generate_ai_commentary(symbol: str, fundamentals: dict) -> str:
    """
    Verilen temel analiz özetini (GYO/Varlık odaklı) daha kapsamlı yorumlar.
    """
    
    # Simülasyon verilerini güvenli bir şekilde çekme (Kullanıcının verdiği örnek veriler baz alınarak)
    fk = fundamentals.get('Geriye Dönük F/K')
    roe = fundamentals.get('Özkaynak Karlılığı (ROE) (%)')
    roa = fundamentals.get('Varlık Karlılığı (ROA) (%)') 
    current_ratio = fundamentals.get('Cari Oran')
    debt_to_equity = fundamentals.get('Borç/Özkaynak')
    ps = fundamentals.get('Fiyat/Satış (P/S)') 
    
    # Ekstra varsayılan veriler 
    net_profit_margin = fundamentals.get('Net Kar Marjı (%)')
    
    # ------------------- 1. Temel Çıkarımlar ve Yorum Cümleleri -------------------
    yorumlar = []
    
    # 1.1. Değerleme (F/K)
    if fk is not None and fk > 0:
        if fk < 10:
            yorumlar.append(f"Çok Düşük F/K ({fk:.2f}) oranı, hissenin mevcut **yüksek kârlılığa göre çok ucuz** (iskontolu) işlem gördüğünü gösterir.")
        elif fk > 20:
            yorumlar.append(f"Yüksek F/K ({fk:.2f}) oranı, piyasanın şirketten **agresif bir büyüme beklentisi** olduğunu gösterir.")
        else:
            yorumlar.append(f"F/K oranı ({fk:.2f}) piyasa ortalamasında kabul edilebilir bir seviyededir.")
    elif fk is not None and fk <= 0:
         yorumlar.append("Negatif F/K oranı, şirketin son 12 ayda **zarar** ettiğini gösterir. Temel analiz açısından güçlü bir zayıflıktır.")
    
    # 1.2. Kârlılık ve Verimlilik (Net Kar Marjı, ROA)
    if net_profit_margin is not None and net_profit_margin > 15:
        yorumlar.append(f"Mükemmel Net Kâr Marjı ({net_profit_margin:.2f}%) ile şirket, satışlarının büyük bir kısmını kâra çevirmede **son derece başarılıdır**.")
    elif net_profit_margin is not None and net_profit_margin > 5:
        yorumlar.append(f"Güçlü Net Kâr Marjı ({net_profit_margin:.2f}%).")

    if roa is not None:
        if symbol.endswith('GYO') or roa < 5: 
            yorumlar.append(f"Varlık Karlılığı (ROA) ({roa:.2f}%) düşüktür. Ancak, **GYO'lar** ve varlık şirketlerinde varlıklar yüksek değerlendiği için bu oran düşük çıkar ve bu durum **sektör için normaldir**.")
        elif roa > 10:
            yorumlar.append(f"Yüksek Varlık Karlılığı (ROA) ({roa:.2f}%) ile şirketin varlıklarını etkin kullandığı görülmektedir.")

    # 1.3. Likidite ve Borçluluk (Cari Oran, Borç/Özkaynak)
    if current_ratio is not None and current_ratio >= 1.5:
        yorumlar.append(f"Cari Oran ({current_ratio:.2f}) 1.5'in üzerindedir. Şirketin kısa vadeli yükümlülüklerini yerine getirme konusunda **güçlü ve rahat bir likiditeye** sahip olduğu görülmektedir.")
    elif current_ratio is not None and current_ratio < 1:
        yorumlar.append(f"Cari Oran ({current_ratio:.2f}) 1'in altındadır. Kısa vadeli borç ödemede baskı riski mevcuttur. **Dikkatle incelenmelidir**.")
    elif current_ratio is not None:
         yorumlar.append(f"Cari Oran ({current_ratio:.2f}) yeterli düzeydedir (1.0 ile 1.5 arası).")

    if debt_to_equity is not None:
        if debt_to_equity < 1:
            yorumlar.append(f"Borç/Özkaynak oranı ({debt_to_equity:.2f}) 1'in altındadır. Finansal kaldıraç orta düzeydedir ve **borç yükü yönetilebilir** sınırlar içindedir.")
        else:
            yorumlar.append(f"Borç/Özkaynak oranı ({debt_to_equity:.2f}) 1'in üzerindedir. Borçluluk seviyesi yüksektir, ancak GYO/Altyapı şirketlerinde bu borcun uzun vadeli olması riski hafifletebilir.")
            
    # 1.4. P/S Oranı ve Sektörel Bağlam (Özel Durum)
    if ps is not None:
        if symbol.endswith('GYO') and ps is not None and ps > 5: # ps için None kontrolü eklendi
            yorumlar.append(f"Yüksek P/S Oranı ({ps:.2f}) satışlara göre pahalı görünse de, GYO'larda asıl odak **aktiflerin net defter değeri (NAV)** üzerindedir. Yüksek P/S, piyasanın aktiflerin değerini yüksek gördüğü şeklinde yorumlanabilir.")
        elif ps is not None and ps > 5:
            yorumlar.append(f"P/S Oranı ({ps:.2f}) yüksektir, bu da şirketin satış gelirlerine göre yüksek fiyatlandığını ve piyasanın gelecekteki satış artışını peşinen fiyatladığını gösterir.")

    # ------------------- 2. Yorumu Birleştirme ve Sınıflandırma -------------------
    
    is_gyo = symbol.endswith('GYO')
    overall_sentiment = "Dengeli"
    if fk is not None and fk < 10 and fk > 0 and net_profit_margin is not None and net_profit_margin > 15:
        overall_sentiment = "Güçlü Kârlılık ve Cazip Değerleme"
    elif fk is not None and fk <= 0:
        overall_sentiment = "Zayıf Kârlılık"
    elif debt_to_equity is not None and debt_to_equity > 2 and not is_gyo:
        overall_sentiment = "Yüksek Finansal Risk"

    # HATA GİDERİLDİ: Puan tablosundaki anahtar adları, tablodaki sütun başlıklarıyla eşleştirildi.
    puan_tablosu = {
         "Değerleme (F/K)": "Çok Güçlü" if fk is not None and fk < 10 and fk > 0 else "Nötr",
         "Kârlılık Marjları": "Mükemmel" if net_profit_margin is not None and net_profit_margin > 15 else "Güçlü",
         "Likidite Düzeyi": "Güçlü" if current_ratio is not None and current_ratio >= 1.5 else "Yeterli/Riskli",
         "Borç Yükü": "Orta/Güçlü" if debt_to_equity is not None and debt_to_equity < 1 else "Yüksek Kaldıraç",
         "Verimlilik (ROA/P/S)": "Nötr (Sektöre Özgü)" if is_gyo else ("Düşük" if roa is not None and roa < 5 else "Yüksek")
    }

    if not yorumlar:
         final_commentary = f"⚠️ **{symbol}** için temel finansal veriler çekilemedi veya yorumlanmaya uygun nitelikte bir veri seti bulunamadı."
    else:
        # Hata düzeltildi: yom değişkeni kullanılıyor
        final_commentary = (
            f"🧠 **Yapay Zeka Kapsamlı Analiz ({symbol})**\n"
            "--------------------------------------------------\n"
            "### 🔎 Temel Çıkarımlar:\n" +
            "\n".join([f"• {yom}" for yom in yorumlar]) +
            f"\n\n### ⭐ Finansal Sağlık Özet Karnesi:\n"
            f"| Kriter | Durum |\n"
            f"|:---|:---|\n"
            f"| Değerleme (F/K) | **{puan_tablosu['Değerleme (F/K)']}** |\n"
            f"| Kârlılık Marjları | **{puan_tablosu['Kârlılık Marjları']}** |\n" # Hata buradaydı, düzeltildi!
            f"| Likidite Düzeyi | **{puan_tablosu['Likidite Düzeyi']}** |\n"
            f"| Borç Yükü | **{puan_tablosu['Borç Yükü']}** |\n"
            f"| Varlık Verimliliği (ROA) | **{puan_tablosu['Verimlilik (ROA/P/S)']}** |\n"
            f"\n### 🎯 Genel Eğilim\n"
            f"Şirket, **{overall_sentiment}** bir görünüme sahiptir.\n"
            f"**Önemli Not:** Değerleme cazipken kârlılık marjları güçlüdür. Ancak eğer hisse bir GYO ise, ROA ve P/S oranlarındaki sapmalar normal kabul edilmeli ve asıl analiz, **Net Aktif Değerine (NAV)** odaklanmalıdır.\n\n"
            f"*(Bu analiz bilgilendirme amaçlı Yapay Zeka simülasyonudur ve kesinlikle yatırım tavsiyesi değildir.)*"
        )
    return final_commentary


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Abonelik kontrolü
    if not await check_subscription(update, context):
        return

    # Sadece hisse kodu bekleniyorsa çalışır
    if context.user_data.get('waiting_for_stock'):
        text = update.message.text.strip().upper()
        context.user_data['waiting_for_stock'] = False
        
        mevcut_hisseler = list(BILINEN_HISSELER.keys())
        
        # 1. Tam Eşleşme Kontrolü
# handle_message içindeki ilgili blok
        if text in BILINEN_HISSELER:
            hisse_adi = BILINEN_HISSELER[text]
            message = await update.message.reply_text(f"⏳ **{text}** için veriler alınıyor...")
            
            # --- HATAYI ÇÖZEN KISIM ---
            chart_df = fetch_chart_data(text) # Değişken adı 'chart_df' yapıldı
            chart_path = None
            
            # DataFrame kontrolü: Asla 'if chart_df:' yazma!
            if isinstance(chart_df, pd.DataFrame) and not chart_df.empty:
                chart_path = plot_advanced_chart(text, chart_df)
            # --------------------------

            fundamentals = fetch_fundamentals(text)
            fundamentals_path = generate_fundamentals_image(text, fundamentals) if fundamentals else None
            ai_commentary = generate_ai_commentary(text, fundamentals) if fundamentals else None

            await message.delete()

            # Fotoğrafları gönder
            if chart_path:
                with open(chart_path, "rb") as img:
                    await update.message.reply_photo(img, caption=f"📈 {text} - 2 Yıllık Heikin-Ashi Grafiği")
                os.remove(chart_path)
            
            if fundamentals_path:
                with open(fundamentals_path, "rb") as img2:
                    await update.message.reply_photo(img2, caption=f"💹 {text} - Cari Temel Veriler")
                os.remove(fundamentals_path)            
            if ai_commentary:
                await update.message.reply_text(ai_commentary, parse_mode='Markdown')
            
            keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("İşlem tamamlandı.", reply_markup=reply_markup)
            
            return # Tam eşleşme işlemi bitti
            
        
        # 2. Benzerlik Kontrolü (FUZZY MATCHING) - Yeni/düzeltilmiş blok
        
        # Benzerlik skoru 80 ve üzeri olan ilk 5 eşleşmeyi bul
        best_matches = process.extractBests(text, mevcut_hisseler, limit=5, score_cutoff=80) 

        if best_matches:
            # Öneri metnini hazırla
            oneriler = []
            for match, score in best_matches:
                company_name = BILINEN_HISSELER.get(match, "Bilinmeyen Şirket")
                # Skor 85 ve üzeri ise kalın, altı ise normal yaz
                if score >= 85:
                    oneriler.append(f"**{match}** ({company_name}) - Benzerlik: {score}%")
                else:
                    # %80-84 arası eşleşmeler
                    oneriler.append(f"{match} ({company_name}) - Benzerlik: {score}%") 
            
            oneriler_metni = "\n".join(oneriler)
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"❌ **'{text}'** kodu tam olarak bulunamadı. Lütfen aşağıdaki **benzer hisselerden** birinin kodunu tam olarak girin:\n\n{oneriler_metni}\n\n", 
                reply_markup=reply_markup, 
                parse_mode='Markdown'
            )
            # Burada tekrar hisse kodu beklemeye devam etmesi için 'waiting_for_stock' flag'ini tekrar True yapıyoruz.
            context.user_data['waiting_for_stock'] = True 
            return # Benzerlik eşleşme işlemi bitti

        # 3. Hiçbir Eşleşme Yoksa (Skor < 80)
        keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="BACK_MAIN")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ **{text}** geçerli bir BIST kodu değil ve yüksek benzerlikte bir kod bulunamadı (Eşleşme Skoru < 80). Lütfen listeden bir kodu kontrol edin.",
            reply_markup=reply_markup
        )
        context.user_data['waiting_for_stock'] = True 
        return
            
    else:
        # Menü harici bir mesaj gelirse
        await update.message.reply_text("Lütfen menüden bir seçenek seçin veya /start yazın.", reply_markup=main_menu_keyboard())
# ------------------- Hata -------------------

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f'Hata oluştu: {context.error}')
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin veya /start ile menüye dönün."
            )
        except:
            pass

# ------------------- Bot Başlat -------------------

def main():
    clear()
    print("Bot modülleri kontrol ediliyor...")
    
    if 'BeautifulSoup' not in globals():
             print("❌ BeautifulSoup kütüphanesi yüklü.")


    time.sleep(1)
    print("Bot çalışıyor... ✅\n")

    app = Application.builder().token(BOT_TOKEN).build()
    
    # Komutlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("duyuru", duyuru))
    app.add_handler(CommandHandler("addchannel", add_channel)) 
    app.add_handler(CommandHandler("removechannel", remove_channel)) 
    app.add_handler(CommandHandler("listchannels", list_channels)) 
    
    # Callback Query Handler
    app.add_handler(CallbackQueryHandler(button))
    
    # Mesaj Handler (Komut olmayan tüm metin mesajları)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.add_error_handler(error)
    app.run_polling()

if __name__ == "__main__":
    main()