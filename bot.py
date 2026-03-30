import os
import time
import requests
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. 환경 설정 (GitHub Secrets에서 가져옴) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Gemini 초기화
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. AI 전문가 분석 프롬프트 (가장 중요) ---
def analyze_with_gemini(property_data):
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    prompt = f"""
    너는 대한민국 부동산 경매 전문 변호사이자 투자 컨설턴트야. 
    아래 수집된 경매 물건 데이터를 바탕으로 정밀한 권리분석과 수익성을 평가해줘.
    
    데이터: {property_data}
    
    분석 지침:
    1. **말소기준권리:** 등기부 요약에서 가장 앞선 근저당, 압류 등을 찾아 '말소기준권리'로 설정해.
    2. **대항력:** 임차인의 전입일이 말소기준권리보다 빠른 '선순위'인지 확인해. 선순위라면 배당요구 여부와 보증금 액수를 파악해 낙찰자가 '인수'해야 할 금액을 계산해.
    3. **수익성 점수 (1~100):** 권리상 안전(후순위 임차인, 인수금 없음)하고 시세(감정가) 대비 최저가가 낮으면 높은 점수를 줘. 선순위 임차인 보증금 미상이거나 위험한 권리가 있으면 0점 처리해.
    4. **용도 구분:** 주거용(아파트, 빌라)과 상업용(오피스텔)의 특성에 맞춰 분석해.
    
    출력 형식 (JSON만 출력):
    {{ "risk": "안전/주의/위험", "acquisition_cost": "00원", "profit_score": 00, "comment": "..." }}
    """
    
    try:
        response = model.generate_content(prompt)
        # JSON 텍스트만 추출하는 로직 (Gemini 출력에 ```json 등이 붙을 수 있음)
        result_text = response.text.replace('```json', '').replace('```', '').strip()
        return result_text
    except Exception as e:
        return f'{{"risk": "오류", "comment": "{str(e)}"}}'

# --- 3. 텔레그램 알림 발송 ---
def send_telegram_msg(msg):
    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# --- 4. 법원 경매 상세 크롤러 (천안시 전체) ---
def crawl_and_analyze():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # 화면 없이 실행 (서버용)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get("https://www.courtauction.go.kr/")
        time.sleep(2)
        driver.switch_to.frame("indexFrame")
        driver.find_element(By.ID, "menu01").click() # 경매물건 메뉴
        time.sleep(1)
        
        # 법원 선택
        Select(driver.find_element(By.ID, "idJiwon")).select_by_visible_text("대전지방법원 천안지원")
        Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
        time.sleep(0.5)
        
        # 서북구, 동남구 반복 검색
        sigu_list = ["천안시 서북구", "천안시 동남구"]
        high_profit_items = []
        
        for sigu in sigu_list:
            Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text(sigu)
            driver.find_element(By.CSS_SELECTOR, "a.btn_next").click() # 검색
            time.sleep(2)
            
            # 결과 테이블
            items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
            
            for item in items[1:6]: # 성능을 위해 각 구별 상위 5개만 테스트
                cols = item.find_elements(By.TAG_NAME, "td")
                if len(cols) > 1:
                    # 상세 페이지 진입을 위해 사건번호 클릭
                    case_link = cols[1].find_element(By.TAG_NAME, "a")
                    case_no = case_link.text.strip()
                    case_link.click()
                    time.sleep(2)
                    
                    # --- 상세 페이지 데이터 스크래핑 ---
                    # 1. 임차인 현황
                    tenant_text = "임차인 현황 없음"
                    try:
                        tenant_tab = driver.find_element(By.XPATH, "//a[contains(text(), '임차인현황')]")
                        tenant_tab.click()
                        time.sleep(1)
                        tenant_text = driver.find_element(By.CSS_SELECTOR, "table.Ltbl_list").text
                    except: pass
                    
                    # 2. 등기부 요약
                    registry_text = "등기부 요약 없음"
                    try:
                        registry_tab = driver.find_element(By.XPATH, "//a[contains(text(), '등기부현황')]")
                        registry_tab.click()
                        time.sleep(1)
                        registry_text = driver.find_element(By.CSS_SELECTOR, "table.Ltbl_list").text
                    except: pass
                    
                    # 기본 정보
                    basic_data = cols[3].text + " " + cols[4].text # 소재지, 가격
                    
                    # 전체 데이터 통합
                    full_property_data = f"사건번호:{case_no}, 기본:{basic_data}, [임차인현황]:{tenant_text}, [등기부현황]:{registry_text}"
                    
                    # Gemini 분석 실행
                    analysis_result = analyze_with_gemini(full_property_data)
                    import json
                    analysis_json = json.loads(analysis_result)
                    
                    # 수익성 점수가 70점 이상인 것만 저장
                    if analysis_json.get("profit_score", 0) >= 70:
                        high_profit_items.append({
                            "case_no": case_no,
                            "sigu": sigu,
                            "analysis": analysis_json
                        })
                    
                    # 리스트로 돌아가기
                    driver.execute_script("window.history.go(-1)")
                    time.sleep(2)
                    # 프레임 다시 전환 필요
                    driver.switch_to.frame("indexFrame")
            
            # 다음 구 검색을 위해 조건 설정 페이지로 이동
            driver.execute_script("window.history.go(-1)")
            time.sleep(2)
            driver.switch_to.frame("indexFrame")

        # --- 최종 알림 발송 ---
        if high_profit_items:
            for item in high_profit_items:
                msg = f"""
🏠 **[천안 경매 비서] 수익 물건 발견!**

📍 **구역:** {item['sigu']}
⚖️ **사건번호:** {item['case_no']}
🛡️ **위험도:** {item['analysis']['risk']}
💰 **인수금:** {item['analysis']['acquisition_cost']}
📈 **수익점수:** {item['analysis']['profit_score']}점

📝 **AI 한줄평:**
{item['analysis']['comment']}
                """
                send_telegram_msg(msg)
        else:
            send_telegram_msg("오늘 천안 지역에는 조건에 맞는 수익 물건이 없습니다.")

    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_and_analyze()
