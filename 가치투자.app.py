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

def safe_translate(text):
    if not text or not isinstance(text, str) or len(text) < 2: return text
    try:
        return GoogleTranslator(source='en', target='ko').translate(text[:3000])
    except:
        return text

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

def calculate_simple_dcf(stock, info, price):
    try:
        fcf = info.get('freeCashflow')
        if not fcf:
            cf = stock.cash_flow
            if cf is not None and not cf.empty:
                if 'Free Cash Flow' in cf.index:
                    fcf = cf.loc['Free Cash Flow'].iloc[0]
                elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                    fcf = cf.loc['Operating Cash Flow'].iloc[0] + cf.loc['Capital Expenditure'].iloc[0]
        
        if not fcf or fcf <= 0:
            return None, "최근 잉여현금흐름(FCF) 부족 및 적자"

        shares = info.get('sharesOutstanding')
        if not shares or shares == 0:
            mcap = info.get('marketCap')
            if mcap and price > 0:
                shares = mcap / price
            else:
                return None, "발행주식수 산출 불가"

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
        return None, "DCF 산출용 데이터 누락"

st.title("⚡ JB Value Terminal PRO")
st.error("💡 주요 한국/미국 주식은 '이름'만 쳐도 됩니다. (예: 삼성전자, 애플, 테슬라)")

# 검색 편의를 위한 대규모 티커 맵핑
ticker_map = {
    # 한국 주식
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "현대자동차": "005380.KS",
    "기아": "000270.KS", "기아차": "000270.KS", "KB금융": "105560.KS", "신한지주": "055550.KS",
    "네이버": "035420.KS", "NAVER": "035420.KS", "카카오": "035720.KS",
    "에코프로": "086520.KQ", "에코프로비엠": "247540.KQ", "셀트리온": "068270.KS",
    "LG엔솔": "373220.KS", "LG에너지솔루션": "373220.KS", "POSCO홀딩스": "005490.KS",
    "포스코홀딩스": "005490.KS", "LG화학": "051910.KS", "삼성SDI": "006400.KS",
    "메리츠금융지주": "138040.KS", "삼성바이오로직스": "207940.KS", "하나금융지주": "086790.KS",
    
    # 미국 주식
    "애플": "AAPL", "구글": "GOOGL", "알파벳": "GOOGL", "마이크로소프트": "MSFT", "마소": "MSFT",
    "아마존": "AMZN", "테슬라": "TSLA", "엔비디아": "NVDA", "메타": "META", "페이스북": "META",
    "넷플릭스": "NFLX", "크록스": "CROX", "무디스": "MCO", "코카콜라": "KO", "펩시": "PEP",
    "뱅크오브아메리카": "BAC", "버크셔": "BRK-B", "버크셔해서웨이": "BRK-B", "스타벅스": "SBUX",
    "AMD": "AMD", "인텔": "INTC", "퀄컴": "QCOM", "TSMC": "TSM", "팔란티어": "PLTR", "델타항공": "DAL"
}

user_input = st.text_input("기업명 또는 티커를 입력하세요", placeholder="예: 삼성전자, 애플, TSLA")

