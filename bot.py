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
    send_telegram_msg("🚀 **천안 경매 비서 최종 기동**")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # 1. 검색 메인 페이지 접속
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        time.sleep(3)
        
        # 2. 법원 선택 (천안지원만 선택하고 바로 검색)
        send_telegram_msg("⚙️ 법원 설정: 대전지방법원 천안지원")
        jiwon = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        Select(jiwon).select_by_visible_text("대전지방법원 천안지원")
        
        # 다른 필터(시/군/구)를 건너뛰고 바로 검색 버튼 클릭 (에러 방지)
        time.sleep(2)
        driver.execute_script("goSrch();")
        send_telegram_msg("🔍 검색 버튼 클릭 완료 (로딩 중...)")
        
        # 3. 결과 로딩 대기 및 확인
        time.sleep(10)
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        
        if len(items) > 1:
            # 상위 2개 물건만 리포트
            found_msg = f"✅ 총 {len(items)-1}개의 물건을 찾았습니다.\n상위 2개를 분석합니다."
            send_telegram_msg(found_msg)
            
            for i in range(1, min(len(items), 3)):
                cols = items[i].find_elements(By.TAG_NAME, "td")
                case_no = cols[1].text.strip()
                addr = cols[3].text.replace('\n', ' ')
                
                # Gemini AI 분석
                prompt = f"경매 물건 분석: 사건번호 {case_no}, 주소 {addr}. 투자 가치 점수(100점 만점)와 핵심 이유 한 줄만 써줘."
                response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
                
                send_telegram_msg(f"🏠 <b>물건 {i}</b>\n사건번호: {case_no}\n{response.text}")
        else:
            send_telegram_msg("⚠️ 검색 결과가 없습니다. (법원 사이트 응답 확인 필요)")

    except Exception as e:
        send_telegram_msg(f"❌ 중단 오류: {str(e)[:100]}")
    
    finally:
        driver.quit()
        send_telegram_msg("🏁 비서 업무 종료")

if __name__ == "__main__":
    crawl_and_analyze()
