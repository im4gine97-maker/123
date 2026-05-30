import streamlit as st
import yfinance as yf
from googletrans import Translator
import time

# 번역기 초기화
translator = Translator()

def safe_translate(text):
    try:
        # 영어 텍스트를 한국어로 번역
        return translator.translate(text, dest='ko').text
    except:
        return text

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

st.title("⚡ JB Value Terminal PRO")
st.error("🚨 시클리컬 기업 주의: 알파벳, 무디스 등 '해자(Moat) 기업' 분석에 최적화됨.")

ticker_map = {
    "애플": "AAPL", "구글": "GOOGL", "알파벳": "GOOGL", "마이크로소프트": "MSFT", 
    "아마존": "AMZN", "테슬라": "TSLA", "엔비디아": "NVDA", "크록스": "CROX", 
    "무디스": "MCO", "코카콜라": "KO", "뱅크오브아메리카": "BAC", "버크셔": "BRK-B",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "KB금융": "105560.KS", "현대차": "005380.KS"
}

user_input = st.text_input("기업명 또는 티커 입력", placeholder="예: 무디스, AAPL")

if st.button("가치 분석 실행", type="primary"):
    if user_input:
        with st.spinner('데이터 추출 및 번역 중...'):
            search_ticker = ticker_map.get(user_input.strip(), user_input.strip().upper())
            stock = yf.Ticker(search_ticker)
            info = stock.info if isinstance(stock.info, dict) else {}
            
            # --- 경영진 및 비즈니스 (번역 적용) ---
            name = info.get('shortName', search_ticker)
            sector = info.get('sector', 'Unknown')
            
            # 경영진 번역
            ceo_raw = "CEO 정보 누락"
            if info.get('companyOfficers'):
                ceo_raw = info['companyOfficers'][0].get('name', '이름 누락')
            ceo_kr = safe_translate(ceo_raw)
            
            # 비즈니스 요약 번역
            summary_raw = info.get('longBusinessSummary', '설명 없음')
            summary_kr = safe_translate(summary_raw)
            
            st.success(f"🏢 {name} / 업종: {safe_translate(sector)}")
            
            st.subheader("🕵️‍♂️ 2. 질적 분석 (번역 완료)")
            st.markdown(f"- **핵심 경영진:** <span class='good'>{ceo_kr}</span>", unsafe_allow_html=True)
            st.markdown(f"- **비즈니스 모델:**\n> {summary_kr[:500]}...")
            st.info("💡 위 비즈니스 모델을 다른 사람에게 논리적으로 설명할 수 없다면 내 '능력 범위' 밖입니다. 검색된 경영자의 이름으로 과거 주주 기만 이력이 없는지 반드시 직접 사실 수집을 진행하십시오.")
