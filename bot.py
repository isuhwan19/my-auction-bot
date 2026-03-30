import os
import time
import requests
import json
from google import genai  # 최신 라이브러리 사용
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

# --- 2. AI 분석 함수 ---
def analyze_with_gemini(property_data):
    prompt = f"너는 경매 전문가야. 다음 데이터를 분석해서 JSON으로 응답해줘: {property_data}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return clean_json
    except:
        return json.dumps({"risk": "확인불가", "profit_score": 0, "comment": "분석 오류"})

# --- 3. 텔레그램 알림 발송 (URL 마크다운 완전 제거) ---
def send_telegram_msg(msg):
    # 괄호와 링크 형식을 완전히 제거한 순수 주소입니다.
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, data=payload)

# --- 4. 메인 크롤러 로직 ---
def crawl_and_analyze():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 보안 회피를 위해 유저 에이전트 추가 (중요!)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 15) # 요소를 기다리는 시간 설정
    
    try:
        driver.get("https://www.courtauction.go.kr/")
        
        # [수정] 프레임이 나타날 때까지 기다린 후 전환
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "indexFrame")))
        except:
            # 만약 indexFrame이 없으면 이미 메인 페이지일 수 있음
            pass
            
        # 경매물건 메뉴 클릭
        wait.until(EC.element_to_be_clickable((By.ID, "menu01"))).click()
        time.sleep(2)
        
        sigu_list = ["천안시 서북구", "천안시 동남구"]
        high_profit_items = []
        
        for sigu in sigu_list:
            # 법원/지역 선택 (매번 프레임 안에서 요소 대기)
            Select(wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))).select_by_visible_text("대전지방법원 천안지원")
            Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
            time.sleep(0.5)
            Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text(sigu)
            
            driver.find_element(By.CSS_SELECTOR, "a.btn_next").click()
            time.sleep(2)
            
            items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
            if len(items) > 1:
                # 상위 1개만 샘플 분석 (테스트용)
                cols = items[1].find_elements(By.TAG_NAME, "td")
                case_no = cols[1].text.strip()
                basic_info = cols[3].text
                
                analysis_res = analyze_with_gemini(f"{case_no} {basic_info}")
                res_json = json.loads(analysis_res)
                
                high_profit_items.append({"sigu": sigu, "case_no": case_no, "analysis": res_json})
            
            # 다음 검색을 위해 검색 메인으로 이동
            driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
            time.sleep(2)
            try: driver.switch_to.frame("indexFrame")
            except: pass

        # 알림 전송
        if high_profit_items:
            for item in high_profit_items:
                msg = f"🏠 <b>[{item['sigu']}] 경매 분석</b>\n사건번호: {item['case_no']}\n점수: {item['analysis'].get('profit_score')}점\n내용: {item['analysis'].get('comment')}"
                send_telegram_msg(msg)
        else:
            send_telegram_msg("오늘 분석된 물건이 없습니다.")

    except Exception as e:
        send_telegram_msg(f"❌ 크롤링 중 오류 발생: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    # 1. 먼저 텔레그램 연결 테스트 (이게 오면 텔레그램 설정은 OK!)
    send_telegram_msg("🚀 천안 경매 비서 가동 테스트 시작!")
    
    # 2. 원래 크롤링 실행
    crawl_and_analyze()
