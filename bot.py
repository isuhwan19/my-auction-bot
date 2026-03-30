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
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def send_telegram_photo(photo_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"photo": photo})

def crawl_and_analyze():
    send_telegram_msg("🔍 **비서가 현장(법원)에 도착했습니다. 확인 중...**")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # 한국인인 척 하기 위한 헤더 설정
    options.add_argument("lang=ko_KR")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # 1. 메인 페이지부터 접속 (세션 쿠키 생성)
        driver.get("https://www.courtauction.go.kr/")
        time.sleep(5)
        
        # 2. 부동산 검색 메뉴로 이동
        send_telegram_msg("🌐 부동산 경매 검색 페이지로 진입 시도...")
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        time.sleep(5)
        
        # [중요] 화면 캡처 (비서가 지금 뭘 보고 있는지 기록)
        driver.save_screenshot("current_screen.png")
        
        # 3. 법원 선택창 확인
        try:
            jiwon_element = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
            send_telegram_msg("📍 천안지원 선택 버튼을 찾았습니다!")
            Select(jiwon_element).select_by_visible_text("대전지방법원 천안지원")
        except:
            send_telegram_msg("❓ 버튼을 못 찾겠어요. 현재 화면 사진을 보냅니다.")
            send_telegram_photo("current_screen.png")
            return # 여기서 중단

        # 4. 검색 실행
        driver.execute_script("goSrch();")
        time.sleep(10)
        
        # 5. 결과 파싱
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        if len(items) > 1:
            cols = items[1].find_elements(By.TAG_NAME, "td")
            case_no = cols[1].text.strip()
            addr = cols[3].text.replace('\n', ' ')
            
            prompt = f"경매 사건 {case_no}, 주소 {addr} 분석. 투자 점수와 핵심 한줄평."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            send_telegram_msg(f"🏠 <b>분석 성공!</b>\n사건번호: {case_no}\n{response.text}")
        else:
            send_telegram_msg("📍 검색 결과가 비어 있습니다. (현재 경매 물건 없음)")

    except Exception as e:
        send_telegram_msg(f"❌ 돌발 상황 발생: {str(e)[:50]}")
    finally:
        driver.quit()
        send_telegram_msg("🏁 비서 업무 종료 (로그 확인 완료)")

if __name__ == "__main__":
    crawl_and_analyze()
