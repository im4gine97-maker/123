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
    .box {background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; height: 100%;}
    </style>
    """, unsafe_allow_html=True)

# 1. 안전한 자동 번역 함수
def safe_translate(text):
    if not text or not isinstance(text, str) or len(text) < 2: return text
    try:
        return GoogleTranslator(source='en', target='ko').translate(text[:3000])
    except:
        return text

# 2. 데이터 수집 함수 (미국/한국 주식 오류 방어)
def get_stock_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    for i in range(3):
        try:
            price = stock.fast_info['lastPrice']
            info = stock.info
            if not isinstance(info, dict): info = {}
            return stock, price, info
        except Exception:
            time.sleep(2)
    return None, None, {}

# 3. 10년 DCF 모델 (강력한 데이터 우회 추출 적용)
def calculate_simple_dcf(stock, info, price):
    try:
        # 잉여현금흐름(FCF) 찾기 3단계 방어 로직
        fcf = info.get('freeCashflow')
        if not fcf:
            cf = stock.cash_flow
            if cf is not None and not cf.empty:
                if 'Free Cash Flow' in cf.index:
                    fcf = cf.loc['Free Cash Flow'].iloc[0]
                elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                    fcf = cf.loc['Operating Cash Flow'].iloc[0] + cf.loc['Capital Expenditure'].iloc[0]
        
        if not fcf or fcf <= 0:
            return None, "최근 잉여현금흐름(FCF)이 적자이거나 데이터가 없습니다."

        # 발행주식수 찾기
        shares = info.get('sharesOutstanding')
        if not shares or shares == 0:
            mcap = info.get('marketCap')
            if mcap and price > 0:
                shares = mcap / price
            else:
                return None, "발행주식수 산출 불가"

        # DCF 계산 (할인율 9%, 성장률 5%->3%, 영구성장률 2%)
        discount_rate, g1, g2, tg = 0.09, 0.05, 0.03, 0.02
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
        return None, "재무제표 API 제공 한도 초과"

st.title("⚡ JB Value Terminal PRO")
st.error("💡 한국 주식: 종목코드 뒤에 코스피는 '.KS', 코스닥은 '.KQ' (예: 005930.KS) / 미국 주식: 티커 입력 (예: AAPL)")

user_input = st.text_input("분석할 종목코드(Ticker)를 입력하세요", placeholder="예: AAPL, MSFT, 005930.KS")

if st.button("가치 분석 심층 스캔", type="primary"):
    if user_input:
        with st.spinner('미국/한국 실시간 데이터 추출 및 DCF 산출 중...'):
            search_ticker = user_input.strip().upper()
            
            stock, price, info = get_stock_data(search_ticker)
            
            if price and info:
                name = info.get('shortName', search_ticker)
                sector = info.get('sector', 'Unknown')
                is_financial = 'Financial' in sector
                
                # 지표 추출 (PBR 방어 로직 포함)
                fwd_pe = info.get('forwardPE', 0)
                pbr = info.get('priceToBook')
                if not pbr:  # PBR이 누락됐을 경우 직접 계산
                    book_value = info.get('bookValue')
                    pbr = (price / book_value) if book_value and book_value > 0 else 0
                
                roe = (info.get('returnOnEquity', 0) * 100) if info.get('returnOnEquity') else 0
                dividend_yield = (info.get('dividendYield', 0) * 100) if info.get('dividendYield') else 0
                
                # 질적 데이터 추출 (경영진)
                officers = info.get('companyOfficers', [])
                ceo_name = officers[0].get('name', 'CEO 정보 누락') if officers else 'CEO 정보 누락'
                summary = info.get('longBusinessSummary', '비즈니스 설명 데이터가 없습니다.')

                st.success(f"🏢 {name} ({search_ticker}) / 업종: {safe_translate(sector)}")
                
                col1, col2 = st.columns(2)
                
                # ---------------- [왼쪽] 펀더멘털 & DCF ----------------
                with col1:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("📊 1. 밸류에이션 & 안전마진")
                    st.write(f"**현재 주가:** {price:,.2f}")
                    st.write(f"**배당 수익률:** {dividend_yield:.2f}% (배당 일관성 체크 필요)")
                    
                    if is_financial:
                        st.warning("🏦 금융업: 부채가 원재료인 특성상 DCF 대신 PBR과 ROE로 평가합니다.")
                        st.write(f"- **PBR (주가순자산비율):** {pbr:.2f}배")
                        st.write(f"- **ROE (자기자본이익률):** {roe:.2f}%")
                        if 0 < pbr < 1.0:
                            st.markdown("- 상태: <span class='good'>청산가치 이하 할인 구간 (안전마진 확보)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("- 상태: <span class='highlight'>장부 투자가치 대비 프리미엄 구간</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"- **포워드 PER:** {fwd_pe:.2f}배")
                        st.write(f"- **PBR:** {pbr:.2f}배")
                        st.write(f"- **ROE (자본수익률):** {roe:.2f}% (ROIC 대체 확인용)")
                        
                        st.markdown("---")
                        st.write("**[10-Year DCF 내재가치 모델]**")
                        dcf_value, dcf_error = calculate_simple_dcf(stock, info, price)
                        
                        if dcf_value:
                            st.write(f"추정 적정가 (보수적 가정): **{dcf_value:,.2f}**")
                            mos = ((dcf_value - price) / dcf_value) * 100
                            if mos > 0:
                                st.markdown(f"- 안전마진 확보율: <span class='good'>{mos:.1f}% 저평가 (매수 고려)</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"- 상태: <span class='highlight'>시장가 대비 고평가 (프리미엄 지불 중)</span>", unsafe_allow_html=True)
                        else:
                            st.error(f"⚠️ 확인 필요: {dcf_error}")
                    st.markdown("</div>", unsafe_allow_html=True)

                # ---------------- [오른쪽] 경영진 번역 & 거장 모델 ----------------
                with col2:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("🕵️‍♂️ 2. 질적 분석 (자동 번역)")
                    st.markdown(f"- **핵심 경영진 (CEO):** <span class='good'>{safe_translate(ceo_name)}</span>", unsafe_allow_html=True)
                    st.markdown(f"- **비즈니스 모델 요약:**\n> {safe_translate(summary)[:400]}... (중략)")
                    st.info("💡 위 비즈니스 모델을 다른 사람에게 논리적으로 설명할 수 없다면 내 '능력 범위' 밖입니다.")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # ---------------- [하단] 거장들의 한마디 & 체크리스트 ----------------
                st.markdown("---")
                st.subheader("🧠 3. 거장들의 멘탈 모델")
                st.markdown("<div class='guru-quote'><b>워런 버핏:</b> 이익이 복리로 팽창하는가? 무엇보다 <span class='highlight'>경영자가 정직한가?</span> 도덕성이 의심되면 즉각 손절하게.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>필립 피셔:</b> 이 하락이 ①상업화 초기 문제 ②미스터 마켓의 우울증 ③해결 가능한 악재 중 하나라면 영혼을 걸고 매수하시오.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>찰리 멍거:</b> 단일 실패 지점은 없는가? 전문가의 반론을 재반박할 수 없다면 당신의 능력 범위 밖이네.</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("✅ 4. 투자의견 최종 체크리스트")
                col3, col4 = st.columns(2)
                with col3:
                    st.write("**[매수 전 필수 확인 6가지]**")
                    st.write("1. 가격은 저렴한가? (안전마진 확보)")
                    st.write("2. 좋은 비즈니스인가? (경제적 해자)")
                    st.write("3. 경영진은 신뢰할 수 있는가? (정직성 검증됨)")
                    st.write("4. 내가 놓친 리스크는 없는가?")
                    st.write("5. 이 기회를 어떻게 발견했는가?")
                    st.write("6. 내 능력 범위 안인가?")
                with col4:
                    st.write("**[오직 다음 3가지 경우에만 매도]**")
                    st.markdown("<span class='highlight'>1. 분석에 치명적인 실수가 있었을 때</span>", unsafe_allow_html=True)
                    st.markdown("<span class='highlight'>2. 밸류에이션이 지나치게 과열되었을 때</span>", unsafe_allow_html=True)
                    st.markdown("<span class='highlight'>3. 더 확실하고 안전한 기회를 발견했을 때</span>", unsafe_allow_html=True)
                    
            else:
                st.error("데이터를 가져오는 데 실패했습니다. 종목코드(티커)가 정확한지 확인하거나 잠시 후 다시 시도해 주세요.")
    else:
        st.warning("분석할 종목명이나 티커를 입력하세요.")
