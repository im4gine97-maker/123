import streamlit as st
import yfinance as yf
from deep_translator import GoogleTranslator
import time

st.set_page_config(page_title="JB Value Terminal", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main {background-color: #0d1117; color: #c9d1d9;}
    h1, h2, h3 {color: #58a6ff;}
    .guru-quote {font-style: italic; color: #8b949e; border-left: 3px solid #e3b341; padding-left: 10px;}
    .highlight {color: #da3633; font-weight: bold;}
    .good {color: #3fb950; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

def safe_translate(text):
    if not text or len(text) < 2: return text
    try:
        return GoogleTranslator(source='en', target='ko').translate(text[:3000])
    except:
        return text

# 데이터 가져오기 (재시도 로직 추가)
def get_stock_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    for i in range(3): # 3번까지 재시도
        try:
            # 최대한 무거운 .info 대신 fast_info 사용
            info = stock.fast_info
            # 가격 정보
            price = info['lastPrice']
            # .info는 필요할 때만 호출
            full_info = stock.info 
            return price, full_info
        except Exception:
            time.sleep(2) # 2초 대기 후 재시도
    return None, {}

st.title("⚡ JB Value Terminal PRO")
st.error("🚨 시클리컬 기업 주의: 알파벳, 무디스 등 '해자(Moat) 기업' 분석에 최적화됨.")

ticker_map = {
    "애플": "AAPL", "구글": "GOOGL", "알파벳": "GOOGL", "마이크로소프트": "MSFT", 
    "아마존": "AMZN", "테슬라": "TSLA", "엔비디아": "NVDA", "크록스": "CROX", 
    "무디스": "MCO", "코카콜라": "KO", "뱅크오브아메리카": "BAC", "버크셔": "BRK-B",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "KB금융": "105560.KS", "현대차": "005380.KS"
}

user_input = st.text_input("기업명 또는 티커 입력", placeholder="예: 무디스, AAPL, 005930.KS")

if st.button("가치 분석 실행", type="primary"):
    if user_input:
        with st.spinner('실시간 서버 통신 중...'):
            search_ticker = ticker_map.get(user_input.strip(), user_input.strip().upper())
            price, info = get_stock_data(search_ticker)
            
            if price:
                name = info.get('shortName', search_ticker)
                sector = info.get('sector', 'Unknown')
                ceo_raw = info.get('companyOfficers', [{'name': '정보 없음'}])[0].get('name', '정보 없음')
                summary_raw = info.get('longBusinessSummary', '설명 없음')
                
                st.success(f"🏢 {name} / 업종: {safe_translate(sector)}")
                st.subheader("🕵️‍♂️ 질적 분석")
                st.markdown(f"- **핵심 경영진:** <span class='good'>{safe_translate(ceo_raw)}</span>", unsafe_allow_html=True)
                st.markdown(f"- **비즈니스 모델:**\n> {safe_translate(summary_raw)}")
            else:
                st.error("데이터를 가져오는 데 실패했습니다. 잠시 후 다시 시도해 주세요.")
    else:
        st.warning("기업명이나 티커를 입력해주세요.")