if st.button("가치 분석 심층 스캔", type="primary"):
    if user_input:
        with st.spinner('실시간 재무 데이터 추출 및 가치 평가 중...'):
            query = user_input.replace(" ", "")
            search_ticker = ticker_map.get(query, user_input.strip().upper())
            
            stock, price, info = get_stock_data(search_ticker)
            
            if price and info:
                name = info.get('shortName', search_ticker)
                sector = info.get('sector', 'Unknown')
                is_korean = search_ticker.endswith('.KS') or search_ticker.endswith('.KQ')
                
                # 10년물 국채 금리 가져오기
                try:
                    tnx = yf.Ticker("^TNX")
                    treasury_yield = tnx.fast_info['lastPrice']
                except:
                    treasury_yield = 4.4 
                
                # 주요 재무 지표 추출
                fwd_pe = info.get('forwardPE', 0)
                trailing_pe = info.get('trailingPE', 0)
                pbr = info.get('priceToBook')
                if not pbr: 
                    book_value = info.get('bookValue')
                    pbr = (price / book_value) if book_value and book_value > 0 else 0
                
                roe = (info.get('returnOnEquity', 0) * 100) if info.get('returnOnEquity') else 0
                roic = roe # yfinance API 한계로 임시 대체 표기
                dividend_yield = (info.get('dividendYield', 0) * 100) if info.get('dividendYield') else 0
                
                # 질적 데이터 추출 (경영진 번역)
                officers = info.get('companyOfficers', [])
                ceo_name = officers[0].get('name', 'CEO 정보 누락') if officers else 'CEO 정보 누락'
                summary = info.get('longBusinessSummary', '비즈니스 설명 데이터가 없습니다.')

                st.success(f"🏢 {name} ({search_ticker}) / 업종: {safe_translate(sector)}")
                
                col1, col2 = st.columns(2)
                
                # ---------------- [왼쪽] 펀더멘털 & 적정가치 ----------------
                with col1:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("📊 1. 밸류에이션 & 안전마진")
                    st.write(f"**현재 주가:** {price:,.2f}")
                    st.write(f"**배당 수익률:** {dividend_yield:.2f}% (※ 배당 일관성 확인 필요)")
                    
                    if is_korean:
                        st.warning("🇰🇷 한국 주식: 시클리컬 특성상 PBR을 최우선 지표로 확인합니다.")
                        st.write(f"- **PBR (주가순자산비율):** {pbr:.2f}배")
                        st.write(f"- **현재 PER:** {trailing_pe:.2f}배 / **컨센서스(Fwd) PER:** {fwd_pe:.2f}배")
                        st.write(f"- **ROIC (자본수익률 추정치):** {roic:.2f}%")
                        
                        if 0 < pbr < 1.0:
                            st.markdown("- 안전마진: <span class='good'>자산가치 대비 저평가 (할인 구간)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("- 안전마진: <span class='highlight'>장부 투자가치 대비 프리미엄 구간</span>", unsafe_allow_html=True)
                    else:
                        earnings_yield = (1 / fwd_pe * 100) if fwd_pe > 0 else 0
                        spread = earnings_yield - treasury_yield
                        
                        st.write(f"- **현재 PER:** {trailing_pe:.2f}배 / **컨센서스(Fwd) PER:** {fwd_pe:.2f}배")
                        st.write(f"- **PBR:** {pbr:.2f}배")
                        st.write(f"- **ROIC (자본수익률 추정치):** {roic:.2f}%")
                        
                        st.markdown("---")
                        st.write(f"**[이익수익률 vs 10년물 국채]**")
                        st.write(f"- 10년물 미국채 금리: {treasury_yield:.2f}%")
                        if spread > 0:
                            st.markdown(f"- 예상 이익수익률: **{earnings_yield:.2f}%** (<span class='good'>+{spread:.2f}%p 초과 수익</span>)", unsafe_allow_html=True)
                        else:
                            st.markdown(f"- 예상 이익수익률: **{earnings_yield:.2f}%** (<span class='highlight'>국채 대비 메리트 부족</span>)", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.write("**[10-Year DCF 내재가치 모델]**")
                        dcf_value, dcf_error = calculate_simple_dcf(stock, info, price)
                        
                        if dcf_value:
                            st.write(f"추정 적정가 (보수적 가정): **{dcf_value:,.2f}**")
                            mos = ((dcf_value - price) / dcf_value) * 100
                            if mos > 0:
                                st.markdown(f"- 안전마진 확보율: <span class='good'>{mos:.1f}% 저평가</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"- 상태: <span class='highlight'>시장가 대비 고평가</span>", unsafe_allow_html=True)
                        else:
                            st.error(f"⚠️ {dcf_error}")
                    st.markdown("</div>", unsafe_allow_html=True)

                # ---------------- [오른쪽] 경영진 번역 & 질적 분석 ----------------
                with col2:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("🕵️‍♂️ 2. 질적 분석 (자동 번역)")
                    st.markdown(f"- **핵심 경영진 (CEO):** <span class='good'>{safe_translate(ceo_name)}</span>", unsafe_allow_html=True)
                    st.markdown(f"- **비즈니스 모델 요약:**\n> {safe_translate(summary)[:500]}... (중략)")
                    st.info("💡 비즈니스가 내 상식으로 이해 가능한 범위인가? 가격 결정력이 있는가? 경영진의 도덕성(사실 수집)을 확인하십시오.")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # ---------------- [하단] 거장들의 체크리스트 ----------------
                st.markdown("---")
                st.subheader("🧠 3. 거장들의 멘탈 모델")
                st.markdown("<div class='guru-quote'><b>워런 버핏:</b> 이익이 10년물 국채를 이기고 복리로 팽창하는 구간에 있는가? 단일 실패 지점은 없는가?</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>필립 피셔:</b> 이 하락이 ①상업화 초기 문제 ②미스터 마켓의 우울증 ③해결 가능한 악재 중 하나라면 매수하시오.</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("✅ 4. 투자의견 최종 체크리스트")
                col3, col4 = st.columns(2)
                with col3:
                    st.write("**[매수 전 필수 확인 6가지]**")
                    st.write("1. 가격은 저렴한가?")
                    st.write("2. 좋은 비즈니스인가?")
                    st.write("3. 경영진은 신뢰할 수 있는가(검증됨)?")
                    st.write("4. 내가 놓친 리스크는 없는가?")
                    st.write("5. 이 기회를 어떻게 발견했는가?")
                    st.write("6. 내 능력 범위 안인가?")
                with col4:
                    st.write("**[오직 다음 3가지 경우에만 매도]**")
                    st.markdown("<span class='highlight'>1. 분석에 실수가 있었을 때.</span>", unsafe_allow_html=True)
                    st.markdown("<span class='highlight'>2. 밸류에이션이 지나치게 높아졌을 때.</span>", unsafe_allow_html=True)
                    st.markdown("<span class='highlight'>3. 더 확실하고 안전한 기회를 발견했을 때.</span>", unsafe_allow_html=True)
                    
            else:
                st.error("데이터를 불러오지 못했습니다. 종목명을 다시 확인해주세요.")
    else:
        st.warning("분석할 종목명을 입력하세요.")
