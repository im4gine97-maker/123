import streamlit as st
import yfinance as yf
from deep_translator import GoogleTranslator
import time

# 앱 설정 및 디자인
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

# 번역기 함수
def safe_translate(text):
    if not text or len(text) < 2: return text
    try:
        return GoogleTranslator(source='en', target='ko').translate(text[:4500])
    except:
        return text

st.title("⚡ JB Value Terminal PRO")
st.error("🚨 시클리컬 기업 주의: 알파벳, 무디스 등 '해자(Moat) 기업' 분석에 최적화됨.")

# 티커 매핑
ticker_map = {
    "애플": "AAPL", "구글": "GOOGL", "알파벳": "GOOGL", "마이크로소프트": "MSFT", 
    "아마존": "AMZN", "테슬라": "TSLA", "엔비디아": "NVDA", "크록스": "CROX", 
    "무디스": "MCO", "코카콜라": "KO", "뱅크오브아메리카": "BAC", "버크셔": "BRK-B",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "KB금융": "105560.KS", "현대차": "005380.KS"
}

user_input = st.text_input("기업명 또는 티커 입력", placeholder="예: 무디스, AAPL, 005930.KS")

if st.button("가치 분석 실행", type="primary"):
    if user_input:
        with st.spinner('데이터 추출 및 번역 중...'):
            search_ticker = ticker_map.get(user_input.strip(), user_input.strip().upper())
            stock = yf.Ticker(search_ticker)
            info = stock.info if isinstance(stock.info, dict) else {}
            
            # 기본 정보
            name = info.get('shortName', search_ticker)
            sector = info.get('sector', 'Unknown')
            
            # 경영진 및 비즈니스 (번역 적용)
            ceo_raw = "CEO 정보 누락"
            if info.get('companyOfficers'):
                ceo_raw = info['companyOfficers'][0].get('name', '이름 누락')
            
            summary_raw = info.get('longBusinessSummary', '설명 없음')
            
            # 결과 출력
            st.success(f"🏢 {name} / 업종: {safe_translate(sector)}")
            
            st.subheader("🕵️‍♂️ 질적 분석 (능력범위 & 경영진)")
            st.markdown(f"- **핵심 경영진:** <span class='good'>{safe_translate(ceo_raw)}</span>", unsafe_allow_html=True)
            st.markdown(f"- **비즈니스 모델:**\n> {safe_translate(summary_raw)}")
            st.info("💡 위 비즈니스 모델을 다른 사람에게 논리적으로 설명할 수 없다면 내 '능력 범위' 밖입니다.")

            st.markdown("---")
            st.subheader("🧠 거장들의 멘탈 모델")
            st.markdown("<div class='guru-quote'><b>워런 버핏:</b> 경영자가 정직한가? 도덕성이 의심되면 즉각 손절하게.</div>", unsafe_allow_html=True)
            st.markdown("<div class='guru-quote'><b>필립 피셔:</b> 이 하락이 ①상업화 초기 문제 ②미스터 마켓의 우울증 ③해결 가능한 악재 중 하나라면 매수하시오.</div>", unsafe_allow_html=True)
            st.markdown("<div class='guru-quote'><b>찰리 멍거:</b> 단일 실패 지점은 없는가? 전문가의 반론을 재반박할 수 없다면 당신의 능력 범위 밖이네.</div>", unsafe_allow_html=True)
    else:
        st.warning("기업명이나 티커를 입력해주세요.")
