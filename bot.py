import os
import time
import requests
from google import genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- 환경 설정 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def crawl_km_madang():
    send_telegram_msg("🏃 **경매마당으로 목표 변경! 데이터 수집 시작**")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # 천안 지역 경매 물건 검색 결과로 직접 접속 (예시 URL)
        # 경매마당에서 '천안' 검색 필터를 적용한 주소를 사용합니다.
        search_url = "https://www.kyungmaemadang.com/auction/list?address=%EC%B2%9C%EC%95%88"
        driver.get(search_url)
        time.sleep(7) # 결과 로딩 대기
        
        # 물건 리스트 찾기 (실제 사이트의 태그 구조에 맞춰 수정 필요)
        # 경매마당의 경우 클래스명이 'AuctionItem_container' 등으로 구성됨
        items = driver.find_elements(By.CSS_SELECTOR, "div[class*='AuctionItem_container']")
        
        if items:
            send_telegram_msg(f"✅ 경매마당에서 {len(items)}개의 물건을 찾았습니다!")
            
            # 첫 번째 물건 정보 추출
            title = items[0].text.split('\n')[0] # 예: 아파트 이름 등
            
            # Gemini 분석
            prompt = f"경매 물건 '{title}'에 대해 천안 지역 부동산 전망을 섞어서 짧은 투자평을 써줘."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            
            send_telegram_msg(f"🏠 <b>경매마당 분석</b>\n물건명: {title}\n{response.text}")
        else:
            # 만약 못 찾았다면 화면 텍스트 확인
            body_text = driver.find_element(By.TAG_NAME, "body").text[:100]
            send_telegram_msg(f"📍 물건 리스트를 읽지 못했습니다. (원인: {body_text})")

    except Exception as e:
        send_telegram_msg(f"❌ 경매마당 접속 실패: {str(e)[:50]}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_km_madang()
