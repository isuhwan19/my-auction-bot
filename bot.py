import os
import time
import requests
import json
from google import genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- 환경 설정 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def crawl_and_analyze():
    # 1. 실행 시작 알림 (이게 와야 프로그램이 돌기 시작한 것임)
    send_telegram_msg("⚙️ 브라우저 엔진 기동 중...")
    
    options = Options()
    options.add_argument("--headless=new") # 최신 헤드리스 모드 사용
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled") # 자동화 감지 회피
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # 자동화 감지 방지 스크립트 실행
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    try:
        # 2. 사이트 접속 시도 알림
        send_telegram_msg("🌐 법원 경매 사이트 접속 시도 중...")
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        time.sleep(7)
        
        # 접속 성공 여부 확인 (제목 읽기)
        page_title = driver.title
        print(f"페이지 제목: {page_title}")
        
        # 3. 법원 선택 (가장 에러가 잦은 구간)
        send_telegram_msg("📍 천안지원 검색 조건 입력 중...")
        wait = WebDriverWait(driver, 20)
