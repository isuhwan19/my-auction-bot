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

# --- 1. 환경 설정 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except:
        pass

def crawl_and_analyze():
    send_telegram_msg("⚙️ 엔진 가동 중 (문법 수정 완료 버전)")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # 사이트 접속
        send_telegram_msg("🌐 법원 사이트 접속 중...")
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        
        wait = WebDriverWait(driver, 25)
        
        # 검색 조건 입력
        send_telegram_msg("📍 천안지원 선택 중...")
        jiwon = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        Select(jiwon).select_by_visible_text("대전지방법원 천안지원")
        
        Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
        time.sleep(1)
        Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text("천안시 서북구")
        
        # 검색 실행
        driver.execute_script("goSrch();")
        send_telegram_msg("🔍 검색 중... 잠시만 기다려주세요.")
        time.sleep(8)
        
        # 결과 확인
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        
        if len(items) > 1:
            cols = items[1].find_elements(By.TAG_NAME, "td")
            case_no = cols[1].text.strip()
            
            # AI 분석 요청
            prompt = f"경매 사건번호 {case_no} 분석해줘. 수익성 점수(100점 만점)와 이유를 짧게."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            
            result_msg = f"✨ <b>분석 성공!</b>\n사건번호: {case_no}\n\n{response.text}"
            send_telegram_msg(result_msg)
        else:
            send_telegram_msg("📍 현재 검색 결과가 없습니다.")

    except Exception as e:
        send_telegram_msg(f"❌ 오류 발생: {str(e)[:150]}")
    
    finally:
        driver.quit()
        send_telegram_msg("🏁 작업 종료")

if __name__ == "__main__":
    crawl_and_analyze()
