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

# --- 2. AI 분석 함수 ---
def analyze_with_gemini(property_data):
    # 테스트를 위해 점수를 후하게 달라고 프롬프트에 명시했습니다.
    prompt = f"너는 경매 전문가야. 다음 데이터를 분석해서 JSON으로 응답해줘. 특히 profit_score는 30점 이상으로 줘: {property_data}"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return clean_json
    except:
        return json.dumps({"risk": "확인불가", "profit_score": 50, "comment": "분석 오류 발생시 테스트용 점수 부여"})

# --- 3. 텔레그램 알림 발송 ---
def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"텔레그램 발송 실패: {e}")

# --- 4. 메인 크롤러 로직 ---
def crawl_and_analyze():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 15)
    
    try:
        driver.get("https://www.courtauction.go.kr/")
        time.sleep(2)
        
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "indexFrame")))
        except: pass
            
        wait.until(EC.element_to_be_clickable((By.ID, "menu01"))).click()
        time.sleep(2)
        
        sigu_list = ["천안시 서북구", "천안시 동남구"]
        high_profit_items = []
        
        for sigu in sigu_list:
            # 법원 선택 로직 안정화
            wait.until(EC.presence_of_element_located((By.ID, "idJiwon")))
            Select(driver.find_element(By.ID, "idJiwon")).select_by_visible_text("대전지방법원 천안지원")
            Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
            time.sleep(1)
            Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text(sigu)
            
            driver.find_element(By.CSS_SELECTOR, "a.btn_next").click()
            time.sleep(3)
            
            items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
            
            # 검색 결과가 있을 경우 상위 2개 분석
            for i in range(1, min(len(items), 3)):
                cols = items[i].find_elements(By.TAG_NAME, "td")
                if len(cols) > 1:
                    case_no = cols[1].text.strip()
                    basic_info = cols[3].text
                    
                    analysis_res = analyze_with_gemini(f"{case_no} {basic_info}")
                    res_json = json.loads(analysis_res)
                    
                    # [수정 포인트] 점수 기준을 30점으로 낮춤
                    if res_json.get("profit_score", 0) >= 30:
                        high_profit_items.append({"sigu": sigu, "case_no": case_no, "analysis": res_json})
            
            # 다음 검색을 위해 리스트 초기화
            driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
            time.sleep(2)
            try: driver.switch_to.frame("indexFrame")
            except: pass

        if high_profit_items:
            for item in high_profit_items:
                msg = f"🏠 <b>[{item['sigu']}] 테스트 분석 완료</b>\n" \
                      f"사건번호: {item['case_no']}\n" \
                      f"AI점수: {item['analysis'].get('profit_score')}점\n" \
                      f"내용: {item['analysis'].get('comment')}"
                send_telegram_msg(msg)
        else:
            send_telegram_msg("⚠️ 오늘 분석된 물건 중 30점을 넘는 것이 없습니다.")

    except Exception as e:
        send_telegram_msg(f"❌ 오류 발생: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    # 시작하자마자 텔레그램으로 인사부터 합니다. (연결 확인용)
    send_telegram_msg("🤖 천안 경매 비서 가동 테스트를 시작합니다!")
    crawl_and_analyze()
