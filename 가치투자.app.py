import streamlit as st
import yfinance as yf
from deep_translator import GoogleTranslator
import time

st.set_page_config(page_title="JB Value Terminal PRO", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #0d1117; color: #c9d1d9;}
    h1, h2, h3 {color: #58a6ff;}
    .guru-quote {font-style: italic; color: #8b949e; border-left: 3px solid #e3b341; padding-left: 10px; margin-bottom: 15px;}
    .highlight {color: #da3633; font-weight: bold;}
    .good {color: #3fb950; font-weight: bold;}
    .box {background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d;}
    </style>
    """, unsafe_allow_html=True)

# 1. 안전한 자동 번역 함수
def safe_translate(text):
    if not text or not isinstance(text, str) or len(text) < 2: return text
    try:
        return GoogleTranslator(source='en', target='ko').translate(text[:3000])
    except:
        return text

# 2. 10년 DCF 모델 계산 함수
def calculate_simple_dcf(stock_ticker):
    try:
        stock = yf.Ticker(stock_ticker)
        cashflow = stock.cash_flow
        if cashflow is None or cashflow.empty:
            return None, "현금흐름 데이터 없음"
            
        if 'Free Cash Flow' in cashflow.index:
            fcf = cashflow.loc['Free Cash Flow'].iloc[0]
        elif 'Operating Cash Flow' in cashflow.index and 'Capital Expenditure' in cashflow.index:
            fcf = cashflow.loc['Operating Cash Flow'].iloc[0] + cashflow.loc['Capital Expenditure'].iloc[0]
        else:
            return None, "FCF 계산 불가"

        if fcf <= 0:
            return None, "최근 잉여현금흐름이 적자입니다."

        # 기본 가정: 할인율 9%, 1~5년 성장률 5%, 6~10년 성장률 3%, 영구 성장률 2%
        discount_rate, g1, g2, tg = 0.09, 0.05, 0.03, 0.02
        shares = stock.info.get('sharesOutstanding')
        if not shares: return None, "발행주식수 누락"

        future_fcf = []
        current_fcf = fcf
        for year in range(1, 11):
            current_fcf *= (1 + g1) if year <= 5 else (1 + g2)
            future_fcf.append(current_fcf / ((1 + discount_rate) ** year))

        tv = (current_fcf * (1 + tg)) / (discount_rate - tg)
        discounted_tv = tv / ((1 + discount_rate) ** 10)
        
        intrinsic_value = (sum(future_fcf) + discounted_tv) / shares
        return intrinsic_value, None
    except Exception as e:
        return None, "DCF 산출 실패 (데이터 부족)"

st.title("⚡ JB Value Terminal PRO")
st.error("💡 한국 주식 검색 방법: 종목코드 6자리 뒤에 코스피는 '.KS', 코스닥은 '.KQ'를 붙이세요. (예: 삼성전자 -> 005930.KS, 에코프로 -> 086520.KQ)")

# 편의용 단축키 맵 (여기에 없어도 티커만 치면 다 검색됩니다)
ticker_map = {
    "애플": "AAPL", "구글": "GOOGL", "알파벳": "GOOGL", "마이크로소프트": "MSFT", 
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS"
}

user_input = st.text_input("종목명(단축키) 또는 티커(Ticker)를 입력하세요", placeholder="예: AAPL, 035720.KS")

if st.button("가치 분석 심층 스캔", type="primary"):
    if user_input:
        with st.spinner('실시간 재무 데이터 추출 및 10년 DCF 시뮬레이션 중...'):
            search_ticker = ticker_map.get(user_input.strip(), user_input.strip().upper())
            
            try:
                stock = yf.Ticker(search_ticker)
                price = stock.fast_info['lastPrice']
                info = stock.info if isinstance(stock.info, dict) else {}
                
                name = info.get('shortName', search_ticker)
                sector = info.get('sector', 'Unknown')
                is_financial = 'Financial' in sector
                
                # 핵심 지표
                fwd_pe = info.get('forwardPE', 0)
                pbr = info.get('priceToBook', 0)
                roe = (info.get('returnOnEquity', 0) * 100) if info.get('returnOnEquity') else 0
                
                # 질적 데이터 (경영진 및 비즈니스)
                officers = info.get('companyOfficers', [])
                ceo_name = officers[0].get('name', '정보 누락') if officers else '정보 누락'
                summary = info.get('longBusinessSummary', '비즈니스 설명 데이터가 없습니다.')

                st.success(f"🏢 {name} ({search_ticker}) / 업종: {safe_translate(sector)}")
                
                col1, col2 = st.columns(2)
                
                # 왼쪽 단: 펀더멘털 & 적정 가치 (업종별 분기 처리)
                with col1:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("📊 1. 밸류에이션 & 안전마진")
                    st.write(f"**현재 주가:** {price:,.2f}")
                    
                    if is_financial:
                        st.warning("🏦 금융업: 부채가 원재료인 특성상 DCF와 POE 대신 PBR과 ROE를 최우선으로 평가합니다.")
                        st.write(f"- **PBR (주가순자산비율):** {pbr:.2f}배")
                        st.write(f"- **ROE (자기자본이익률):** {roe:.2f}%")
                        if pbr > 0 and pbr < 1.0:
                            st.markdown("- 안전마진: <span class='good'>청산가치 이하 할인 구간</span>", unsafe_allow_html=True)
                        elif pbr >= 1.0:
                            st.markdown("- 안전마진: <span class='highlight'>장부 투자가치 대비 프리미엄 구간</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"- **포워드 PER:** {fwd_pe:.2f}배")
                        st.write(f"- **PBR:** {pbr:.2f}배")
                        
                        st.markdown("---")
                        st.write("**[10-Year DCF 내재가치 모델]**")
                        dcf_value, dcf_error = calculate_simple_dcf(search_ticker)
                        
                        if dcf_value:
                            st.write(f"추정 적정가 (보수적 가정): **{dcf_value:,.2f}**")
                            mos = ((dcf_value - price) / dcf_value) * 100
                            if mos > 0:
                                st.markdown(f"- 안전마진 확보율: <span class='good'>{mos:.1f}% 저평가</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"- 상태: <span class='highlight'>시장가 대비 고평가 (프리미엄 지불 중)</span>", unsafe_allow_html=True)
                        else:
                            st.error(f"DCF 계산 보류: {dcf_error}")
                    st.markdown("</div>", unsafe_allow_html=True)

                # 오른쪽 단: 질적 분석 (자동 번역)
                with col2:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("🕵️‍♂️ 2. 질적 분석 (능력 범위 체크)")
                    st.markdown(f"- **핵심 경영진 (CEO):** <span class='good'>{safe_translate(ceo_name)}</span>", unsafe_allow_html=True)
                    st.markdown(f"- **비즈니스 모델 요약 (자동번역):**\n> {safe_translate(summary)[:500]}...")
                    st.info("💡 위 비즈니스 모델을 다른 사람에게 논리적으로 설명할 수 없다면 내 '능력 범위' 밖입니다. 검색된 경영자의 과거 주주 기만 이력이 없는지 직접 팩트체크 하십시오.")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.subheader("🧠 3. 매도 절대 3원칙 점검")
                st.markdown("<div class='guru-quote'>1. 분석에 치명적인 실수가 있었는가? <br>2. 주가가 폭등하여 밸류에이션(PBR/PER)이 지나치게 과열되었는가? <br>3. 더 확실하고 안전한 기회를 발견했는가?</div>", unsafe_allow_html=True)
                
            except Exception as e:
                st.error("데이터를 불러오지 못했습니다. 종목코드(티커)가 정확한지 확인해주세요.")
    else:
        st.warning("분석할 종목명이나 티커를 입력하세요.")
