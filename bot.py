import os
import time
import requests
from google import genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, data=payload)

def crawl_and_analyze():
    send_telegram_msg("⚙️ 엔진 가동 (검색 로직 강화 버전)")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        wait = WebDriverWait(driver, 20)
        
        # 1. 지역 선택
        send_telegram_msg("📍 천안지원 상세 검색 설정 중...")
        jiwon = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        Select(jiwon).select_by_visible_text("대전지방법원 천안지원")
        
        # 시도/시군구 선택 시 약간의 시간차를 둡니다.
        time.sleep(1)
        Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
        time.sleep(1)
        Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text("천안시 서북구")
        
        # 2. 검색 버튼 클릭 (강력한 방식 사용)
        send_telegram_msg("🔍 검색 버튼을 누릅니다.")
        search_btn = driver.find_element(By.CSS_SELECTOR, "a.btn_next")
        # 자바스크립트로 직접 호출 + 엔터키 입력 병행
        driver.execute_script("goSrch();") 
        time.sleep(10) # 검색 결과 로딩을 위해 충분히 대기
        
        # 3. 결과 테이블 확인
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        row_count = len(items)
        
        if row_count > 1:
            send_telegram_msg(f"✅ 물건을 찾았습니다! (검색된 행: {row_count-1}건)")
            cols = items[1].find_elements(By.TAG_NAME, "td")
            case_no = cols[1].text.strip()
            addr = cols[3].text.replace('\n', ' ')
            
            # AI 분석
            prompt = f"경매 사건번호 {case_no}, 주소 {addr} 분석해줘. 점수와 이유를 아주 짧게."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            
            send_telegram_msg(f"🤖 <b>AI 분석 결과</b>\n사건번호: {case_no}\n{response.text}")
        else:
            # 결과가 없을 때 현재 페이지의 텍스트를 일부 보냅니다 (진단용)
            body_text = driver.find_element(By.TAG_NAME, "body").text[:100]
            send_telegram_msg(f"📍 검색 결과가 0건입니다.\n(페이지 상태: {body_text}...)")

    except Exception as e:
        send_telegram_msg(f"❌ 오류: {str(e)[:100]}")
    
    finally:
        driver.quit()
        send_telegram_msg("🏁 모든 작업이 완료되었습니다.")

if __name__ == "__main__":
    crawl_and_analyze()
