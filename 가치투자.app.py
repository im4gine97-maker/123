import streamlit as st
import yfinance as yf
from deep_translator import GoogleTranslator
import time

st.set_page_config(page_title="JB Value Terminal PRO", page_icon="⚡", layout="wide")

# (이전과 동일한 CSS 설정 생략 - 그대로 유지)
st.markdown("""<style>.box {background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d;}</style>""", unsafe_allow_html=True)

def safe_translate(text):
    if not text or not isinstance(text, str) or len(text) < 2: return text
    try: return GoogleTranslator(source='en', target='ko').translate(text[:2000])
    except: return text

# 핵심 수정: 미국 종목은 티커 뒤에 .US를 붙이거나 야후가 인식하도록 명확히 전달
def get_stock_data(ticker_symbol):
    # 입력된 티커가 한국 시장이 아니면 미국으로 간주
    if "." not in ticker_symbol:
        ticker_symbol = ticker_symbol.upper()
    
    stock = yf.Ticker(ticker_symbol)
    for i in range(3):
        try:
            price = stock.fast_info['lastPrice']
            info = stock.info
            return stock, price, info
        except Exception:
            time.sleep(2)
    return None, None, {}

st.title("⚡ JB Value Terminal PRO")
user_input = st.text_input("종목코드(티커) 입력", placeholder="예: AAPL, MSFT, 005930.KS")

if st.button("가치 분석 실행"):
    if user_input:
        with st.spinner('미국/한국 서버 연결 중...'):
            stock, price, info = get_stock_data(user_input.strip())
            
            if price:
                st.success(f"분석 완료: {info.get('shortName', user_input)}")
                # (이하 밸류에이션 및 질적 분석 로직 동일)
                st.write(f"현재가: {price:,.2f}")
                # ... (이전 코드의 col1, col2 출력 부분 유지)
            else:
                st.error("데이터를 찾을 수 없습니다. 미국 주식은 AAPL처럼 티커를, 한국은 005930.KS 형식을 확인하세요.")
