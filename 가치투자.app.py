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
    if "." not in ticker_symbol:
        ticker_symbol = ticker_symbol.upper()
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

def calculate_buffett_dcf(stock, info, price, treasury_yield):
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
            return None, 0, "최근 잉여현금흐름(FCF)이 적자이거나 데이터가 없습니다."

        shares = info.get('sharesOutstanding')
        if not shares or shares == 0:
            mcap = info.get('marketCap')
            if mcap and price > 0:
                shares = mcap / price
            else:
                return None, 0, "발행주식수 산출 불가"

        discount_rate = max(treasury_yield / 100, 0.09)
        g1, g2, tg = 0.05, 0.03, 0.02

        future_fcf = []
        current_fcf = fcf
        
        for year in range(1, 11):
            current_fcf *= (1 + g1) if year <= 5 else (1 + g2)
            future_fcf.append(current_fcf / ((1 + discount_rate) ** year))

        tv = (current_fcf * (1 + tg)) / (discount_rate - tg)
        discounted_tv = tv / ((1 + discount_rate) ** 10)
        
        intrinsic_value = (sum(future_fcf) + discounted_tv) / shares
        mos = ((intrinsic_value - price) / intrinsic_value) * 100
        
        return intrinsic_value, mos, None
        
    except Exception as e:
        return None, 0, "DCF 산출용 재무 데이터 누락"

st.title("⚡ JB Value Terminal PRO")

# 해자(Moat) 및 시클리컬 경고문 복구 (가장 상단에 배치)
st.error("🚨 **시클리컬 기업 주의:** 본 분석 모델은 알파벳, 무디스처럼 **'경제적 해자(Moat)'**를 갖추고 이익이 장기 우상향하는 기업에 최적화되어 있습니다. 경기 민감주 분석 시 밸류에이션 왜곡에 주의하십시오.")
st.info("💡 **검색 팁:** 디어, 캐터필러, 삼성전자 등 주요 국내외 주식은 한글 이름만 쳐도 검색됩니다.")

ticker_map = {
    # 한국 주식
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", 
    "기아": "000270.KS", "KB금융": "105560.KS", "메리츠금융지주": "138040.KS",
    
    # 미국 주식
    "디어": "DE", "존디어": "DE", "캐터필러": "CAT", "캐타필러": "CAT",
    "보잉": "BA", "록히드마틴": "LMT", "GE": "GE", "3M": "MMM",
    "애플": "AAPL", "구글": "GOOGL", "알파벳": "GOOGL", "마이크로소프트": "MSFT", 
    "아마존": "AMZN", "테슬라": "TSLA", "엔비디아": "NVDA", "메타": "META",
    "월마트": "WMT", "코스트코": "COST", "타겟": "TGT", "홈디포": "HD",
    "비자": "V", "마스터카드": "MA", "아메리칸익스프레스": "AXP", "무디스": "MCO",
    "코카콜라": "KO", "펩시": "PEP", "맥도날드": "MCD", "스타벅스": "SBUX", 
    "존슨앤존슨": "JNJ", "P&G": "PG", "피앤지": "PG", "디즈니": "DIS",
    "버크셔": "BRK-B", "버크셔해서웨이": "BRK-B", "크록스": "CROX", "팔란티어": "PLTR"
}

