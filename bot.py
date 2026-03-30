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

def crawl_and_analyze():
    send_telegram_msg("🕵️ **스텔스 모드로 법원 잠입 중...**")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # [강력 추가] 자동화 흔적 지우기
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # [강력 추가] 웹드라이버 속성 제거
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    try:
        # 법원 사이트는 메인부터 천천히 들어가야 합니다.
        driver.get("https://www.courtauction.go.kr/")
        time.sleep(7)
        
        # 검색 페이지로 우회 접속
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        time.sleep(10)
        
        # 검색 조건 설정
        wait = WebDriverWait(driver, 20)
        jiwon = wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
        Select(jiwon).select_by_visible_text("대전지방법원 천안지원")
        
        # 사람처럼 보이게 랜덤 대기
        time.sleep(3)
        driver.execute_script("goSrch();")
        
        time.sleep(10)
        items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
        
        if len(items) > 1:
            cols = items[1].find_elements(By.TAG_NAME, "td")
            case_no = cols[1].text.strip()
            addr = cols[3].text.replace('\n', ' ')
            
            prompt = f"경매 {case_no}, 주소 {addr} 분석 및 투자 가치 점수."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            send_telegram_msg(f"🏠 **드디어 성공!**\n{response.text}")
        else:
            send_telegram_msg("📍 입장은 했으나 물건을 찾지 못했습니다.")

    except Exception as e:
        send_telegram_msg(f"❌ 보안망을 뚫지 못했습니다.")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_and_analyze()
