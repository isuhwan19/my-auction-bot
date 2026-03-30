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
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def crawl_and_analyze():
    send_telegram_msg("🚀 **경매 비서 5차 가동 (직접 접속 모드)**")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 자동화 감지 방지
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    # 자동화 방지 스크립트
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    wait = WebDriverWait(driver, 30)
    
    try:
        # 1. 검색 페이지 직접 접속 (메인 페이지 거치지 않음)
        send_telegram_msg("🌐 경매 검색 페이지로 직접 이동 중...")
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        
        # 2. 페이지 로딩 확인 (idJiwon 요소가 뜰 때까지 최대 30초 대기)
        jiwon_element = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        send_telegram_msg("📍 법원 선택 리스트 확인 완료.")
        
        # 3. 천안지원 선택
        Select(jiwon_element).select_by_visible_text("대전지방법원 천안지원")
        time.sleep(2)
        
        # 4. 검색 버튼 클릭 (가장 안전한 버튼 클릭 방식)
        send_telegram_msg("🔍 검색 버튼을 누릅니다.")
        search_btn = driver.find_element(By.XPATH, "//a[@title='검색']")
        driver.execute_script("arguments[0].click();", search_btn)
        
        # 5. 결과 대기 (표가 로딩될 때까지)
        time.sleep(12)
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        
        if len(items) > 1:
            send_telegram_msg(f"✅ 총 {len(items)-1}건의 물건을 찾았습니다.")
            
            # 분석 데이터 추출 (첫 번째 물건)
            cols = items[1].find_elements(By.TAG_NAME, "td")
            case_no = cols[1].text.strip()
            addr = cols[3].text.replace('\n', ' ')
            
            # AI 분석 요청
            prompt = f"경매 사건 {case_no}, 주소 {addr}에 대해 투자 가치 점수(100점 만점)와 핵심 이유 한 줄을 한국어로 써줘."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            
            send_telegram_msg(f"🏠 <b>AI 분석 결과</b>\n사건번호: {case_no}\n{response.text}")
        else:
            send_telegram_msg("⚠️ 현재 조회된 경매 물건이 없습니다. (조건 확인 필요)")

    except Exception as e:
        # 에러 발생 시 로그 출력 및 알림
        print(f"상세 에러: {e}")
        send_telegram_msg(f"❌ 오류가 발생했습니다. (진단: {str(e)[:50]}...)")
    
    finally:
        driver.quit()
        send_telegram_msg("🏁 비서 업무 종료")

if __name__ == "__main__":
    crawl_and_analyze()
