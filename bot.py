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
    send_telegram_msg("🚀 **경매 비서 4차 가동 (최종 진단)**")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # [수정] 메인 페이지부터 접속하여 쿠키를 생성합니다.
        send_telegram_msg("🌐 법원 사이트 접속 시도...")
        driver.get("https://www.courtauction.go.kr/")
        time.sleep(5)
        
        # [수정] 검색 페이지로 이동하는 자바스크립트 실행
        driver.execute_script("util_menu_click('RetrieveRealEstMainList.action');")
        time.sleep(5)
        
        # 현재 페이지 제목 확인 (보안 차단 여부 체크)
        print(f"현재 페이지 제목: {driver.title}")
        
        # 법원 선택
        send_telegram_msg("📍 천안지원 설정 시작...")
        # idJiwon 요소가 나타날 때까지 확실히 대기
        jiwon_element = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        Select(jiwon_element).select_by_visible_text("대전지방법원 천안지원")
        
        # 검색 실행
        send_telegram_msg("🔍 물건 검색 중...")
        driver.execute_script("goSrch();")
        time.sleep(10)
        
        # 결과 파싱
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        print(f"검색 결과 행 수: {len(items)}")

        if len(items) > 1:
            send_telegram_msg(f"✅ {len(items)-1}건 발견! 분석 리포트를 작성합니다.")
            
            # 첫 번째 물건 데이터 가져오기
            cols = items[1].find_elements(By.TAG_NAME, "td")
            case_no = cols[1].text.strip()
            addr = cols[3].text.replace('\n', ' ')
            
            # Gemini AI 분석
            prompt = f"경매 사건번호 {case_no}, 주소 {addr}에 대해 투자 가치 점수와 핵심 한줄평을 써줘."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            
            report = f"🏠 <b>AI 분석 보고서</b>\n사건번호: {case_no}\n{response.text}"
            send_telegram_msg(report)
        else:
            # 결과가 없을 때의 화면 텍스트를 로그에 남김
            print("결과 없음. 현재 화면 텍스트:", driver.find_element(By.TAG_NAME, "body").text[:200])
            send_telegram_msg("📍 현재 천안지원에 진행 중인 경매 물건이 없습니다.")

    except Exception as e:
        error_log = str(e)
        print(f"상세 에러 로그: {error_log}")
        send_telegram_msg(f"❌ 작업 중 오류가 발생했습니다. (로그 확인 필요)")
    
    finally:
        driver.quit()
        send_telegram_msg("🏁 비서 업무 종료")

if __name__ == "__main__":
    crawl_and_analyze()
