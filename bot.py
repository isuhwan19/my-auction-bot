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
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu") # 리소스 절약
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15) # 대기 시간 최적화
    
    try:
        # 1. 검색 페이지 바로 접속
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        
        # 2. 법원 및 지역 선택 (천안 서북구만 먼저 테스트)
        wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        Select(driver.find_element(By.ID, "idJiwon")).select_by_visible_text("대전지방법원 천안지원")
        Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
        time.sleep(1)
        Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text("천안시 서북구")
        
        # 3. 검색 버튼 클릭
        driver.execute_script("goSrch();") # 자바스크립트 직접 실행으로 속도 향상
        time.sleep(5)
        
        # 4. 결과 파싱
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        print(f"검색 결과 행 수: {len(items)}")
        
        if len(items) > 1:
            # 첫 번째 물건만 샘플로 분석 (성공 여부 확인용)
            cols = items[1].find_elements(By.TAG_NAME, "td")
            case_no = cols[1].text.strip()
            msg = f"✅ <b>천안 경매물건 발견!</b>\n사건번호: {case_no}\n분석을 시작합니다..."
            send_telegram_msg(msg)
            
            # AI 분석 (간략하게)
            prompt = f"사건번호 {case_no} 분석해줘. 점수와 한줄평만."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            send_telegram_msg(f"🤖 <b>AI 분석 결과</b>\n{response.text}")
        else:
            send_telegram_msg("📍 현재 천안 서북구에 진행 중인 경매 물건이 리스트에 없습니다.")

    except Exception as e:
        send_telegram_msg(f"❌ 오류 발생: {str(e)[:100]}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_and_analyze()
