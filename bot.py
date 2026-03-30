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
    prompt = f"너는 경매 전문가야. 다음 데이터를 분석해서 JSON으로 응답해줘. 특히 profit_score는 30점 이상으로 줘: {property_data}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return clean_json
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
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # [핵심 수정] 프레임을 거치지 않고 검색 직접 주소로 접속
        driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
        time.sleep(3)
        
        sigu_list = ["천안시 서북구", "천안시 동남구"]
        high_profit_items = []
        
        for sigu in sigu_list:
            # 요소가 나타날 때까지 확실히 대기
            wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
            
            Select(driver.find_element(By.ID, "idJiwon")).select_by_visible_text("대전지방법원 천안지원")
            Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
            time.sleep(1)
            Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text(sigu)
            
            # 검색 버튼 클릭 (더 정확한 셀렉터 사용)
            search_btn = driver.find_element(By.CSS_SELECTOR, "a.btn_next")
            driver.execute_script("arguments[0].click();", search_btn)
            time.sleep(4)
            
            items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
            
            # 검색 결과가 있는지 확인
            if len(items) <= 1:
                continue

            for i in range(1, min(len(items), 3)):
                cols = items[i].find_elements(By.TAG_NAME, "td")
                if len(cols) > 5:
                    case_no = cols[1].text.strip()
                    address = cols[3].text.replace('\n', ' ')
                    price_info = cols[4].text.replace('\n', ' ')
                    
                    # AI에게 넘길 데이터 조합
                    full_data = f"사건번호: {case_no}, 주소: {address}, 가격: {price_info}"
                    
                    analysis_res = analyze_with_gemini(full_data)
                    res_json = json.loads(analysis_res)
                    
                    if res_json.get("profit_score", 0) >= 30:
                        high_profit_items.append({"sigu": sigu, "case_no": case_no, "analysis": res_json})
            
            # 다시 검색 페이지로 이동
            driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
            time.sleep(2)

        if high_profit_items:
            for item in high_profit_items:
                msg = f"🏠 <b>[{item['sigu']}] 분석 결과</b>\n" \
                      f"사건번호: {item['case_no']}\n" \
                      f"AI점수: {item['analysis'].get('profit_score')}점\n" \
                      f"내용: {item['analysis'].get('comment')}"
                send_telegram_msg(msg)
        else:
            send_telegram_msg("📍 오늘 천안 지역에 분석 가능한 물건 리스트가 비어있거나 조건에 맞는 물건이 없습니다.")

    except Exception as e:
        send_telegram_msg(f"❌ 크롤링 중단 오류: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    send_telegram_msg("🤖 천안 경매 비서 2차 가동 테스트(우회 접속) 시작!")
    crawl_and_analyze()
