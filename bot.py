import os
import time
import requests
import json
from google import genai  # 최신 라이브러리 방식
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. 환경 설정 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 최신 제미나이 클라이언트 초기화
client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. AI 분석 함수 ---
def analyze_with_gemini(property_data):
    prompt = f"""
    너는 대한민국 부동산 경매 전문 변호사이자 투자 컨설턴트야. 
    아래 수집된 경매 물건 데이터를 바탕으로 정밀한 권리분석과 수익성을 평가해줘.
    
    데이터: {property_data}
    
    분석 지침:
    1. 말소기준권리 설정 및 대항력 확인 (선순위 임차인 여부)
    2. 수익성 점수 (1~100): 안전하고 시세 대비 저렴하면 높은 점수. 위험하면 0점.
    
    출력 형식 (반드시 아래 JSON 형식만 출력):
    {{ "risk": "안전/주의/위험", "acquisition_cost": "0원", "profit_score": 85, "comment": "분석 내용" }}
    """
    
    try:
        # 무료 등급에서 가장 안정적인 flash 모델 사용
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        # JSON 텍스트 정제
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return clean_json
    except Exception as e:
        return json.dumps({"risk": "오류", "profit_score": 0, "comment": str(e)})

# --- 3. 텔레그램 알림 발송 ---
def send_telegram_msg(msg):
    # URL 마크다운 에러 수정 완료
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# --- 4. 메인 크롤러 로직 ---
def crawl_and_analyze():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 법원 사이트 접속 (URL 에러 수정 완료)
        driver.get("https://www.courtauction.go.kr/")
        time.sleep(3)
        
        driver.switch_to.frame("indexFrame")
        driver.find_element(By.ID, "menu01").click() # 경매물건 메뉴
        time.sleep(1)
        
        sigu_list = ["천안시 서북구", "천안시 동남구"]
        high_profit_items = []
        
        for sigu in sigu_list:
            # 매번 검색 조건 초기화 후 재검색
            Select(driver.find_element(By.ID, "idJiwon")).select_by_visible_text("대전지방법원 천안지원")
            Select(driver.find_element(By.ID, "idSido")).select_by_visible_text("충청남도")
            time.sleep(0.5)
            Select(driver.find_element(By.ID, "idSigu")).select_by_visible_text(sigu)
            
            driver.find_element(By.CSS_SELECTOR, "a.btn_next").click() # 검색 버튼
            time.sleep(2)
            
            items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
            
            # 각 구별 상위 3개 물건만 정밀 분석 (시간/한도 고려)
            for i in range(1, min(len(items), 4)):
                try:
                    # 매 루프마다 다시 요소를 찾아야 에러가 안 남
                    current_items = driver.find_elements(By.CSS_SELECTOR, "table.Ltbl_list tr")
                    cols = current_items[i].find_elements(By.TAG_NAME, "td")
                    
                    case_no = cols[Case_No_Col := 1].text.strip()
                    basic_info = cols[3].text.replace('\n', ' ')
                    
                    # 상세 페이지 진입
                    cols[1].find_element(By.TAG_NAME, "a").click()
                    time.sleep(2)
                    
                    # 임차인/등기부 데이터 수집
                    detail_text = driver.find_element(By.TAG_NAME, "body").text[:2000] # 상단 데이터 위주
                    
                    # AI 분석
                    analysis_res = analyze_with_gemini(f"{case_no} {basic_info} {detail_text}")
                    res_json = json.loads(analysis_res)
                    
                    if res_json.get("profit_score", 0) >= 70:
                        high_profit_items.append({
                            "sigu": sigu, "case_no": case_no, "analysis": res_json
                        })
                    
                    driver.back() # 리스트로 돌아가기
                    time.sleep(2)
                    driver.switch_to.frame("indexFrame")
                except Exception as e:
                    print(f"항목 분석 중 스킵: {e}")
                    continue
            
            # 다음 구 검색을 위해 초기화 페이지 이동
            driver.get("https://www.courtauction.go.kr/RetrieveRealEstMainList.action")
            time.sleep(2)
            driver.switch_to.frame("indexFrame")

        # 결과 발송
        if high_profit_items:
            for item in high_profit_items:
                message = f"🏠 <b>[{item['sigu']}] 추천 물건</b>\n\n" \
                          f"사건번호: {item['case_no']}\n" \
                          f"위험도: {item['analysis']['risk']}\n" \
                          f"수익점수: {item['analysis']['profit_score']}점\n" \
                          f"설명: {item['analysis']['comment']}"
                send_telegram_msg(message)
        else:
            send_telegram_msg("오늘 천안 지역에 추천할 만한 수익 물건이 없습니다.")

    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_and_analyze()
