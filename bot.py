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

def analyze_with_gemini(property_data):
    prompt = f"경매 전문가로서 다음 데이터를 분석해 JSON 응답해줘. 점수는 30점 이상으로: {property_data}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text.replace('```json', '').replace('```', '').strip()
    except:
        return json.dumps({"risk": "확인불가", "profit_score": 50, "comment": "분석 오류"})

def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, data=payload)

def crawl_and_analyze():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 30) # 대기 시간을 30초로 대폭 상향
    
    try:
        # 직접 검색 페이지 접속
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        time.sleep(5) # 초기 로딩 대기
        
        sigu_list = ["천안시 서북구", "천안시 동남구"]
        high_profit_items = []
        
        for sigu in sigu_list:
            print(f"--- {sigu} 검색 시작 ---")
            
            # 검색 조건 입력
            wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
            Select(driver.find_element(By.ID, "idJiwon")).select_by_visible_text("대전지방법원 천안지원")
            Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
            time.sleep(2)
            Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text(sigu)
            
            # 검색 버튼 클릭 (엔터 키 입력 방식 병행)
            search_btn = driver.find_element(By.CSS_SELECTOR, "a.btn_next")
            driver.execute_script("arguments[0].click();", search_btn)
            
            print("검색 버튼 클릭 완료, 결과 대기 중...")
            time.sleep(7) # 결과 로딩을 위해 충분히 대기
            
            # 결과 테이블 확인
            items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
            print(f"발견된 행(row) 개수: {len(items)}")

            if len(items) <= 1:
                print(f"{sigu} 결과 없음. 화면 확인용 로그 남김.")
                continue

            for i in range(1, min(len(items), 3)):
                cols = items[i].find_elements(By.TAG_NAME, "td")
                if len(cols) > 5:
                    case_no = cols[1].text.strip()
                    address = cols[3].text.replace('\n', ' ')
                    
                    analysis_res = analyze_with_gemini(f"{case_no} {address}")
                    res_json = json.loads(analysis_res)
                    
                    if res_json.get("profit_score", 0) >= 30:
                        high_profit_items.append({"sigu": sigu, "case_no": case_no, "analysis": res_json})
            
            # 다음 검색 전 초기화
            driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
            time.sleep(3)

        if high_profit_items:
            for item in high_profit_items:
                msg = f"🏠 <b>[{item['sigu']}] 분석 결과</b>\n사건번호: {item['case_no']}\n점수: {item['analysis'].get('profit_score')}점\n내용: {item['analysis'].get('comment')}"
                send_telegram_msg(msg)
        else:
            send_telegram_msg("📍 검색 결과 테이블을 읽지 못했거나 조건에 맞는 물건이 없습니다. (로그 확인 필요)")

    except Exception as e:
        send_telegram_msg(f"❌ 실행 중 오류: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    send_telegram_msg("🔍 3차 정밀 진단 테스트 시작!")
    crawl_and_analyze()
