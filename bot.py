import os
import time
import requests
from google import genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import AlertPresentException

# --- 환경 설정 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try: requests.post(url, data=payload)
    except: pass

def crawl_and_analyze():
    send_telegram_msg("🚀 **천안 경매 비서 가동 (팝업 제어 모드)**")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # 1. 상세 검색 페이지 접속
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        time.sleep(5)
        
        # 2. 법원 선택
        send_telegram_msg("📍 대전지방법원 천안지원 선택 중...")
        jiwon = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        Select(jiwon).select_by_visible_text("대전지방법원 천안지원")
        time.sleep(2)
        
        # 3. 검색 버튼 직접 클릭 (가장 중요!)
        send_telegram_msg("🔍 검색 버튼 클릭 시도...")
        search_btn = driver.find_element(By.XPATH, "//a[contains(@onclick, 'goSrch')]")
        driver.execute_script("arguments[0].click();", search_btn)
        
        # 4. 혹시 모를 팝업창(Alert) 확인 및 닫기
        time.sleep(3)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            send_telegram_msg(f"⚠️ 법원 사이트 메시지: {alert_text}")
            alert.accept() # 확인 버튼 누르기
        except AlertPresentException:
            pass # 팝업 없으면 통과
            
        # 5. 결과 로딩 대기
        send_telegram_msg("⏳ 결과 데이터를 기다리는 중 (15초)...")
        time.sleep(15)
        
        # 6. 결과 파싱
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        
        if len(items) > 1:
            send_telegram_msg(f"✅ {len(items)-1}건
