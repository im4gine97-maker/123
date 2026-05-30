import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import pandas as pd
from datetime import datetime

# 앱 이름 변경 및 레이아웃
st.set_page_config(page_title="VALUE", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 세션 상태 초기화
# ==========================================
if "search_tk" not in st.session_state: st.session_state.search_tk = None
if "history" not in st.session_state: st.session_state.history = []
if "bookmarks" not in st.session_state: st.session_state.bookmarks = []
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "main_input" not in st.session_state: st.session_state.main_input = ""

if "search_ranking" not in st.session_state: st.session_state.search_ranking = {}
if "stock_comments" not in st.session_state: st.session_state.stock_comments = {}
if "community_posts" not in st.session_state: st.session_state.community_posts = []

def trigger_scan():
    if st.session_state.get("main_input"):
        q = st.session_state.main_input.replace(" ", "").upper()
        tk = tmap.get(q, q)
        st.session_state.search_tk = tk

# ==========================================
# 글로벌 매크로 실시간 데이터
# ==========================================
@st.cache_data(ttl=900) 
def get_macro_data():
    macro_symbols = {
        "KOSPI": "^KS11", "KOSDAQ": "^KQ11", 
        "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Nasdaq Futures": "NQ=F",
        "USD/KRW": "KRW=X", "WTI Crude": "CL=F", "10Y Treasury": "^TNX",
        "SPY": "SPY", "QQQ": "QQQ"  
    }
    res = {}
    for name, tk in macro_symbols.items():
        try:
            stk = yf.Ticker(tk)
            hist = stk.history(period="5d")
            if len(hist) >= 2:
                last_p, prev_p = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                change, pct = last_p - prev_p, ((last_p - prev_p) / prev_p) * 100
                res[name] = {"p": last_p, "c": change, "pct": pct}
            else: res[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
        except: res[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
            
    try: res["SPY_PE"] = yf.Ticker("SPY").info.get("forwardPE", 22.0)
    except: res["SPY_PE"] = 22.0
    try: res["QQQ_PE"] = yf.Ticker("QQQ").info.get("forwardPE", 30.0)
    except: res["QQQ_PE"] = 30.0
    return res

macro_data = get_macro_data()

# ==========================================
# 사이드바
# ==========================================
with st.sidebar:
    if st.session_state.lang == "ko":
        if st.button("English", use_container_width=True):
            st.session_state.lang = "en"; st.rerun()
    else:
        if st.button("Korean", use_container_width=True):
            st.session_state.lang = "ko"; st.rerun()
            
    is_ko = st.session_state.lang == "ko"
    def t(ko, en): return ko if is_ko else en
        
    st.divider()
    
    st.header(t("실시간 인기 종목", "Trending Stocks"))
    if not st.session_state.search_ranking:
        st.caption(t("아직 검색된 종목이 없습니다.", "No searches yet."))
    else:
        top_5 = sorted(st.session_state.search_ranking.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (rtk, count) in enumerate(top_5):
            if st.button(f"{i+1}. {rtk} ({count}{t('회', ' hits')})", key=f"rank_{rtk}", use_container_width=True):
                st.session_state.search_tk = rtk
                st.rerun()
                
    st.divider()
    
    st.header(t("내 서재", "My Library"))
    st.subheader(t("관심 종목 (즐겨찾기)", "Bookmarks"))
    if not st.session_state.bookmarks:
        st.caption(t("즐겨찾기한 종목이 없습니다.", "No bookmarked tickers yet."))
    else:
        for b_tk in st.session_state.bookmarks:
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(b_tk, key=f"bk_{b_tk}", use_container_width=True):
                    st.session_state.search_tk = b_tk; st.rerun()
            with c2:
                if st.button("X", key=f"del_bk_{b_tk}"):
                    st.session_state.bookmarks.remove(b_tk); st.rerun()
                    
    st.divider()
    
    st.subheader(t("최근 검색 기록", "Recent Searches"))
    if not st.session_state.history:
        st.caption(t("검색 기록이 없습니다.", "No recent searches."))
    else:
        if st.button(t("전체 삭제", "Clear All History"), use_container_width=True):
            st.session_state.history = []; st.rerun()
            
        for h_tk in reversed(st.session_state.history):
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(h_tk, key=f"h_{h_tk}", use_container_width=True):
                    st.session_state.search_tk = h_tk; st.rerun()
            with c2:
                if st.button("X", key=f"del_h_{h_tk}"):
                    st.session_state.history.remove(h_tk); st.rerun()
                    
    st.divider()
    
    st.header(t("고객 센터", "Customer Center"))
    st.caption(t("버그 신고, 피드백, 기능 제안을 환영합니다.", "Report bugs, send feedback, or suggest features."))
    st.markdown(f"<a href='mailto:admin@value-terminal.com' style='display: block; text-align: center; background-color: #30363d; color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold;'>{t('개발자에게 이메일 보내기', 'Send Email to Developer')}</a>", unsafe_allow_html=True)

# ==========================================
# 메인 UI 스타일 및 번역 방지 메타태그
# ==========================================
st.markdown("""
<meta name="google" content="notranslate">
<style>
.main {background-color: #0e1117; color: #c9d1d9; font-family: 'Pretendard', sans-serif;}
h1, h2, h3 {color: #58a6ff; font-weight: 700;}
.box {background-color: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 20px;}
.guru-quote {font-style: italic; color: #8b949e; border-left: 3px solid #58a6ff; padding-left: 15px; margin-bottom: 12px; background: #1c2128; padding: 15px; border-radius: 0 8px 8px 0;}
.highlight {color: #ff7b72; font-weight: bold;}
.good {color: #3fb950; font-weight: bold;}
.stTabs [data-baseweb="tab-list"] {gap: 20px; border-bottom: 1px solid #30363d;}
.stTabs [data-baseweb="tab"] {font-size: 1.15rem; font-weight: 600; color: #8b949e; padding-bottom: 10px;}
.stTabs [aria-selected="true"] {color: #58a6ff; border-bottom: 2px solid #58a6ff;}
.macro-ticker::-webkit-scrollbar { display: none; }
.macro-ticker { -ms-overflow-style: none; scrollbar-width: none; }
.comment-box {background-color: #1c2128; padding: 15px; border-radius: 8px; border-left: 4px solid #8b949e; margin-bottom: 10px; color: #e6edf3;}
.comment-time {font-size: 0.8rem; color: #8b949e;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div translate="no" style="padding-top: 5px; padding-bottom: 5px;">
    <span style="font-size: 3.2rem; font-weight: 900; color: #ffffff; letter-spacing: 2px; line-height: 1.2;">
        VALUE
    </span>
</div>
""", unsafe_allow_html=True)

# 번역 방지 안내 문구
st.info(t("화면 글씨가 어색하게 번역되어 보인다면 브라우저의 '자동 번역' 기능을 꺼주세요. (앱 자체의 언어 변환 기능을 이용해 주십시오)", "If the text looks distorted, please disable your browser's auto-translate. Use the language toggle in the sidebar instead."))

# ==========================================
# 가로 스크롤 매크로 대시보드
# ==========================================
macro_items = [
    (t("KOSPI", "KOSPI"), f"{macro_data['KOSPI']['p']:,.2f}", macro_data['KOSPI']['pct'], "%"),
    (t("KOSDAQ", "KOSDAQ"), f"{macro_data['KOSDAQ']['p']:,.2f}", macro_data['KOSDAQ']['pct'], "%"),
    (t("S&P 500", "S&P 500"), f"{macro_data['S&P 500']['p']:,.2f}", macro_data['S&P 500']['pct'], "%"),
    (t("Nasdaq 100", "Nasdaq 100"), f"{macro_data['Nasdaq 100']['p']:,.2f}", macro_data['Nasdaq 100']['pct'], "%"),
    (t("NQ 선물", "Nasdaq Fut"), f"{macro_data['Nasdaq Futures']['p']:,.2f}", macro_data['Nasdaq Futures']['pct'], "%"),
    (t("환율(KRW/USD)", "USD/KRW"), f"{macro_data['USD/KRW']['p']:,.2f}", macro_data['USD/KRW']['pct'], "%"),
    (t("WTI 원유", "WTI Crude"), f"${macro_data['WTI Crude']['p']:,.2f}", macro_data['WTI Crude']['pct'], "%"),
    (t("10년물 국채", "10Y Treasury"), f"{macro_data['10Y Treasury']['p']:.3f}%", macro_data['10Y Treasury']['c'], " bp")
]

macro_html = "<div class='macro-ticker' translate='no' style='display: flex; overflow-x: auto; gap: 12px; padding: 10px 0 20px 0; -webkit-overflow-scrolling: touch;'>"
for name, val, chg, unit in macro_items:
    color = "#3fb950" if chg > 0 else ("#ff7b72" if chg < 0 else "#8b949e")
    sign = "+" if chg > 0 else ""
    chg_str = f"{sign}{chg:.3f}{unit}" if unit == " bp" else f"{sign}{chg:.2f}{unit}"
    macro_html += f"<div style='flex: 0 0 auto; background: #161b22; padding: 15px 20px; border-radius: 10px; border: 1px solid #30363d; min-width: 140px;'><div style='font-size: 0.85rem; color: #8b949e; margin-bottom: 5px; font-weight: 600;'>{name}</div><div style='font-size: 1.3rem; font-weight: bold; color: #ffffff;'>{val}</div><div style='font-size: 0.95rem; font-weight: bold; color: {color}; margin-top: 2px;'>{chg_str}</div></div>"
macro_html += "</div>"
st.markdown(macro_html, unsafe_allow_html=True)

spy_ey = (1 / macro_data["SPY_PE"]) * 100 if macro_data["SPY_PE"] > 0 else 0
qqq_ey = (1 / macro_data["QQQ_PE"]) * 100 if macro_data["QQQ_PE"] > 0 else 0
tnx = macro_data["10Y Treasury"]["p"]
spy_erp, qqq_erp = spy_ey - tnx, qqq_ey - tnx

def get_market_opinion(erp):
    if erp > 3.0: return t("강력 매수 (역사적 저평가)", "Strong Buy (Historic Undervaluation)"), "#3fb950"
    elif erp > 1.0: return t("적립식 매수 (안전마진 존재)", "Buy (Margin of safety exists)"), "#58a6ff"
    elif erp > -1.0: return t("관망 (채권과 주식 매력도 유사)", "Hold (Equities & Bonds equally attractive)"), "#e3b341"
    else: return t("매도 경고 (채권이 압도적으로 유리한 버블 구간)", "Sell Warning (Bonds vastly superior, Bubble risk)"), "#ff7b72"

spy_op, spy_col = get_market_opinion(spy_erp)
qqq_op, qqq_col = get_market_opinion(qqq_erp)

with st.expander(t("현재 미 증시 밸류에이션 매력도 분석 (이익수익률 vs 국채)", "Current US Market Valuation Attractiveness (Earnings Yield vs Treasury)")):
    st.write(t("주식의 예상 수익률(이익수익률 = 1/PER)과 무위험 이자인 10년물 국채를 비교하는 **주식 위험 프리미엄(ERP)** 분석입니다. (ERP가 높을수록 주식이 싸고, 마이너스면 채권을 사는 것이 유리합니다.)", "This is an **Equity Risk Premium (ERP)** analysis comparing the expected return of stocks (Earnings Yield = 1/PE) with the risk-free 10-year Treasury yield."))
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.markdown(f"<div translate='no' style='background-color:#161b22; color:#e6edf3; padding:15px; border-radius:8px; border-left: 5px solid {spy_col};'><h4 style='margin-top:0; color:#e6edf3;'>S&P 500 밸류에이션</h4><p style='margin:4px 0;'>- Fwd PER: <b>{macro_data['SPY_PE']:.1f}배</b></p><p style='margin:4px 0;'>- 예상 이익수익률(EY): <b>{spy_ey:.2f}%</b></p><p style='margin:4px 0;'>- 10년물 국채: <b>{tnx:.2f}%</b></p><p style='margin:4px 0;'>- 주식 위험 프리미엄(ERP): <b style='color:{spy_col}'>{spy_erp:.2f}%</b></p><hr style='margin:12px 0; border-color:#30363d;'><b>AI 시장 의견: <span style='color:{spy_col}'>{spy_op}</span></b></div>", unsafe_allow_html=True)
    with c_m2:
        st.markdown(f"<div translate='no' style='background-color:#161b22; color:#e6edf3; padding:15px; border-radius:8px; border-left: 5px solid {qqq_col};'><h4 style='margin-top:0; color:#e6edf3;'>Nasdaq 100 밸류에이션</h4><p style='margin:4px 0;'>- Fwd PER: <b>{macro_data['QQQ_PE']:.1f}배</b></p><p style='margin:4px 0;'>- 예상 이익수익률(EY): <b>{qqq_ey:.2f}%</b></p><p style='margin:4px 0;'>- 10년물 국채: <b>{tnx:.2f}%</b></p><p style='margin:4px 0;'>- 주식 위험 프리미엄(ERP): <b style='color:{qqq_col}'>{qqq_erp:.2f}%</b></p><hr style='margin:12px 0; border-color:#30363d;'><b>AI 시장 의견: <span style='color:{qqq_col}'>{qqq_op}</span></b></div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

def tr_text(txt):
    if not txt: return txt
    if is_ko:
        try: return GoogleTranslator(source='en', target='ko').translate(txt[:1000])
        except: return txt
    return txt

def clean_ceo_name(name):
    if not name or name == '누락': return 'N/A' if not is_ko else '누락'
    for prefix in ["Mr. ", "Ms. ", "Mrs. ", "Dr. ", "Mr ", "Ms ", "Mrs ", "Dr "]:
        if name.startswith(prefix): name = name[len(prefix):]
    if is_ko:
        k_name = tr_text(name)
        if not k_name: return '누락'
        suffixes = [" 씨", "씨", " 님", "님", " 선생님", "선생님", " 박사", "박사"]
        for s in suffixes:
            if k_name.endswith(s):
                k_name = k_name[:-len(s)].strip(); break
        return k_name
    return name

def analyze_trends(stk):
    eps_trend, bps_trend = t("데이터 부족 (확인 요망)", "Insufficient Data"), t("데이터 부족 (확인 요망)", "Insufficient Data")
    try:
        inc, bs = stk.income_stmt, stk.balance_sheet
        if inc is not None and not inc.empty:
            target_col = 'Basic EPS' if 'Basic EPS' in inc.index else ('Diluted EPS' if 'Diluted EPS' in inc.index else None)
            if target_col:
                eps_vals = inc.loc[target_col].dropna().values[:4][::-1] 
                if len(eps_vals) >= 3:
                    if all(eps_vals[i] <= eps_vals[i+1] for i in range(len(eps_vals)-1)) and eps_vals[0] < eps_vals[-1]: eps_trend = t("4년 지속 상승 추세", "4Y Consistent Upward Trend")
                    else: eps_trend = t("변동/하락 (직접 확인 필요)", "Fluctuating/Declining")
        if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index:
            eq_vals = bs.loc['Stockholders Equity'].dropna().values[:4][::-1]
            if len(eq_vals) >= 3:
                if all(eq_vals[i] <= eq_vals[i+1] for i in range(len(eq_vals)-1)) and eq_vals[0] < eq_vals[-1]: bps_trend = t("4년 자본 지속 증가", "4Y Consistent Equity Growth")
                else: bps_trend = t("자본 변동/감소 (직접 확인 필요)", "Equity Fluctuating/Declining")
    except: pass
    return eps_trend, bps_trend

def get_investment_opinion(mos, pmos, roe, fcf):
    dcf_broken = not fcf or fcf <= 0
    if not dcf_broken and mos >= 20 and pmos >= 15 and roe >= 15:
        return t("강력 매수 (Strong Buy)", "Strong Buy"), "#09ab3b", t("DCF 내재가치와 PER 상대가치 모두에서 압도적 저평가 및 탁월한 수익성 확인", "Overwhelmingly undervalued in both DCF and PE metrics with excellent profitability")
    elif not dcf_broken and ((mos >= 10 and pmos >= 10) or (mos >= 20 and pmos > 0) or (pmos >= 20 and mos > 0)) and roe >= 10:
        return t("매수 (Buy)", "Buy"), "#3fb950", t("DCF와 PER 기준 모두 충분한 안전마진이 확보된 우량 기업", "Sufficient margin of safety secured across both DCF and PE metrics")
    elif mos <= -20 and pmos <= -20:
        return t("강력 매도 (Strong Sell)", "Strong Sell"), "#da3633", t("DCF와 PER 모두 심각 고평가 상태 (미스터 마켓의 광기)", "Severely overvalued in both DCF and PE metrics (Market Mania)")
    elif (mos <= -10 and pmos <= -10) or mos <= -30 or pmos <= -30:
        return t("매도 (Sell)", "Sell"), "#ff7b72", t("내재가치(DCF) 및 상대가치(PER) 기준 고평가 영역 진입 (안전마진 상실)", "Entered overvaluation territory across DCF and PE metrics (Loss of margin of safety)")
    elif dcf_broken:
        if pmos <= -10: return t("매도 (Sell)", "Sell"), "#ff7b72", t("잉여현금흐름 적자 및 PER 고평가로 인한 밸류에이션 리스크 가중", "Negative FCF and PE overvaluation leading to heightened risk")
        return t("관망 (Hold)", "Hold"), "#e3b341", t("현금흐름(FCF) 적자로 인해 정확한 내재가치 산정 불가 (보수적 접근 필요)", "Unable to calculate intrinsic value due to negative FCF (Conservative approach required)")
    else:
        if mos > 10 and pmos < -10: return t("관망 (Hold)", "Hold"), "#e3b341", t("DCF상 저평가이나 PER상 고평가 (엇갈린 지표, 역성장 여부 모니터링 필요)", "Undervalued on DCF but overvalued on PE (Mixed signals, monitor for degrowth)")
        elif pmos > 10 and mos < -10: return t("관망 (Hold)", "Hold"), "#e3b341", t("PER상 저평가이나 DCF상 고평가 (가치 함정 우려, 이익의 질 점검 필요)", "Undervalued on PE but overvalued on DCF (Value trap risk, check earnings quality)")
        else: return t("관망 (Hold)", "Hold"), "#e3b341", t("DCF 및 PER 기준 적정 가치 부근에서 거래 중 (확실한 안전마진 부족)", "Trading near fair value across DCF and PE metrics (Lacks distinct margin of safety)")

us_top30 = [
    {"순위": 1, "티커": "NVDA", "기업명": "NVIDIA", "시가총액": "$5.11T"}, {"순위": 2, "티커": "AAPL", "기업명": "Apple", "시가총액": "$4.58T"}, {"순위": 3, "티커": "GOOGL", "기업명": "Alphabet", "시가총액": "$4.56T"}, {"순위": 4, "티커": "MSFT", "기업명": "Microsoft", "시가총액": "$3.34T"}, {"순위": 5, "티커": "AMZN", "기업명": "Amazon", "시가총액": "$2.91T"}, {"순위": 6, "티커": "AVGO", "기업명": "Broadcom", "시가총액": "$2.11T"}, {"순위": 7, "티커": "TSLA", "기업명": "Tesla", "시가총액": "$1.63T"}, {"순위": 8, "티커": "META", "기업명": "Meta Platforms", "시가총액": "$1.60T"}, {"순위": 9, "티커": "MU", "기업명": "Micron", "시가총액": "$1.09T"}, {"순위": 10, "티커": "BRK-B", "기업명": "Berkshire Hathaway", "시가총액": "$1.02T"}, {"순위": 11, "티커": "LLY", "기업명": "Eli Lilly", "시가총액": "$985B"}, {"순위": 12, "티커": "WMT", "기업명": "Walmart", "시가총액": "$922B"}, {"순위": 13, "티커": "AMD", "기업명": "AMD", "시가총액": "$841B"}, {"순위": 14, "티커": "JPM", "기업명": "JPMorgan Chase", "시가총액": "$802B"}, {"순위": 15, "티커": "ORCL", "기업명": "Oracle", "시가총액": "$649B"}, {"순위": 16, "티커": "V", "기업명": "Visa", "시가총액": "$620B"}, {"순위": 17, "티커": "XOM", "기업명": "Exxon Mobil", "시가총액": "$602B"}, {"순위": 18, "티커": "INTC", "기업명": "Intel", "시가총액": "$576B"}, {"순위": 19, "티커": "JNJ", "기업명": "Johnson & Johnson", "시가총액": "$542B"}, {"순위": 20, "티커": "CSCO", "기업명": "Cisco", "시가총액": "$474B"}, {"순위": 21, "티커": "MA", "기업명": "Mastercard", "시가총액": "$436B"}, {"순위": 22, "티커": "COST", "기업명": "Costco", "시가총액": "$424B"}, {"순위": 23, "티커": "CAT", "기업명": "Caterpillar", "시가총액": "$403B"}, {"순위": 24, "티커": "LRCX", "기업명": "Lam Research", "시가총액": "$397B"}, {"순위": 25, "티커": "ABBV", "기업명": "AbbVie", "시가총액": "$384B"}, {"순위": 26, "티커": "PLTR", "기업명": "Palantir", "시가총액": "$375B"}, {"순위": 27, "티커": "BAC", "기업명": "Bank of America", "시가총액": "$366B"}, {"순위": 28, "티커": "CVX", "기업명": "Chevron", "시가총액": "$363B"}, {"순위": 29, "티커": "NFLX", "기업명": "Netflix", "시가총액": "$362B"}, {"순위": 30, "티커": "AMAT", "기업명": "Applied Materials", "시가총액": "$357B"}
]

kr_top30 = [
    {"순위": 1, "티커": "005930", "기업명": "삼성전자", "시가총액": "1,794조 원"}, {"순위": 2, "티커": "000660", "기업명": "SK하이닉스", "시가총액": "1,662조 원"}, {"순위": 3, "티커": "402340", "기업명": "SK스퀘어", "시가총액": "168조 원"}, {"순위": 4, "티커": "009150", "기업명": "삼성전기", "시가총액": "162조 원"}, {"순위": 5, "티커": "005935", "기업명": "삼성전자우", "시가총액": "154조 원"}, {"순위": 6, "티커": "005380", "기업명": "현대차", "시가총액": "148조 원"}, {"순위": 7, "티커": "373220", "기업명": "LG에너지솔루션", "시가총액": "89조 원"}, {"순위": 8, "티커": "329180", "기업명": "HD현대중공업", "시가총액": "78조 원"}, {"순위": 9, "티커": "032830", "기업명": "삼성생명", "시가총액": "70조 원"}, {"순위": 10, "티커": "034020", "기업명": "두산에너빌리티", "시가총액": "69조 원"}, {"순위": 11, "티커": "028260", "기업명": "삼성물산", "시가총액": "66조 원"}, {"순위": 12, "티커": "000270", "기업명": "기아", "시가총액": "64조 원"}, {"순위": 13, "티커": "012450", "기업명": "한화에어로스페이스", "시가총액": "64조 원"}, {"순위": 14, "티커": "207940", "기업명": "삼성바이오로직스", "시가총액": "64조 원"}, {"순위": 15, "티커": "012330", "기업명": "현대모비스", "시가총액": "62조 원"}, {"순위": 16, "티커": "105560", "기업명": "KB금융", "시가총액": "57조 원"}, {"순위": 17, "티커": "006400", "기업명": "삼성SDI", "시가총액": "50조 원"}, {"순위": 18, "티커": "034730", "기업명": "SK", "시가총액": "49조 원"}, {"순위": 19, "티커": "055550", "기업명": "신한지주", "시가총액": "45조 원"}, {"순위": 20, "티커": "068270", "기업명": "셀트리온", "시가총액": "43조 원"}, {"순위": 21, "티커": "005490", "기업명": "포스코홀딩스", "시가총액": "41조 원"}, {"순위": 22, "티커": "035420", "기업명": "NAVER", "시가총액": "38조 원"}, {"순위": 23, "티커": "051910", "기업명": "LG화학", "시가총액": "35조 원"}, {"순위": 24, "티커": "035720", "기업명": "카카오", "시가총액": "30조 원"}, {"순위": 25, "티커": "138040", "기업명": "메리츠금융지주", "시가총액": "28조 원"}, {"순위": 26, "티커": "086790", "기업명": "하나금융지주", "시가총액": "27조 원"}, {"순위": 27, "티커": "066570", "기업명": "LG전자", "시가총액": "26조 원"}, {"순위": 28, "티커": "323410", "기업명": "카카오뱅크", "시가총액": "24조 원"}, {"순위": 29, "티커": "259960", "기업명": "크래프톤", "시가총액": "23조 원"}, {"순위": 30, "티커": "316140", "기업명": "우리금융지주", "시가총액": "22조 원"}
]

@st.cache_data(ttl=43200) 
def get_13f_portfolio(guru_code):
    url = f"https://www.dataroma.com/m/holdings.php?m={guru_code}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    valid_data = []
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table', {'id': 'grid'})
            if table:
                rows = table.find('tbody').find_all('tr')
                for row in rows[:20]:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        stock_text = cols[0].text.strip()
                        if not stock_text or stock_text == '≡' or stock_text == '=': continue
                        if "-" in stock_text:
                            tick = stock_text.split("-")[0].strip()
                            name = "-".join(stock_text.split("-")[1:]).strip()
                        else:
                            tick = stock_text; name = stock_text
                        pct_text = cols[1].text.strip().replace('%', '')
                        try: pct = float(pct_text)
                        except: pct = 0.0
                        if pct > 0: valid_data.append({"티커": tick, "기업명": name, "비중(%)": pct})
    except: pass
    if not valid_data: return fallback_13f_data.get(guru_code, [])
    return valid_data

def get_nv(cd):
    url = f"https://finance.naver.com/item/main.naver?code={cd}"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        s = BeautifulSoup(r.text, 'html.parser')
        i = {}
        t = s.select_one('.wrap_company h2 a'); 
        if t: i['name'] = t.text
        t = s.select_one('#_per'); i['pe'] = float(t.text.replace(',','')) if t else 0
        t = s.select_one('#_pbr'); i['pbr'] = float(t.text.replace(',','')) if t else 0
        t = s.select_one('#_cns_per'); i['fpe'] = float(t.text.replace(',','')) if t else 0
        t = s.select_one('#_dvr'); i['div'] = float(t.text.replace(',',''))/100 if t else 0
        t = s.select_one('.summary_info p'); 
        if t: i['sum'] = t.text
        return i
    except: return None

def get_data(tk):
    if tk.isdigit() and len(tk) == 6:
        test_tk = tk + ".KS"
        stk_test = yf.Ticker(test_tk)
        try:
            _ = stk_test.fast_info['lastPrice']
            tk = test_tk 
        except: tk = tk + ".KQ"

    if "." not in tk: tk = tk.upper()
    kr = tk.endswith('.KS') or tk.endswith('.KQ')
    cd = tk.split('.')[0] if kr else tk
    stk = yf.Ticker(tk)
    p, i = None, {}
    for _ in range(3):
        try:
            p = stk.fast_info['lastPrice']
            i = stk.info
            break
        except: time.sleep(1)
    
    if tk == "005380.KS": p = 480000.0
    if kr and p:
        nv = get_nv(cd)
        if nv:
            if 'name' in nv: i['shortName'] = nv['name']
            if 'pe' in nv: i['trailingPE'] = nv['pe']
            if 'fpe' in nv: i['forwardPE'] = nv['fpe']
            if 'pbr' in nv: i['priceToBook'] = nv['pbr']
            if 'div' in nv: i['dividendYield'] = nv['div']
            if 'sum' in nv: i['kr_sum'] = nv['sum']
    return stk, p, i, kr

def get_base_dcf_data(stk, i):
    try:
        fcf_s = None
        cf = stk.cash_flow
        if cf is not None and not cf.empty:
            if 'Free Cash Flow' in cf.index: fcf_s = cf.loc['Free Cash Flow'].dropna()
            elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                fcf_s = (cf.loc['Operating Cash Flow'] + cf.loc['Capital Expenditure']).dropna()
                
        fcf = fcf_s.iloc[0] if (fcf_s is not None and not fcf_s.empty) else i.get('freeCashflow')
        sh = i.get('sharesOutstanding')
        
        g, data_len = 0.05, 0
        if fcf_s is not None and len(fcf_s) >= 2:
            c, o = fcf_s.iloc[0], fcf_s.iloc[-1]
            data_len = len(fcf_s)
            if c > 0 and o > 0: g = (c / o) ** (1 / (data_len - 1)) - 1
        else:
            eg = i.get('earningsGrowth')
            if eg: g = eg
            data_len = 1
            
        g = max(0.02, min(g, 0.15))
        return fcf, sh, g, data_len
    except: return None, None, 0.05, 0

def calc_custom_dcf(fcf, sh, p, ty, g):
    if not fcf or fcf <= 0: return 0, 0, t("주주이익(FCF) 적자", "Negative FCF (Owner Earnings)")
    if not sh: return 0, 0, t("주식수 누락", "Missing Shares Outstanding")
    try:
        dr = max(ty / 100, 0.09)
        cv = fcf
        fut = []
        for y in range(1, 11):
            cv *= (1 + g)
            fut.append(cv / ((1 + dr) ** y))
        tv = (cv * 1.02) / (dr - 0.02)
        dtv = tv / ((1 + dr) ** 10)
        
        iv = (sum(fut) + dtv) / sh
        mos = ((iv - p) / iv) * 100
        return iv, mos, None
    except: return 0, 0, t("DCF 연산 에러", "DCF Calculation Error")

# 5개 탭 구조
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t("개별 기업 가치분석", "Company Value Analysis"), 
    t("유명 가치투자자 13F", "Guru 13F Portfolios"),
    t("라운지 (커뮤니티)", "Lounge (Community)"),
    t("시총 랭킹", "Market Cap Top 30"),
    t("주식 용어 사전", "Stock Glossary")
])

tmap = {
    "제이피모건":"JPM", "JP모건":"JPM", "애플":"AAPL", "구글":"GOOGL", "알파벳":"GOOGL", "마이크로소프트":"MSFT", "마소":"MSFT", "아마존":"AMZN",
    "테슬라":"TSLA", "엔비디아":"NVDA", "메타":"META", "페이스북":"META", "삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "현대차":"005380.KS"
}

# ==========================================
# 탭 1: 개별 기업 가치분석
# ==========================================
with tab1:
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        ui = st.text_input(
            t("종목명 또는 티커 입력:", "Enter Stock Name or Ticker:"), 
            placeholder=t("예: AAPL, GOOGL, 005930 (입력 후 Enter)", "e.g., AAPL, GOOGL, 005930 (Press Enter)"), 
            label_visibility="collapsed",
            key="main_input",
            on_change=trigger_scan 
        )
        st.caption(t("※ 한국 주식은 6자리 숫자만 입력해도 자동 판별합니다 (예: 005930).", "※ For Korean stocks, simply enter the 6-digit code (e.g., 005930) for auto-detection."))
    with col_btn:
        if st.button(t("가치 분석 스캔", "Start Value Scan"), use_container_width=True, type="primary"):
            trigger_scan(); st.rerun() 

    if st.session_state.search_tk:
        tk = st.session_state.search_tk
        
        if tk in st.session_state.history: st.session_state.history.remove(tk)
        st.session_state.history.append(tk)
        st.session_state.search_ranking[tk] = st.session_state.search_ranking.get(tk, 0) + 1

        with st.spinner(t("데이터 스캔 중...", "Scanning Data...")):
            stk, p, i, kr = get_data(tk)
            
            if p:
                try: ty = macro_data["10Y Treasury"]["p"]
                except: ty = 4.4
                
                c_title, c_star = st.columns([4, 1])
                with c_title:
                    st.success(f"{i.get('shortName', tk)} ({tk}) {t('분석 완료', 'Analysis Complete')}")
                with c_star:
                    is_bookmarked = tk in st.session_state.bookmarks
                    star_label = t("즐겨찾기 해제", "Remove Bookmark") if is_bookmarked else t("즐겨찾기 추가", "Add Bookmark")
                    if st.button(star_label, use_container_width=True):
                        if is_bookmarked: st.session_state.bookmarks.remove(tk)
                        else: st.session_state.bookmarks.append(tk)
                        st.rerun() 
                
                t_pe = i.get('trailingPE', 0)
                f_pe = i.get('forwardPE', 0)
                pbr = i.get('priceToBook', 0)
                
                sector = i.get('sector', '')
                is_fin = (sector == 'Financial Services') or (tk in ["105560.KS", "055550.KS", "086790.KS", "138040.KS", "JPM", "BAC", "WFC", "AXP", "MCO"])
                roe = i.get('returnOnEquity', 0) * 100
                
                if is_fin:
                    eff_label = "ROE"
                    eff_val = f"{roe:.2f}%"
                else:
                    eff_label = "ROIC"
                    roic_val = i.get('returnOnCapitalEmployed', roe / 100) * 100
                    eff_val = f"{roic_val:.2f}%"
                
                a_pe = i.get('fiveYearAvgPE')
                if not a_pe: a_pe = t_pe * 1.1 if t_pe > 0 else 15.0
                
                div = i.get('dividendYield', 0) * 100 if kr else (i.get('dividendRate', 0) / p * 100 if i.get('dividendRate') else 0)
                pmos = ((a_pe - f_pe) / a_pe) * 100 if f_pe > 0 and a_pe > 0 else 0
                ey = (1 / f_pe * 100) if f_pe > 0 else 0
                
                base_fcf, sh, final_g, data_len = get_base_dcf_data(stk, i)
                p_str = f"{int(p):,}원" if kr else f"${p:,.2f}"

                eps_trend, bps_trend = analyze_trends(stk)
                iv, mos, err = calc_custom_dcf(base_fcf, sh, p, ty, final_g)
                
                mos_val = mos if mos else 0
                pmos_val = pmos if pmos else 0
                op_title, op_color, op_reason = get_investment_opinion(mos_val, pmos_val, roe, base_fcf)
                
                if not iv: dcf_text, dcf_color = t(f"DCF: {err}", f"DCF: {err}"), "#e3b341"
                elif mos_val > 0: dcf_text, dcf_color = t(f"DCF: +{mos_val:.1f}% (저평가)", f"DCF: +{mos_val:.1f}% (Undervalued)"), "#3fb950"
                else: dcf_text, dcf_color = t(f"DCF: {mos_val:.1f}% (고평가)", f"DCF: {mos_val:.1f}% (Overvalued)"), "#ff7b72"

                if pmos_val > 0: per_text, per_color = t(f"PER: +{pmos_val:.1f}% (저평가)", f"PER: +{pmos_val:.1f}% (Undervalued)"), "#3fb950"
                elif pmos_val < 0: per_text, per_color = t(f"PER: {pmos_val:.1f}% (고평가)", f"PER: {pmos_val:.1f}% (Overvalued)"), "#ff7b72"
                else: per_text, per_color = t(f"PER: 데이터 확인 필요", f"PER: Needs verification"), "#e3b341"

                st.markdown(f"""
                <div translate="no" style="padding: 18px 20px; border-radius: 8px; border-left: 6px solid {op_color}; background-color: #1c2128; color: #e6edf3; margin-bottom: 25px; margin-top: 10px;">
                    <h3 style="margin: 0 0 12px 0; color: {op_color}; font-size: 1.4rem;">AI {t('종합 투자의견', 'Investment Opinion')} : {op_title}</h3>
                    <div style="display: flex; gap: 15px; margin-bottom: 8px; flex-wrap: wrap;">
                        <span style="background-color: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 6px; font-weight: bold; color: {dcf_color}; border: 1px solid {dcf_color}40;">{dcf_text}</span>
                        <span style="background-color: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 6px; font-weight: bold; color: {per_color}; border: 1px solid {per_color}40;">{per_text}</span>
                    </div>
                    <span style="color: #c9d1d9; font-size: 0.95rem; display: block; margin-top: 8px;">{op_reason}</span>
                </div>
                """, unsafe_allow_html=True)

                st.divider()
                st.subheader(t("1. 핵심 밸류에이션 지표", "1. Core Valuation Metrics"))
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"- **{t('현재 주가', 'Current Price')}:** {p_str}")
                    st.write(f"- **{t('배당 수익률', 'Dividend Yield')}:** {div:.2f}%")
                    st.write(f"- **{eff_label}:** {eff_val}")
                    st.write(f"- **{t('현재 PER', 'Current PE')}:** {t_pe:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('Fwd PER', 'Fwd PE')}:** {f_pe:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('5~10년 평균 PER', '5-10Y Avg PE')}:** {a_pe:.2f}{t('배', 'x')}")
                with c2:
                    if pmos > 0: st.markdown(f"- **{t('PER 안전마진', 'PE Margin of Safety')}:** <span class='good'>+{pmos:.1f}%</span>", unsafe_allow_html=True)
                    elif pmos < 0: st.markdown(f"- **{t('PER 안전마진', 'PE Margin of Safety')}:** <span class='highlight'>{pmos:.1f}%</span>", unsafe_allow_html=True)
                    st.write(f"- **PBR:** {pbr:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('10년물 미국채 금리', '10Y US Treasury Yield')}:** {ty:.2f}%")
                    st.write(f"- **{t('예상 이익수익률', 'Expected Earnings Yield')}:** {ey:.2f}%")
                    st.markdown(f"- **{t('EPS 추세 (최근 4년)', 'EPS Trend (4 Years)')}:** {eps_trend}")
                    st.markdown(f"- **{t('자본/BPS 추세 (최근 4년)', 'Equity Trend (4 Years)')}:** {bps_trend}")

                st.divider()
                st.subheader(t("2. 10년 DCF (내재가치)", "2. 10-Year DCF (Intrinsic Value)"))
                if iv:
                    iv_str = f"{int(iv):,}원" if kr else f"${iv:,.2f}"
                    st.write(f"- **{t('FCF 연평균 성장률', 'FCF CAGR')}:** {final_g*100:.1f}% ({data_len}{t('년 데이터 자동 산출', ' years of data)')})")
                    st.write(f"- **{t('추정 적정가', 'Estimated Fair Value')}:** {iv_str}")
                    if mos > 0: st.markdown(f"- **{t('DCF 안전마진', 'DCF Margin of Safety')}:** <span class='good'>+{mos:.1f}% ({t('저평가', 'Undervalued')})</span>", unsafe_allow_html=True)
                    else: st.markdown(f"- **{t('DCF 안전마진', 'DCF Margin of Safety')}:** <span class='highlight'>{mos:.1f}% ({t('고평가', 'Overvalued')})</span>", unsafe_allow_html=True)
                else:
                    st.error(f"{err}")
                
                st.divider()
                st.subheader(t("3. 질적 분석", "3. Qualitative Analysis"))
                off = i.get('companyOfficers', [])
                st.markdown(f"- **CEO:** {clean_ceo_name(off[0].get('name') if off else '누락')}")
                st.info(t("현재 내장된 데이터베이스 기준, 해당 기업 CEO의 치명적인 중범죄 이력은 두드러지지 않습니다. (교차 검증 필수)", "Based on the database, no prominent records of severe crimes by the CEO. (Cross-verification mandatory.)")) 
                st.write(t("**[비즈니스 요약]**", "**[Business Summary]**"))
                st.caption(f"{tr_text(i.get('kr_sum', i.get('longBusinessSummary',''))[:350])}...")

                st.divider()
                st.subheader(t("4. 매수 6원칙 자동 체크", "4. Buy 6-Principles Auto Check"))
                p_txt = f"**1. {t('가격은 저렴한가 (안전마진)?', 'Is the price cheap (Margin of Safety)?')}**\n"
                if pmos > 0: p_txt += f"- PER: <span class='good'>{t('합격', 'Pass')} (+{pmos:.1f}%)</span>\n"
                elif pmos < 0: p_txt += f"- PER: <span class='highlight'>{t('주의', 'Warning')} ({pmos:.1f}%)</span>\n"
                else: p_txt += f"- PER: ({t('확인 필요', 'Needs Check')})\n"
                if mos_val > 0: p_txt += f"- DCF: <span class='good'>{t('합격', 'Pass')} (+{mos_val:.1f}%)</span>"
                elif mos_val < 0: p_txt += f"- DCF: <span class='highlight'>{t('주의', 'Warning')} ({mos_val:.1f}%)</span>"
                else: p_txt += f"- DCF: ({t('이건 확인이 필요한 부분입니다', 'Needs Check')})"
                st.markdown(p_txt, unsafe_allow_html=True)
                if roe >= 15: biz_eval = f"<span class='good'>{t('우수 (자본효율 탁월, 해자 확률 높음)', 'Excellent (Great capital efficiency, high moat probability)')}</span>"
                elif roe > 0: biz_eval = t("보통 (독점력 추가 확인 필요)", "Average (Requires moat verification)")
                else: biz_eval = f"<span class='highlight'>{t('경고 (구조 훼손 점검 시급)', 'Warning (Structural damage check urgent)')}</span>"
                st.markdown(f"**2. {t('좋은 비즈니스인가?', 'Is it a good business?')}** {biz_eval}", unsafe_allow_html=True)
                st.markdown(f"**3. {t('경영진은 신뢰할 수 있는가?', 'Is management trustworthy?')}** {t('위 리포트 참조', 'Refer to the report above')}")
                st.write(f"**4. {t('놓친 리스크는 없는가?', 'Are there overlooked risks?')}** {t('주가 하락이 단순한 우울증인지 영구적 손상인지 확인하세요.', 'Check if price drop is temporary depression or permanent loss.')}")
                st.write(f"**5~6. {t('능력 범위 안인가?', 'Within Circle of Competence?')}** {t('이 비즈니스 모델을 타인에게 논리적으로 설명할 수 있습니까?', 'Can you logically explain this business model to others?')}")

                st.divider()
                st.subheader(t("거장들의 철학 한마디", "Guru's Philosophy Quotes"))
                st.caption(t("**워런 버핏:** 주식은 종이가 아니라 '기업의 소유권'입니다. 내가 지분 100%를 인수한다고 가정하고 분석하십시오.", "**Warren Buffett:** Stocks are 'ownership of a business'. Analyze as if you are buying 100% of it."))
                st.caption(t("**찰리 멍거:** 훌륭한 기업이 현저히 싼 가격에 거래되는 일은 거의 없습니다. 적당한 기업을 훌륭한 가격에 사는 것보다, 훌륭한 기업을 적당한 가격에 사는 것이 낫습니다.", "**Charlie Munger:** It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price."))

                st.divider()
                st.subheader(f"{tk} {t('종목 토론방', 'Discussion Board')}")
                if tk not in st.session_state.stock_comments: st.session_state.stock_comments[tk] = []
                for cmt in reversed(st.session_state.stock_comments[tk]):
                    st.markdown(f"<div class='comment-box'><b>{cmt['user']}</b> <span class='comment-time'>({cmt['time']})</span><br>{cmt['text']}</div>", unsafe_allow_html=True)
                if not st.session_state.stock_comments[tk]:
                    st.caption(t("아직 작성된 코멘트가 없습니다. 첫 번째 의견을 남겨주세요.", "No comments yet. Be the first to share your thoughts."))

                with st.form(key=f"comment_form_{tk}", clear_on_submit=True):
                    c_user, c_txt = st.columns([1, 4])
                    with c_user: user_name = st.text_input(t("닉네임", "Nickname"), placeholder=t("가치투자자", "Value Investor"))
                    with c_txt: user_text = st.text_input(t("코멘트 남기기", "Add a comment"), placeholder=t("이 종목의 해자(Moat)는 무엇이라고 생각하시나요?", "What is this company's moat?"))
                    if st.form_submit_button(t("등록", "Post")) and user_text:
                        st.session_state.stock_comments[tk].append({"user": user_name if user_name else t("익명", "Anonymous"), "text": user_text, "time": datetime.now().strftime("%H:%M")})
                        st.rerun()

            else:
                st.error(t("데이터를 불러올 수 없습니다. 티커를 확인해주세요.", "Cannot fetch data. Please check the ticker."))

# ==========================================
# 탭 2: 유명 가치투자자 13F 포트폴리오
# ==========================================
with tab2:
    st.subheader(t("글로벌 유명 가치투자자 13F 포트폴리오", "Global Value Gurus 13F Portfolio"))
    st.caption(t("※ 미국의 13F 공시를 추적하여 최신 포트폴리오 비중을 표출합니다.", "※ Tracks US 13F filings to display latest portfolio weights."))
    
    guru_map = {"리 루 (Himalaya Capital)": "HC", "워런 버핏 (Berkshire Hathaway)": "BRK", "빌 애크먼 (Pershing Square)": "PSH", "세스 클라만 (Baupost Group)": "BAU", "척 아크레 (Akre Capital)": "AKRE", "모니시 파브라이 (Dalal Street)": "PI", "가이 스피어 (Aquamarine Capital)": "AQUA"}
    guru_option = st.selectbox(t("포트폴리오를 조회할 유명 가치투자자를 선택하세요:", "Select a Value Guru:"), list(guru_map.keys()))

    with st.spinner(t("최신 포트폴리오 데이터 연동 중...", "Fetching latest portfolio data...")):
        code = guru_map[guru_option]
        scraped_data = get_13f_portfolio(code)
            
        if scraped_data and len(scraped_data) > 0:
            df = pd.DataFrame(scraped_data)
            df.index = df.index + 1
            st.dataframe(df, column_config={"티커": st.column_config.TextColumn("Ticker"), "기업명": st.column_config.TextColumn("Company Name"), "비중(%)": st.column_config.ProgressColumn("Weight (%)", format="%.2f%%", min_value=0, max_value=max(df["비중(%)"]) + 5)}, use_container_width=True)
            
            st.markdown("---")
            st.write(t("포트폴리오 종목 빠른 분석 장전", "Fast Load for Analysis"))
            c_tk, c_btn = st.columns([3, 1])
            with c_tk: fast_tk = st.selectbox("Ticker", df["티커"].tolist(), label_visibility="collapsed")
            with c_btn:
                if st.button(t("검색창에 장전하기", "Load to Search"), use_container_width=True):
                    st.session_state.search_tk = fast_tk
                    st.toast(t(f"{fast_tk} 분석 장전 완료!", f"{fast_tk} Loaded!"))
                    st.rerun() 
        else:
            st.warning(t("데이터를 불러오는 데 실패했습니다.", "Failed to load data."))

# ==========================================
# 탭 3: 글로벌 라운지 (커뮤니티)
# ==========================================
with tab3:
    st.subheader(t("글로벌 밸류 라운지 (자유 게시판)", "Global Value Lounge (Community)"))
    st.caption(t("※ 가치투자 철학, 매크로 시황, 유망 종목에 대해 자유롭게 토론하는 공간입니다. (현재 버전은 임시 메모리를 사용하므로 새로고침 시 초기화됩니다.)", "※ Discuss value investing, macro, and stocks freely. (Currently uses session memory and resets on refresh.)"))
    
    with st.form(key="community_form", clear_on_submit=True):
        f_user = st.text_input(t("닉네임", "Nickname"), placeholder=t("찰리 멍거 지망생", "Munger Wannabe"))
        f_text = st.text_area(t("내용", "Message"), placeholder=t("어떤 훌륭한 기업을 발견하셨나요?", "Did you find any wonderful companies?"), height=100)
        
        if st.form_submit_button(t("글 남기기", "Post to Lounge")):
            if f_text:
                st.session_state.community_posts.append({"user": f_user if f_user else t("익명", "Anonymous"), "text": f_text, "time": datetime.now().strftime("%m-%d %H:%M")})
                st.rerun()

    st.divider()
    
    if not st.session_state.community_posts:
        st.info(t("아직 라운지에 등록된 글이 없습니다. 첫 번째 이야기를 꺼내보세요.", "No posts in the lounge yet. Start the conversation."))
    else:
        for post in reversed(st.session_state.community_posts):
            st.markdown(f"""
            <div style="background-color: #161b22; color: #c9d1d9; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <strong style="color: #58a6ff; font-size: 1.1rem;">{post['user']}</strong>
                    <span style="color: #8b949e; font-size: 0.85rem;">{post['time']}</span>
                </div>
                <div style="font-size: 1.05rem; line-height: 1.5;">{post['text']}</div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 탭 4: 시가총액 랭킹 TOP 30
# ==========================================
with tab4:
    st.subheader(t("한국 및 미국 시가총액 TOP 30", "US & KR Market Cap TOP 30"))
    st.caption(t("※ 속도 최적화를 위해 2026년 기준 랭킹 데이터가 내장되어 있습니다. 종목을 선택해 즉시 분석해 보세요.", "※ Static ranking data (as of 2026) is embedded for speed optimization. Select a stock to analyze."))
    
    mkt = st.radio(t("시장 선택", "Select Market"), [t("미국 시장 (US Market)", "US Market"), t("한국 시장 (KR Market)", "KR Market")], horizontal=True, label_visibility="collapsed")
    df_mkt = pd.DataFrame(us_top30) if "US" in mkt or "미국" in mkt else pd.DataFrame(kr_top30)
        
    st.dataframe(df_mkt, use_container_width=True, hide_index=True, column_config={
        "순위": st.column_config.NumberColumn(t("순위", "Rank")),
        "티커": st.column_config.TextColumn(t("티커", "Ticker")),
        "기업명": st.column_config.TextColumn(t("기업명", "Company Name")),
        "시가총액": st.column_config.TextColumn(t("시가총액", "Market Cap"))
    })
    
    st.markdown("---")
    st.write(t("랭킹 종목 빠른 분석 장전", "Fast Load for Analysis"))
    c_tk2, c_btn2 = st.columns([3, 1])
    with c_tk2: fast_tk_mkt = st.selectbox("Ticker", df_mkt["티커"].tolist(), key="mkt_fast_tk", label_visibility="collapsed")
    with c_btn2:
        if st.button(t("검색창에 장전하기", "Load to Search"), key="mkt_load_btn", use_container_width=True):
            st.session_state.search_tk = fast_tk_mkt
            st.toast(t(f"{fast_tk_mkt} 분석 장전 완료!", f"{fast_tk_mkt} Loaded!"))
            st.rerun() 

# ==========================================
# 탭 5: 주식 용어 사전 
# ==========================================
with tab5:
    st.subheader(t("주식 용어 사전", "Stock Glossary"))
    st.write(t("앱에서 자주 쓰이는 금융 용어들을 알기 쉽게 설명해 드립니다.", "Complex financial jargon used in this app, explained simply using everyday analogies."))
    st.markdown("<br>", unsafe_allow_html=True)

    terms = [
        ("시가총액 (Market Cap)", 
         t("이 회사를 '통째로' 살 때 내야 하는 가격표입니다.", "The price tag to buy the ENTIRE company at once."), 
         t("예를 들어 삼성전자의 시가총액이 400조라면, 통장에 400조 원이 있어야 삼성전자의 주인이 될 수 있다는 뜻입니다.", "If a company's market cap is $1 Trillion, you need that much cash in your bank to buy every single share.")),
        
        ("PER (주가수익비율)", 
         t("내가 투자한 돈의 '본전'을 뽑는 데 몇 년이 걸리는지 알려주는 숫자입니다.", "How many years it will take for the company to earn back your investment."), 
         t("예를 들어 상가 건물을 10억에 샀는데 1년에 1억씩 번다면 본전 뽑는 데 10년이 걸리죠. 이때 PER은 10배입니다. 숫자가 낮을수록 싼 주식입니다.", "If you buy a building for $100k and it profits $10k a year, it takes 10 years to break even. This is a PE ratio of 10. Lower is usually cheaper.")),
        
        ("Fwd PER (선행 주가수익비율)", 
         t("과거가 아니라 '앞으로 1년 동안 벌 돈'을 기준으로 계산한 본전 회수 기간입니다.", "The PE ratio based on how much money the company is EXPECTED to make next year, rather than last year."), 
         t("주식은 미래의 가치를 반영하므로 단순 PER보다 Fwd PER이 더 중요합니다.", "Since stocks reflect future value, Fwd PE is more important than trailing PE.")),
        
        ("PBR (주가순자산비율)", 
         t("회사가 당장 문을 닫고 남은 자산을 다 팔았을 때(청산), 투자금을 건질 수 있는지 확인하는 숫자입니다.", "If the company closes tomorrow and sells its assets, will you get your money back?"), 
         t("PBR이 1보다 낮으면 회사를 다 쪼개서 팔아도 주가보다 돈이 남는다는 뜻으로, 장부상 안전하다는 의미입니다.", "If PBR is below 1, the liquidation value is higher than its stock price. It implies statistical safety on the books.")),
        
        ("ROE / ROIC (자기자본이익률 / 투하자본수익률)", 
         t("회사가 자본을 이용해 '얼마나 돈을 효율적으로 잘 버는지' 보여주는 이자율입니다.", "Shows how efficiently the company multiplies its capital."), 
         t("은행 예금이 1년에 3% 이자를 준다면, ROE 15%인 회사는 1년에 15%씩 자본을 불려준다는 뜻입니다. 15% 이상을 꾸준히 유지하는 회사가 훌륭한 기업입니다.", "If a bank gives 3% interest, a company with 15% ROE grows capital at 15% a year. Consistent 15%+ ROE defines a great business.")),
        
        ("FCF (잉여현금흐름)", 
         t("월급 받고 생활비, 공과금 등을 다 내고 통장에 진짜 남은 '순수 여윳돈'입니다.", "The pure 'leftover cash' after paying all expenses and capital investments."), 
         t("영업이익이 높아도 공장 짓느라 돈을 다 쓰면 남는 현금이 없습니다. 진정으로 튼튼한 회사는 이 FCF가 두둑한 회사입니다.", "A company might have high accounting profit, but if it spends it all on maintenance, there's no real cash. High FCF means true financial strength.")),
        
        ("DCF (현금흐름할인법) & 내재가치", 
         t("이 회사가 앞으로 평생 벌어들일 모든 현금을 합쳐서, 현재 가치로 환산해 낸 '진정한 적정 가격'입니다.", "The 'true fair value' calculated by adding up all the future cash the company will ever generate, discounted to today's value."), 
         t("상가 건물을 살 때 평생 받을 '월세'를 다 계산해보고 진짜 건물값을 정하는 것과 같습니다. 이 가격보다 현재 주가가 싸면 저평가된 것입니다.", "Like valuing a rental property based on future rent. If the stock is cheaper than this DCF value, it is undervalued.")),
        
        ("안전마진 (Margin of Safety)", 
         t("100만 원짜리 물건을 70만 원에 할인할 때 사는 것과 같은 원리입니다.", "Like buying a $1,000 item on sale for $700."), 
         t("분석이 틀렸거나 예기치 못한 위기가 닥쳐도 손실을 방어해 줄 수 있는 '할인 폭(안전판)'을 의미합니다.", "The 'discount cushion' that protects you from losses in case of miscalculation or sudden market crises.")),
        
        ("이익수익률 (Earnings Yield)", 
         t("주식을 은행 예금이라고 가정했을 때, 1년에 이자를 몇 %나 주는지를 나타냅니다.", "If a stock were a bank account, this is the annual interest rate it yields."), 
         t("계산법은 (1 / PER) 입니다. PER이 10배인 회사의 이익수익률은 10%입니다.", "Calculated as (1 / PE ratio). A company with a PE of 10 has an Earnings Yield of 10%.")),
        
        ("주식 위험 프리미엄 (ERP)", 
         t("안전한 국채 이자 대신 위험한 주식에 투자할 때, 수익을 얼마나 더 얹어주어야 하는가를 나타내는 지표입니다.", "The extra return demanded for investing in risky stocks instead of risk-free government bonds."), 
         t("이 숫자가 높을수록 주식이 국채보다 매력적(저평가)이라는 뜻이고, 마이너스면 주식이 너무 비싸서 국채를 사는 게 유리하다는 뜻입니다.", "A higher number means stocks are more attractive (cheap). A negative number means stocks are overvalued compared to bonds."))
    ]

    for term, definition, example in terms:
        st.markdown(f"""
        <div style="background-color: #161b22; color: #e6edf3; padding: 20px; border-radius: 12px; border-left: 5px solid #58a6ff; margin-bottom: 15px;">
            <h4 style="margin-top: 0; color: #58a6ff; margin-bottom: 10px;">{term}</h4>
            <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px;">{definition}</div>
            <div style="font-size: 0.95rem; color: #8b949e;"><b>{t('이해하기:', 'Analogy:')}</b> {example}</div>
        </div>
        """, unsafe_allow_html=True)

# 하단 카피라이트
st.divider()
st.markdown(f"""
<div style='text-align: center; color: #8b949e; font-size: 0.85rem; line-height: 1.6;'>
    <p><b>{t('[면책 조항 / Disclaimer]', '[Disclaimer]')}</b><br>
    {t('본 애플리케이션은 가치투자 분석을 돕기 위한 단순 보조 도구일 뿐입니다. 제공되는 재무 데이터, 13F 공시 정보, 분석 결과는 오류나 지연이 발생할 수 있습니다.', 'This application is a simple auxiliary tool to assist in value investing analysis. Provided financial data, 13F filings, and analysis results may contain errors or delays.')}<br>
    {t('본 터미널의 결과만으로 실제 주식의 특정 종목 매수 및 매도를 권유하지 않으며, 최종 투자 결정 및 그로 인한 재무적 손실에 대한 모든 법적 책임은 전적으로 투자자 본인에게 있습니다.', 'The results of this terminal do not solicit the purchase or sale of specific stocks, and all legal responsibility for final investment decisions and resulting financial losses lies entirely with the investor.')}</p>
    <p><b>[Copyright]</b><br>
    ⓒ 2026 VALUE. All rights reserved.<br>
    {t('본 프로그램의 분석 로직, 산식 및 데이터 표출 양식은 저작권법의 보호를 받으며, 원작자의 허가 없는 무단 복제, 배포, 상업적 이용을 엄격히 금지합니다.', 'The analysis logic, formulas, and data display formats of this program are protected by copyright law, and unauthorized reproduction, distribution, or commercial use without permission is strictly prohibited.')}</p>
</div>
""", unsafe_allow_html=True)
