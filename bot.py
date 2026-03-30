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
# 임포트 오류를 방지하기 위해 상위 예외 클래스를 가져옵니다.
from selenium.common import exceptions

# --- 환경 설정 ---
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
    send_telegram_msg("🚀 **천안 경매 비서 가동 (라이브러리 최적화)**")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 25)
    
    try:
        # 1. 상세 검색 페이지 접속
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        time.sleep(5)
        
        # 2. 법원 선택
        send_telegram_msg("📍 대전지방법원 천안지원 선택 중...")
        jiwon = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        Select(jiwon).select_by_visible_text("대전지방법원 천안지원")
        time.sleep(2)
        
        # 3. 검색 버튼 직접 클릭
        send_telegram_msg("🔍 검색 버튼 클릭 시도...")
        search_btn = driver.find_element(By.XPATH, "//a[contains(@onclick, 'goSrch')]")
        driver.execute_script("arguments[0].click();", search_btn)
        
        # 4. 혹시 모를 팝업창(Alert) 확인 및 닫기 (예외처리 강화)
        time.sleep(3)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            send_telegram_msg(f"⚠️ 법원 사이트 메시지: {alert_text}")
            alert.accept()
        except:
            # 팝업이 없으면 자연스럽게 넘어갑니다.
            pass
            
        # 5. 결과 로딩 대기
        send_telegram_msg("⏳ 결과 데이터를 기다리는 중 (15초)...")
        time.sleep(15)
        
        # 6. 결과 파싱
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        
        if len(items) > 1:
            count = len(items) - 1
            send_telegram_msg(f"✅ {count}건의 물건을 발견했습니다!")
            
            # 첫 번째 물건 분석
            cols = items[1].find_elements(By.TAG_NAME, "td")
            case_no = cols[1].text.strip()
            addr = cols[3].text.replace('\n', ' ')
            
            # AI 분석
            prompt = f"경매 사건번호 {case_no}, 주소 {addr} 분석. 투자 점수와 핵심 한줄평을 한국어로 써줘."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            
            send_telegram_msg(f"🏠 <b>AI 분석</b>\n사건번호: {case_no}\n{response.text}")
        else:
            page_text = driver.find_element(By.TAG_NAME, "body").text[:50]
            send_telegram_msg(f"⚠️ 결과가 없습니다. (현재 화면: {page_text})")

    except Exception as e:
        send_telegram_msg(f"❌ 오류 발생: {str(e)[:150]}")
    
    finally:
        driver.quit()
        send_telegram_msg("🏁 비서 업무 종료")

if __name__ == "__main__":
    crawl_and_analyze()
