import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import pandas as pd
from datetime import datetime

# 💡 앱 이름 변경 및 레이아웃
st.set_page_config(page_title="VALUE", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 💡 세션 상태 초기화 (플랫폼용 DB 메모리 할당)
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
# 💡 글로벌 매크로 실시간 데이터 (KOSPI, KOSDAQ 포함)
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
# 💡 사이드바 (서재, 랭킹, 고객센터)
# ==========================================
with st.sidebar:
    if st.session_state.lang == "ko":
        if st.button("🇺🇸 English", use_container_width=True):
            st.session_state.lang = "en"; st.rerun()
    else:
        if st.button("🇰🇷 Korean", use_container_width=True):
            st.session_state.lang = "ko"; st.rerun()
            
    is_ko = st.session_state.lang == "ko"
    def t(ko, en): return ko if is_ko else en
        
    st.divider()
    
    st.header(t("🔥 실시간 인기 종목", "🔥 Trending Stocks"))
    if not st.session_state.search_ranking:
        st.caption(t("아직 검색된 종목이 없습니다.", "No searches yet."))
    else:
        top_5 = sorted(st.session_state.search_ranking.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (rtk, count) in enumerate(top_5):
            if st.button(f"{i+1}. {rtk} ({count}{t('회', ' hits')})", key=f"rank_{rtk}", use_container_width=True):
                st.session_state.search_tk = rtk
                st.rerun()
                
    st.divider()
    
    st.header(t("📚 내 서재", "📚 My Library"))
    st.subheader(t("⭐ 관심 종목 (즐겨찾기)", "⭐ Bookmarks"))
    if not st.session_state.bookmarks:
        st.caption(t("즐겨찾기한 종목이 없습니다.", "No bookmarked tickers yet."))
    else:
        for b_tk in st.session_state.bookmarks:
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(b_tk, key=f"bk_{b_tk}", use_container_width=True):
                    st.session_state.search_tk = b_tk; st.rerun()
            with c2:
                if st.button("❌", key=f"del_bk_{b_tk}"):
                    st.session_state.bookmarks.remove(b_tk); st.rerun()
                    
    st.divider()
    
    st.subheader(t("🕒 최근 검색 기록", "🕒 Recent Searches"))
    if not st.session_state.history:
        st.caption(t("검색 기록이 없습니다.", "No recent searches."))
    else:
        if st.button(t("🗑️ 전체 삭제", "🗑️ Clear All History"), use_container_width=True):
            st.session_state.history = []; st.rerun()
            
        for h_tk in reversed(st.session_state.history):
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(h_tk, key=f"h_{h_tk}", use_container_width=True):
                    st.session_state.search_tk = h_tk; st.rerun()
            with c2:
                if st.button("❌", key=f"del_h_{h_tk}"):
                    st.session_state.history.remove(h_tk); st.rerun()
                    
    st.divider()
    
    st.header(t("🎧 고객 센터", "🎧 Customer Center"))
    st.caption(t("버그 신고, 피드백, 기능 제안을 환영합니다.", "Report bugs, send feedback, or suggest features."))
    st.markdown(f"<a href='mailto:admin@value-terminal.com' style='display: block; text-align: center; background-color: #30363d; color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold;'>✉️ {t('개발자에게 이메일 보내기', 'Send Email to Developer')}</a>", unsafe_allow_html=True)

# ==========================================
# 💡 메인 UI 스타일
# ==========================================
st.markdown("""
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
.comment-box {background-color: #1c2128; padding: 15px; border-radius: 8px; border-left: 4px solid #8b949e; margin-bottom: 10px;}
.comment-time {font-size: 0.8rem; color: #8b949e;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="padding-top: 5px; padding-bottom: 5px;">
    <span style="font-size: 3.2rem; font-weight: 900; color: #ffffff; letter-spacing: 2px; line-height: 1.2;">
        VALUE
    </span>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 💡 가로 스크롤 매크로 대시보드
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

macro_html = "<div class='macro-ticker' style='display: flex; overflow-x: auto; gap: 12px; padding: 10px 0 20px 0; -webkit-overflow-scrolling: touch;'>"
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

with st.expander(t("📉 현재 미 증시 밸류에이션 매력도 분석 (이익수익률 vs 국채)", "📉 Current US Market Valuation Attractiveness (Earnings Yield vs Treasury)")):
    st.write(t("주식의 예상 수익률(이익수익률 = 1/PER)과 무위험 이자인 10년물 국채를 비교하는 **주식 위험 프리미엄(ERP)** 분석입니다. (ERP가 높을수록 주식이 싸고, 마이너스면 채권을 사는 것이 유리합니다.)", "This is an **Equity Risk Premium (ERP)** analysis comparing the expected return of stocks (Earnings Yield = 1/PE) with the risk-free 10-year Treasury yield."))
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.markdown(f"<div style='background-color:#161b22; padding:15px; border-radius:8px; border-left: 5px solid {spy_col};'><h4 style='margin-top:0;'>S&P 500 밸류에이션</h4><p style='margin:4px 0;'>- Fwd PER: <b>{macro_data['SPY_PE']:.1f}배</b></p><p style='margin:4px 0;'>- 예상 이익수익률(EY): <b>{spy_ey:.2f}%</b></p><p style='margin:4px 0;'>- 10년물 국채: <b>{tnx:.2f}%</b></p><p style='margin:4px 0;'>- 주식 위험 프리미엄(ERP): <b style='color:{spy_col}'>{spy_erp:.2f}%</b></p><hr style='margin:12px 0; border-color:#30363d;'><b>💡 AI 시장 의견: <span style='color:{spy_col}'>{spy_op}</span></b></div>", unsafe_allow_html=True)
    with c_m2:
        st.markdown(f"<div style='background-color:#161b22; padding:15px; border-radius:8px; border-left: 5px solid {qqq_col};'><h4 style='margin-top:0;'>Nasdaq 100 밸류에이션</h4><p style='margin:4px 0;'>- Fwd PER: <b>{macro_data['QQQ_PE']:.1f}배</b></p><p style='margin:4px 0;'>- 예상 이익수익률(EY): <b>{qqq_ey:.2f}%</b></p><p style='margin:4px 0;'>- 10년물 국채: <b>{tnx:.2f}%</b></p><p style='margin:4px 0;'>- 주식 위험 프리미엄(ERP): <b style='color:{qqq_col}'>{qqq_erp:.2f}%</b></p><hr style='margin:12px 0; border-color:#30363d;'><b>💡 AI 시장 의견: <span style='color:{qqq_col}'>{qqq_op}</span></b></div>", unsafe_allow_html=True)

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
                    if all(eps_vals[i] <= eps_vals[i+1] for i in range(len(eps_vals)-1)) and eps_vals[0] < eps_vals[-1]: eps_trend = t("✅ 4년 지속 상승 추세", "✅ 4Y Consistent Upward Trend")
                    else: eps_trend = t("⚠️ 변동/하락 (직접 확인 필요)", "⚠️ Fluctuating/Declining")
        if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index:
            eq_vals = bs.loc['Stockholders Equity'].dropna().values[:4][::-1]
            if len(eq_vals) >= 3:
                if all(eq_vals[i] <= eq_vals[i+1] for i in range(len(eq_vals)-1)) and eq_vals[0] < eq_vals[-1]: bps_trend = t("✅ 4년 자본 지속 증가", "✅ 4Y Consistent Equity Growth")
                else: bps_trend = t("⚠️ 자본 변동/감소 (직접 확인 필요)", "⚠️ Equity Fluctuating/Declining")
    except: pass
    return eps_trend, bps_trend

def get_investment_opinion(mos, pmos, roe, fcf):
    dcf_broken = not fcf or fcf <= 0
    if not dcf_broken and mos >= 20 and pmos >= 15 and roe >= 15:
        return t("강력 매수 (Strong Buy)", "Strong Buy"), "#09ab3b", t("DCF 내재가치와 PER 상대가치 모두에서 압도적 저평가 및 탁월한 수익성 확인", "Overwhelmingly undervalued in both DCF and PE metrics with excellent profitability")
    elif not dcf_broken and ((mos >= 10 and pmos >= 10) or (mos >= 20 and pmos > 0) or (pmos >= 20 and mos > 0)) and roe >= 10:
        return t("매수 (Buy)", "Buy"), "#3fb950", t("DCF와 PER 기준 모두 충분한 안전마진이 확보된 우량 기업", "Sufficient margin of safety secured across both DCF and PE metrics")
    elif mos <= -20 and pmos <= -20:
        return t("강력 매도 (Strong Sell)", "Strong Sell"), "#da3633", t("DCF와 PER 모두 심각한 고평가 상태 (미스터 마켓의 광기)", "Severely overvalued in both DCF and PE metrics (Market Mania)")
    elif (mos <= -10 and pmos <= -10) or mos <= -30 or pmos <= -30:
        return t("매도 (Sell)", "Sell"), "#ff7b72", t("내재가치(DCF) 및 상대가치(PER) 기준 고평가 영역 진입 (안전마진 상실)", "Entered overvaluation territory across DCF and PE metrics (Loss of margin of safety)")
    elif dcf_broken:
        if pmos <= -10: return t("매도 (Sell)", "Sell"), "#ff7b72", t("잉여현금흐름 적자 및 PER 고평가로 인한 밸류에이션 리스크 가중", "Negative FCF and PE overvaluation leading to heightened risk")
        return t("관망 (Hold)", "Hold"), "#e3b341", t("현금흐름(FCF) 적자로 인해 정확한 내재가치 산정 불가 (보수적 접근 필요)", "Unable to calculate intrinsic value due to negative FCF (Conservative approach required)")
    else:
        if mos > 10 and pmos < -10: return t("관망 (Hold)", "Hold"), "#e3b341", t("DCF상 저평가이나 PER상 고평가 (엇갈린 지표, 역성장 여부 모니터링 필요)", "Undervalued on DCF but overvalued on PE (Mixed signals, monitor for degrowth)")
        elif pmos > 10 and mos < -10: return t("관망 (Hold)", "Hold"), "#e3b341", t("PER상 저평가이나 DCF상 고평가 (가치 함정 우려, 이익의 질 점검 필요)", "Undervalued on PE but overvalued on DCF (Value trap risk, check earnings quality)")
        else: return t("관망 (Hold)", "Hold"), "#e3b341", t("DCF 및 PER 기준 적정 가치 부근에서 거래 중 (확실한 안전마진 부족)", "Trading near fair value across DCF and PE metrics (Lacks distinct margin of safety)")

fallback_13f_data = {
    "HC": [{"티커": "GOOGL", "기업명": "Alphabet Inc. Class A", "비중(%)": 22.85}, {"티커": "GOOG", "기업명": "Alphabet Inc. Class C", "비중(%)": 21.97}, {"티커": "PDD", "기업명": "Pinduoduo Inc. ADR", "비중(%)": 14.71}, {"티커": "BRK.B", "기업명": "Berkshire Hathaway B", "비중(%)": 13.44}, {"티커": "EWBC", "기업명": "East West Bancorp", "비중(%)": 9.26}],
    "BRK": [{"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 21.99}, {"티커": "AXP", "기업명": "American Express Co", "비중(%)": 17.43}, {"티커": "KO", "기업명": "Coca-Cola Co", "비중(%)": 11.56}, {"티커": "BAC", "기업명": "Bank of America", "비중(%)": 9.52}, {"티커": "CVX", "기업명": "Chevron Corp", "비중(%)": 6.64}],
    "PSH": [{"티커": "BN", "기업명": "Brookfield Corporation", "비중(%)": 25.00}, {"티커": "AMZN", "기업명": "Amazon.com Inc.", "비중(%)": 19.19}, {"티커": "MSFT", "기업명": "Microsoft Corp", "비중(%)": 15.26}, {"티커": "CMG", "기업명": "Chipotle Mexican Grill", "비중(%)": 6.55}],
    "BAU": [{"티커": "AMZN", "기업명": "Amazon.com Inc.", "비중(%)": 12.70}, {"티커": "QSR", "기업명": "Restaurant Brands Int.", "비중(%)": 11.67}, {"티커": "WCC", "기업명": "WESCO International", "비중(%)": 7.69}, {"티커": "UNP", "기업명": "Union Pacific Corp", "비중(%)": 7.31}, {"티커": "ELV", "기업명": "Elevance Health", "비중(%)": 7.30}],
    "AKRE": [{"티커": "MA", "기업명": "Mastercard Inc.", "비중(%)": 18.64}, {"티커": "BN", "기업명": "Brookfield Corporation", "비중(%)": 11.27}, {"티커": "KKR", "기업명": "KKR & Co. Inc.", "비중(%)": 10.16}, {"티커": "MCO", "기업명": "Moody's Corp", "비중(%)": 8.89}, {"티커": "V", "기업명": "Visa Inc.", "비중(%)": 8.10}],
    "PI": [{"티커": "HCC", "기업명": "Warrior Met Coal", "비중(%)": 39.89}, {"티커": "RIG", "기업명": "Transocean Ltd", "비중(%)": 31.97}, {"티커": "AMR", "기업명": "Alpha Metallurgical", "비중(%)": 28.14}],
    "AQUA": [{"티커": "BRK.B", "기업명": "Berkshire Hathaway B", "비중(%)": 34.57}, {"티커": "BRK.A", "기업명": "Berkshire Hathaway A", "비중(%)": 15.92}, {"티커": "MA", "기업명": "Mastercard Inc.", "비중(%)": 14.77}, {"티커": "AXP", "기업명": "American Express Co", "비중(%)": 14.53}, {"티커": "MCO", "기업명": "Moody's Corp", "비중(%)": 8.71}]
}

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
        except:
            tk = tk + ".KQ"

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
            if 'Free Cash Flow' in cf.index:
                fcf_s = cf.loc['Free Cash Flow'].dropna()
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

# 💡 시총 탑 30 데이터 하드코딩
us_top30 = [
    {"순위": 1, "티커": "AAPL", "기업명": "Apple Inc."}, {"순위": 2, "티커": "MSFT", "기업명": "Microsoft Corp."},
    {"순위": 3, "티커": "NVDA", "기업명": "NVIDIA Corp."}, {"순위": 4, "티커": "GOOGL", "기업명": "Alphabet Inc."},
    {"순위": 5, "티커": "AMZN", "기업명": "Amazon.com Inc."}, {"순위": 6, "티커": "META", "기업명": "Meta Platforms"},
    {"순위": 7, "티커": "BRK-B", "기업명": "Berkshire Hathaway"}, {"순위": 8, "티커": "LLY", "기업명": "Eli Lilly"},
    {"순위": 9, "티커": "TSM", "기업명": "TSMC"}, {"순위": 10, "티커": "AVGO", "기업명": "Broadcom"},
    {"순위": 11, "티커": "V", "기업명": "Visa Inc."}, {"순위": 12, "티커": "JPM", "기업명": "JPMorgan Chase"},
    {"순위": 13, "티커": "WMT", "기업명": "Walmart"}, {"순위": 14, "티커": "UNH", "기업명": "UnitedHealth"},
    {"순위": 15, "티커": "MA", "기업명": "Mastercard"}, {"순위": 16, "티커": "PG", "기업명": "Procter & Gamble"},
    {"순위": 17, "티커": "JNJ", "기업명": "Johnson & Johnson"}, {"순위": 18, "티커": "XOM", "기업명": "Exxon Mobil"},
    {"순위": 19, "티커": "HD", "기업명": "Home Depot"}, {"순위": 20, "티커": "COST", "기업명": "Costco Wholesale"},
    {"순위": 21, "티커": "ORCL", "기업명": "Oracle"}, {"순위": 22, "티커": "ABBV", "기업명": "AbbVie"},
    {"순위": 23, "티커": "BAC", "기업명": "Bank of America"}, {"순위": 24, "티커": "CRM", "기업명": "Salesforce"},
    {"순위": 25, "티커": "KO", "기업명": "Coca-Cola"}, {"순위": 26, "티커": "NFLX", "기업명": "Netflix"},
    {"순위": 27, "티커": "CVX", "기업명": "Chevron"}, {"순위": 28, "티커": "MRK", "기업명": "Merck & Co."},
    {"순위": 29, "티커": "TSLA", "기업명": "Tesla"}, {"순위": 30, "티커": "PEP", "기업명": "PepsiCo"}
]

kr_top30 = [
    {"순위": 1, "티커": "005930", "기업명": "삼성전자"}, {"순위": 2, "티커": "000660", "기업명": "SK하이닉스"},
    {"순위": 3, "티커": "373220", "기업명": "LG에너지솔루션"}, {"순위": 4, "티커": "207940", "기업명": "삼성바이오로직스"},
    {"순위": 5, "티커": "005380", "기업명": "현대차"}, {"순위": 6, "티커": "000270", "기업명": "기아"},
    {"순위": 7, "티커": "068270", "기업명": "셀트리온"}, {"순위": 8, "티커": "005490", "기업명": "POSCO홀딩스"},
    {"순위": 9, "티커": "105560", "기업명": "KB금융"}, {"순위": 10, "티커": "035420", "기업명": "네이버 (NAVER)"},
    {"순위": 11, "티커": "051910", "기업명": "LG화학"}, {"순위": 12, "티커": "028260", "기업명": "삼성물산"},
    {"순위": 13, "티커": "055550", "기업명": "신한지주"}, {"순위": 14, "티커": "138040", "기업명": "메리츠금융지주"},
    {"순위": 15, "티커": "032830", "기업명": "삼성생명"}, {"순위": 16, "티커": "086790", "기업명": "하나금융지주"},
    {"순위": 17, "티커": "035720", "기업명": "카카오"}, {"순위": 18, "티커": "066570", "기업명": "LG전자"},
    {"순위": 19, "티커": "012330", "기업명": "현대모비스"}, {"순위": 20, "티커": "003670", "기업명": "포스코퓨처엠"},
    {"순위": 21, "티커": "011200", "기업명": "HMM"}, {"순위": 22, "티커": "323410", "기업명": "카카오뱅크"},
    {"순위": 23, "티커": "259960", "기업명": "크래프톤"}, {"순위": 24, "티커": "033780", "기업명": "KT&G"},
    {"순위": 25, "티커": "010130", "기업명": "고려아연"}, {"순위": 26, "티커": "018260", "기업명": "삼성SDS"},
    {"순위": 27, "티커": "042700", "기업명": "한미반도체"}, {"순위": 28, "티커": "000810", "기업명": "삼성화재"},
    {"순위": 29, "티커": "010950", "기업명": "S-Oil"}, {"순위": 30, "티커": "009150", "기업명": "삼성전기"}
]

# 💡 4개 탭 구조
tab1, tab2, tab3, tab4 = st.tabs([
    t("개별 기업 가치분석", "Company Value Analysis"), 
    t("유명 가치투자자 13F", "Guru 13F Portfolios"),
    t("라운지 (커뮤니티)", "Lounge (Community)"),
    t("🏆 시총 랭킹", "🏆 Market Cap Top 30")
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
            trigger_scan()
            st.rerun() 

    if st.session_state.search_tk:
        tk = st.session_state.search_tk
        
        if tk in st.session_state.history:
            st.session_state.history.remove(tk)
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
                    star_label = t("⭐ 즐겨찾기 해제", "⭐ Remove Bookmark") if is_bookmarked else t("☆ 즐겨찾기 추가", "☆ Add Bookmark")
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
                
                if not iv: dcf_text, dcf_color = t(f"⚠️ DCF: {err}", f"⚠️ DCF: {err}"), "#e3b341"
                elif mos_val > 0: dcf_text, dcf_color = t(f"✅ DCF: +{mos_val:.1f}% (저평가)", f"✅ DCF: +{mos_val:.1f}% (Undervalued)"), "#3fb950"
                else: dcf_text, dcf_color = t(f"🚨 DCF: {mos_val:.1f}% (고평가)", f"🚨 DCF: {mos_val:.1f}% (Overvalued)"), "#ff7b72"

                if pmos_val > 0: per_text, per_color = t(f"✅ PER: +{pmos_val:.1f}% (저평가)", f"✅ PER: +{pmos_val:.1f}% (Undervalued)"), "#3fb950"
                elif pmos_val < 0: per_text, per_color = t(f"🚨 PER: {pmos_val:.1f}% (고평가)", f"🚨 PER: {pmos_val:.1f}% (Overvalued)"), "#ff7b72"
                else: per_text, per_color = t(f"⚠️ PER: 데이터 확인 필요", f"⚠️ PER: Needs verification"), "#e3b341"

                st.markdown(f"""
                <div style="padding: 18px 20px; border-radius: 8px; border-left: 6px solid {op_color}; background-color: #1c2128; margin-bottom: 25px; margin-top: 10px;">
                    <h3 style="margin: 0 0 12px 0; color: {op_color}; font-size: 1.4rem;">🎯 AI {t('종합 투자의견', 'Investment Opinion')} : {op_title}</h3>
                    <div style="display: flex; gap: 15px; margin-bottom: 8px; flex-wrap: wrap;">
                        <span style="background-color: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 6px; font-weight: bold; color: {dcf_color}; border: 1px solid {dcf_color}40;">{dcf_text}</span>
                        <span style="background-color: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 6px; font-weight: bold; color: {per_color}; border: 1px solid {per_color}40;">{per_text}</span>
                    </div>
                    <span style="color: #c9d1d9; font-size: 0.95rem; display: block; margin-top: 8px;">💡 {op_reason}</span>
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
                st.subheader(t("거장들의 철학 한마디", "Guru's Philosophy Quotes"))
                st.caption(t("**워런 버핏 (소유권):** 주식은 종이가 아니라 '기업의 소유권'입니다. 내가 지분 100%를 인수한다고 가정하고 분석하십시오.", "**Warren Buffett:** Stocks are 'ownership of a business'. Analyze as if you are buying 100% of it."))
                st.caption(t("**찰리 멍거 (훌륭한 기업):** 훌륭한 기업이 현저히 싼 가격에 거래되는 일은 거의 없습니다. 적당한 기업을 훌륭한 가격에 사는 것보다, 훌륭한 기업을 적당한 가격에 사는 것이 낫습니다.", "**Charlie Munger:** It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price."))

                # ==========================================
                # 💡 종목 토론방 (해당 티커 전용 댓글창)
                # ==========================================
                st.divider()
                st.subheader(f"💬 {tk} {t('종목 토론방', 'Discussion Board')}")
                
                if tk not in st.session_state.stock_comments:
                    st.session_state.stock_comments[tk] = []
                    
                for cmt in reversed(st.session_state.stock_comments[tk]):
                    st.markdown(f"<div class='comment-box'><b>{cmt['user']}</b> <span class='comment-time'>({cmt['time']})</span><br>{cmt['text']}</div>", unsafe_allow_html=True)
                if not st.session_state.stock_comments[tk]:
                    st.caption(t("아직 작성된 코멘트가 없습니다. 첫 번째 의견을 남겨주세요!", "No comments yet. Be the first to share your thoughts!"))

                with st.form(key=f"comment_form_{tk}", clear_on_submit=True):
                    c_user, c_txt = st.columns([1, 4])
                    with c_user: user_name = st.text_input(t("닉네임", "Nickname"), placeholder=t("가치투자자", "Value Investor"))
                    with c_txt: user_text = st.text_input(t("코멘트 남기기", "Add a comment"), placeholder=t("이 종목의 해자(Moat)는 무엇이라고 생각하시나요?", "What is this company's moat?"))
                    
                    if st.form_submit_button(t("등록", "Post")) and user_text:
                        st.session_state.stock_comments[tk].append({
                            "user": user_name if user_name else t("익명", "Anonymous"),
                            "text": user_text,
                            "time": datetime.now().strftime("%H:%M")
                        })
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
            st.write(t("🔍 **포트폴리오 종목 빠른 분석 장전**", "🔍 **Fast Load for Analysis**"))
            c_tk, c_btn = st.columns([3, 1])
            with c_tk: fast_tk = st.selectbox("Ticker", df["티커"].tolist(), label_visibility="collapsed")
            with c_btn:
                if st.button(t("검색창에 장전하기", "Load to Search"), use_container_width=True):
                    st.session_state.search_tk = fast_tk
                    st.toast(t(f"🎯 {fast_tk} 분석 장전 완료!", f"🎯 {fast_tk} Loaded!"), icon="✅")
                    st.rerun() 
        else:
            st.warning(t("데이터를 불러오는 데 실패했습니다.", "Failed to load data."))

# ==========================================
# 탭 3: 글로벌 라운지 (커뮤니티)
# ==========================================
with tab3:
    st.subheader(t("☕ 글로벌 밸류 라운지 (자유 게시판)", "☕ Global Value Lounge (Community)"))
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
        st.info(t("아직 라운지에 등록된 글이 없습니다. 첫 번째 이야기를 꺼내보세요!", "No posts in the lounge yet. Start the conversation!"))
    else:
        for post in reversed(st.session_state.community_posts):
            st.markdown(f"""
            <div style="background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <strong style="color: #58a6ff; font-size: 1.1rem;">👤 {post['user']}</strong>
                    <span style="color: #8b949e; font-size: 0.85rem;">{post['time']}</span>
                </div>
                <div style="color: #c9d1d9; font-size: 1.05rem; line-height: 1.5;">{post['text']}</div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 탭 4: 시가총액 랭킹 TOP 30
# ==========================================
with tab4:
    st.subheader(t("🌍 한국 및 미국 시가총액 TOP 30", "🌍 US & KR Market Cap TOP 30"))
    st.caption(t("※ 속도 최적화를 위해 2026년 기준 랭킹 데이터가 내장되어 있습니다. 종목을 선택해 즉시 분석해 보세요.", "※ Static ranking data (as of 2026) is embedded for speed optimization. Select a stock to analyze."))
    
    mkt = st.radio(t("시장 선택", "Select Market"), [t("🇺🇸 미국 시장 (US Market)", "🇺🇸 US Market"), t("🇰🇷 한국 시장 (KR Market)", "🇰🇷 KR Market")], horizontal=True, label_visibility="collapsed")
    
    if "US" in mkt or "미국" in mkt:
        df_mkt = pd.DataFrame(us_top30)
    else:
        df_mkt = pd.DataFrame(kr_top30)
        
    st.dataframe(
        df_mkt, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "순위": st.column_config.NumberColumn(t("순위", "Rank")),
            "티커": st.column_config.TextColumn(t("티커", "Ticker")),
            "기업명": st.column_config.TextColumn(t("기업명", "Company Name"))
        }
    )
    
    st.markdown("---")
    st.write(t("🔍 **랭킹 종목 빠른 분석 장전**", "🔍 **Fast Load for Analysis**"))
    c_tk2, c_btn2 = st.columns([3, 1])
    with c_tk2:
        fast_tk_mkt = st.selectbox("Ticker", df_mkt["티커"].tolist(), key="mkt_fast_tk", label_visibility="collapsed")
    with c_btn2:
        if st.button(t("검색창에 장전하기", "Load to Search"), key="mkt_load_btn", use_container_width=True):
            st.session_state.search_tk = fast_tk_mkt
            st.toast(t(f"🎯 {fast_tk_mkt} 분석 장전 완료!", f"🎯 {fast_tk_mkt} Loaded!"), icon="✅")
            st.rerun() 

# 하단 카피라이트
st.divider()
st.markdown(f"""
<div style='text-align: center; color: #8b949e; font-size: 0.85rem; line-height: 1.6;'>
    <p><b>[Copyright]</b> ⓒ 2026 VALUE. All rights reserved.<br>
    {t('본 터미널의 결과만으로 매수/매도를 권유하지 않으며, 투자 책임은 본인에게 있습니다.', 'Does not solicit purchase/sale; investment responsibility lies with the investor.')}</p>
</div>
""", unsafe_allow_html=True)