user_input = st.text_input("기업명 또는 티커를 입력하세요", placeholder="예: 무디스, 디어, AAPL, 005930.KS")

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
                
                try:
                    tnx = yf.Ticker("^TNX")
                    treasury_yield = tnx.fast_info['lastPrice']
                except:
                    treasury_yield = 4.4 
                
                # 주요 재무 지표
                fwd_pe = info.get('forwardPE', 0)
                trailing_pe = info.get('trailingPE', 0)
                
                # 10년 평균 PER 산출 로직 (API 데이터 한계를 우회하여 Trailing PER 기반 보수적 추정)
                avg_pe_10y = info.get('fiveYearAvgPE')
                if not avg_pe_10y:
                    if trailing_pe > 0:
                        avg_pe_10y = trailing_pe * 1.1  # 과거 평균을 현재보다 약간 높게 설정 (보수적)
                    elif fwd_pe > 0:
                        avg_pe_10y = fwd_pe * 1.2
                    else:
                        avg_pe_10y = 15.0

                pbr = info.get('priceToBook')
                if not pbr: 
                    book_value = info.get('bookValue')
                    pbr = (price / book_value) if book_value and book_value > 0 else 0
                
                roe = (info.get('returnOnEquity', 0) * 100) if info.get('returnOnEquity') else 0
                dividend_yield = (info.get('dividendYield', 0) * 100) if info.get('dividendYield') else 0
                
                # 질적 데이터 추출
                officers = info.get('companyOfficers', [])
                ceo_name = officers[0].get('name', 'CEO 정보 누락') if officers else 'CEO 정보 누락'
                summary = info.get('longBusinessSummary', '비즈니스 설명 데이터가 없습니다.')

                st.success(f"🏢 {name} ({search_ticker}) / 업종: {safe_translate(sector)}")
                
                col1, col2 = st.columns(2)
                
                # ---------------- [왼쪽] 펀더멘털 & 적정가치 ----------------
                with col1:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("📊 1. 밸류에이션 & 안전마진")
                    currency_symbol = "₩" if is_korean else "$"
                    st.write(f"**현재 주가:** {currency_symbol}{price:,.2f}")
                    st.write(f"**배당 수익률:** {dividend_yield:.2f}% (※ 배당 일관성 확인 필요)")
                    
                    st.markdown("---")
                    st.write("**[상대 가치 평가: PER & PBR]**")
                    st.write(f"- **현재(Trailing) PER:** {trailing_pe:.2f}배")
                    st.write(f"- **컨센서스(Forward) PER:** {fwd_pe:.2f}배")
                    st.write(f"- **장기 과거 평균 PER (추정):** {avg_pe_10y:.2f}배")
                    
                    # Forward PER vs 평균 PER 안전마진 계산
                    if fwd_pe > 0 and avg_pe_10y > 0:
                        pe_mos = ((avg_pe_10y - fwd_pe) / avg_pe_10y) * 100
                        if pe_mos > 0:
                            st.markdown(f"▶ **PER 안전마진:** <span class='good'>+{pe_mos:.1f}% (과거 평균 대비 저평가)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"▶ **PER 안전마진:** <span class='highlight'>{pe_mos:.1f}% (과거 평균 대비 고평가)</span>", unsafe_allow_html=True)
                    
                    st.write(f"- **PBR (주가순자산비율):** {pbr:.2f}배")
                    st.write(f"- **ROE (자본수익률):** {roe:.2f}%")
                    
                    if not is_korean:
                        st.markdown("---")
                        earnings_yield = (1 / fwd_pe * 100) if fwd_pe > 0 else 0
                        spread = earnings_yield - treasury_yield
                        st.write(f"**[이익수익률 vs 10년물 미국채]**")
                        st.write(f"- 10년물 미국채 금리: {treasury_yield:.2f}%")
                        if spread > 0:
                            st.markdown(f"- 예상 이익수익률: **{earnings_yield:.2f}%** (<span class='good'>+{spread:.2f}%p 초과 수익</span>)", unsafe_allow_html=True)
                        else:
                            st.markdown(f"- 예상 이익수익률: **{earnings_yield:.2f}%** (<span class='highlight'>국채 대비 메리트 부족</span>)", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.write("**[절대 가치 평가: 버핏 10-Year DCF]**")
                    dcf_value, dcf_mos, dcf_error = calculate_buffett_dcf(stock, info, price, treasury_yield)
                    
                    if dcf_value:
                        st.write(f"**추정 적정가:** {currency_symbol}{dcf_value:,.2f}")
                        if dcf_mos > 0:
                            st.markdown(f"▶ **DCF 안전마진:** <span class='good'>+{dcf_mos:.1f}% 확보 (내재가치 대비 저평가)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"▶ **DCF 안전마진:** <span class='highlight'>{dcf_mos:.1f}% (현재가 고평가 상태)</span>", unsafe_allow_html=True)
                    else:
                        st.error(f"⚠️ {dcf_error}")
                    st.markdown("</div>", unsafe_allow_html=True)

                # ---------------- [오른쪽] 경영진 번역 & 질적 분석 ----------------
                with col2:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("🕵️‍♂️ 2. 질적 분석 (자동 번역)")
                    st.markdown(f"- **핵심 경영진 (CEO):** <span class='good'>{safe_translate(ceo_name)}</span>", unsafe_allow_html=True)
                    st.markdown(f"- **비즈니스 모델 요약:**\n> {safe_translate(summary)[:500]}... (중략)")
                    st.info("💡 주식은 기업의 소유권입니다. 지분 100%를 인수한다고 가정할 때, 이 비즈니스가 내 상식으로 이해 가능한 범위인가요? 가격 결정력이 있는지, 경영진이 정직한지 사실을 수집하십시오.")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # ---------------- [하단] 거장들의 체크리스트 ----------------
                st.markdown("---")
                st.subheader("✅ 3. 투자의견 최종 체크리스트 (매수/매도 원칙)")
                col3, col4 = st.columns(2)
                with col3:
                    st.write("**[매수 전 필수 확인 6가지]**")
                    st.write("1. 가격은 저렴한가? (PER/DCF 안전마진)")
                    st.write("2. 좋은 비즈니스인가? (경제적 해자)")
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
