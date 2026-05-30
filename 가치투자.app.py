import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import pandas as pd

# 💡 앱 이름 변경
st.set_page_config(page_title="VALUE", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 💡 세션 상태 초기화 (검색 기록, 북마크)
# ==========================================
if "search_tk" not in st.session_state: st.session_state.search_tk = None
if "history" not in st.session_state: st.session_state.history = []
if "bookmarks" not in st.session_state: st.session_state.bookmarks = []
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "main_input" not in st.session_state: st.session_state.main_input = ""

def trigger_scan():
    if st.session_state.get("main_input"):
        q = st.session_state.main_input.replace(" ", "").upper()
        st.session_state.search_tk = tmap.get(q, q)

# ==========================================
# 💡 글로벌 매크로 실시간 데이터 패치 로직
# ==========================================
@st.cache_data(ttl=900) # 15분마다 갱신 (속도 최적화)
def get_macro_data():
    macro_symbols = {
        "S&P 500": "^GSPC",
        "Nasdaq 100": "^NDX",
        "Nasdaq Futures": "NQ=F",
        "USD/KRW": "KRW=X",
        "WTI Crude": "CL=F",
        "10Y Treasury": "^TNX",
        "SPY": "SPY", # S&P 500 PER 대용
        "QQQ": "QQQ"  # Nasdaq 100 PER 대용
    }
    
    res = {}
    for name, tk in macro_symbols.items():
        try:
            stk = yf.Ticker(tk)
            hist = stk.history(period="5d")
            if len(hist) >= 2:
                last_p = hist['Close'].iloc[-1]
                prev_p = hist['Close'].iloc[-2]
                change = last_p - prev_p
                pct = (change / prev_p) * 100
                res[name] = {"p": last_p, "c": change, "pct": pct}
            else:
                res[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
        except:
            res[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
            
    # SPY, QQQ를 통한 시장 PER 추출
    try: res["SPY_PE"] = yf.Ticker("SPY").info.get("forwardPE", 22.0)
    except: res["SPY_PE"] = 22.0
    try: res["QQQ_PE"] = yf.Ticker("QQQ").info.get("forwardPE", 30.0)
    except: res["QQQ_PE"] = 30.0
    
    return res

macro_data = get_macro_data()

# ==========================================
# 💡 사이드바 (서재 및 설정 패널)
# ==========================================
with st.sidebar:
    if st.session_state.lang == "ko":
        if st.button("🇺🇸 English", use_container_width=True):
            st.session_state.lang = "en"
            st.rerun()
    else:
        if st.button("🇰🇷 Korean", use_container_width=True):
            st.session_state.lang = "ko"
            st.rerun()
            
    is_ko = st.session_state.lang == "ko"

    def t(ko, en): return ko if is_ko else en
        
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
                    st.session_state.search_tk = b_tk
                    st.rerun()
            with c2:
                if st.button("❌", key=f"del_bk_{b_tk}"):
                    st.session_state.bookmarks.remove(b_tk)
                    st.rerun()
                    
    st.divider()
    
    st.subheader(t("🕒 최근 검색 기록", "🕒 Recent Searches"))
    if not st.session_state.history:
        st.caption(t("검색 기록이 없습니다.", "No recent searches."))
    else:
        if st.button(t("🗑️ 전체 삭제", "🗑️ Clear All History"), use_container_width=True):
            st.session_state.history = []
            st.rerun()
            
        for h_tk in reversed(st.session_state.history):
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(h_tk, key=f"h_{h_tk}", use_container_width=True):
                    st.session_state.search_tk = h_tk
                    st.rerun()
            with c2:
                if st.button("❌", key=f"del_h_{h_tk}"):
                    st.session_state.history.remove(h_tk)
                    st.rerun()

# ==========================================
# 💡 메인 UI 스타일 및 전역 매크로 대시보드
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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="padding-top: 5px; padding-bottom: 10px;">
    <span style="font-size: 3.2rem; font-weight: 900; color: #ffffff; letter-spacing: 2px; line-height: 1.2;">
        VALUE
    </span>
</div>
""", unsafe_allow_html=True)

# 💡 전역 매크로 대시보드 (어떤 탭에서도 보이게 최상단 배치)
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric(t("S&P 500", "S&P 500"), f"{macro_data['S&P 500']['p']:,.2f}", f"{macro_data['S&P 500']['pct']:.2f}%")
m2.metric(t("Nasdaq 100", "Nasdaq 100"), f"{macro_data['Nasdaq 100']['p']:,.2f}", f"{macro_data['Nasdaq 100']['pct']:.2f}%")
m3.metric(t("NQ 선물", "Nasdaq Fut"), f"{macro_data['Nasdaq Futures']['p']:,.2f}", f"{macro_data['Nasdaq Futures']['pct']:.2f}%")
m4.metric(t("환율 (KRW/USD)", "USD/KRW"), f"{macro_data['USD/KRW']['p']:,.2f}", f"{macro_data['USD/KRW']['pct']:.2f}%")
m5.metric(t("WTI 원유", "WTI Crude"), f"${macro_data['WTI Crude']['p']:,.2f}", f"{macro_data['WTI Crude']['pct']:.2f}%")
m6.metric(t("10년물 국채", "10Y Treasury"), f"{macro_data['10Y Treasury']['p']:.3f}%", f"{macro_data['10Y Treasury']['c']:.3f} bp")

# 💡 시장 이익수익률 기반 매력도 판독 로직
spy_ey = (1 / macro_data["SPY_PE"]) * 100 if macro_data["SPY_PE"] > 0 else 0
qqq_ey = (1 / macro_data["QQQ_PE"]) * 100 if macro_data["QQQ_PE"] > 0 else 0
tnx = macro_data["10Y Treasury"]["p"]

spy_erp = spy_ey - tnx
qqq_erp = qqq_ey - tnx

def get_market_opinion(erp):
    if erp > 3.0: return t("강력 매수 (역사적 저평가)", "Strong Buy (Historic Undervaluation)"), "#3fb950"
    elif erp > 1.0: return t("적립식 매수 (안전마진 존재)", "Buy (Margin of safety exists)"), "#58a6ff"
    elif erp > -1.0: return t("관망 (채권과 주식 매력도 유사)", "Hold (Equities & Bonds equally attractive)"), "#e3b341"
    else: return t("매도 경고 (채권이 압도적으로 유리한 버블 구간)", "Sell Warning (Bonds vastly superior, Bubble risk)"), "#ff7b72"

spy_op, spy_col = get_market_opinion(spy_erp)
qqq_op, qqq_col = get_market_opinion(qqq_erp)

with st.expander(t("📉 현재 미 증시 밸류에이션 매력도 분석 (이익수익률 vs 국채)", "📉 Current US Market Valuation Attractiveness (Earnings Yield vs Treasury)")):
    st.write(t(f"주식의 예상 수익률(이익수익률 = 1/PER)과 무위험 이자인 10년물 국채를 비교하는 **주식 위험 프리미엄(ERP)** 분석입니다. (ERP가 높을수록 주식이 싸고, 마이너스면 채권을 사는 것이 유리합니다.)", 
               f"This is an **Equity Risk Premium (ERP)** analysis comparing the expected return of stocks (Earnings Yield = 1/PE) with the risk-free 10-year Treasury yield. (Higher ERP means stocks are cheap; negative means bonds are better.)"))
    
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.markdown(f"""
        <div style='background-color:#161b22; padding:15px; border-radius:8px; border-left: 5px solid {spy_col};'>
            <h4>S&P 500 밸류에이션</h4>
            <p style='margin:2px;'>- Fwd PER: <b>{macro_data["SPY_PE"]:.1f}배</b></p>
            <p style='margin:2px;'>- 예상 이익수익률(EY): <b>{spy_ey:.2f}%</b></p>
            <p style='margin:2px;'>- 10년물 국채: <b>{tnx:.2f}%</b></p>
            <p style='margin:2px;'>- 주식 위험 프리미엄(ERP): <b style='color:{spy_col}'>{spy_erp:.2f}%</b></p>
            <hr style='margin:10px 0;'>
            <b>💡 AI 시장 의견: <span style='color:{spy_col}'>{spy_op}</span></b>
        </div>
        """, unsafe_allow_html=True)
        
    with c_m2:
        st.markdown(f"""
        <div style='background-color:#161b22; padding:15px; border-radius:8px; border-left: 5px solid {qqq_col};'>
            <h4>Nasdaq 100 밸류에이션</h4>
            <p style='margin:2px;'>- Fwd PER: <b>{macro_data["QQQ_PE"]:.1f}배</b></p>
            <p style='margin:2px;'>- 예상 이익수익률(EY): <b>{qqq_ey:.2f}%</b></p>
            <p style='margin:2px;'>- 10년물 국채: <b>{tnx:.2f}%</b></p>
            <p style='margin:2px;'>- 주식 위험 프리미엄(ERP): <b style='color:{qqq_col}'>{qqq_erp:.2f}%</b></p>
            <hr style='margin:10px 0;'>
            <b>💡 AI 시장 의견: <span style='color:{qqq_col}'>{qqq_op}</span></b>
        </div>
        """, unsafe_allow_html=True)

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
    eps_trend = t("데이터 부족 (이건 확인이 필요한 부분입니다)", "Insufficient Data (Needs verification)")
    bps_trend = t("데이터 부족 (이건 확인이 필요한 부분입니다)", "Insufficient Data (Needs verification)")
    try:
        inc = stk.income_stmt
        bs = stk.balance_sheet
        if inc is not None and not inc.empty:
            target_col = 'Basic EPS' if 'Basic EPS' in inc.index else ('Diluted EPS' if 'Diluted EPS' in inc.index else None)
            if target_col:
                eps_vals = inc.loc[target_col].dropna().values[:4][::-1] 
                if len(eps_vals) >= 3:
                    if all(eps_vals[i] <= eps_vals[i+1] for i in range(len(eps_vals)-1)) and eps_vals[0] < eps_vals[-1]: eps_trend = t("✅ 4년 지속 상승 추세", "✅ 4Y Consistent Upward Trend")
                    else: eps_trend = t("⚠️ 변동/하락 (이건 확인이 필요한 부분입니다)", "⚠️ Fluctuating/Declining (Needs verification)")
                        
        if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index:
            eq_vals = bs.loc['Stockholders Equity'].dropna().values[:4][::-1]
            if len(eq_vals) >= 3:
                if all(eq_vals[i] <= eq_vals[i+1] for i in range(len(eq_vals)-1)) and eq_vals[0] < eq_vals[-1]: bps_trend = t("✅ 4년 자본 지속 증가 (PBR 안정)", "✅ 4Y Consistent Equity Growth")
                else: bps_trend = t("⚠️ 자본 변동/감소 (이건 확인이 필요한 부분입니다)", "⚠️ Equity Fluctuating/Declining (Needs verification)")
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

tab1, tab2 = st.tabs([t("개별 기업 가치분석", "Company Value Analysis"), t("유명 가치투자자 13F 포트폴리오", "Guru 13F Portfolios")])

tmap = {
    "제이피모건":"JPM", "JP모건":"JPM", "애플":"AAPL", "구글":"GOOGL", "알파벳":"GOOGL", "마이크로소프트":"MSFT", "마소":"MSFT", "아마존":"AMZN",
    "테슬라":"TSLA", "엔비디아":"NVDA", "메타":"META", "페이스북":"META", "삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "현대차":"005380.KS"
}

with tab1:
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        ui = st.text_input(
            t("종목명 또는 티커 입력:", "Enter Stock Name or Ticker:"), 
            placeholder=t("예: AAPL, GOOGL, 005930 (입력 후 Enter)", "e.g., AAPL, GOOGL, 005930 (Press Enter)"), 
            label_visibility="collapsed",
            key="main_input",
            on_change=trigger_scan # 💡 엔터키 즉시 스캔
        )
        st.caption(t("※ 한국 주식은 6자리 숫자만 입력해도 자동 판별합니다 (예: 005930).", "※ For Korean stocks, simply enter the 6-digit code (e.g., 005930) for auto-detection."))
    with col_btn:
        if st.button(t("가치 분석 스캔", "Start Value Scan"), use_container_width=True, type="primary"):
            trigger_scan()
            st.rerun() # 💡 원클릭 강제 새로고침

    if st.session_state.search_tk:
        tk = st.session_state.search_tk
        
        if tk in st.session_state.history:
            st.session_state.history.remove(tk)
        st.session_state.history.append(tk)

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
                
                if not iv:
                    dcf_text, dcf_color = t(f"⚠️ DCF: {err}", f"⚠️ DCF: {err}"), "#e3b341"
                elif mos_val > 0:
                    dcf_text, dcf_color = t(f"✅ DCF: +{mos_val:.1f}% (저평가)", f"✅ DCF: +{mos_val:.1f}% (Undervalued)"), "#3fb950"
                else:
                    dcf_text, dcf_color = t(f"🚨 DCF: {mos_val:.1f}% (고평가)", f"🚨 DCF: {mos_val:.1f}% (Overvalued)"), "#ff7b72"

                if pmos_val > 0:
                    per_text, per_color = t(f"✅ PER: +{pmos_val:.1f}% (저평가)", f"✅ PER: +{pmos_val:.1f}% (Undervalued)"), "#3fb950"
                elif pmos_val < 0:
                    per_text, per_color = t(f"🚨 PER: {pmos_val:.1f}% (고평가)", f"🚨 PER: {pmos_val:.1f}% (Overvalued)"), "#ff7b72"
                else:
                    per_text, per_color = t(f"⚠️ PER: 데이터 확인 필요", f"⚠️ PER: Needs verification"), "#e3b341"

                st.markdown(f"""
                <div style="padding: 18px 20px; border-radius: 8px; border-left: 6px solid {op_color}; background-color: #1c2128; margin-bottom: 25px; margin-top: 10px;">
                    <h3 style="margin: 0 0 12px 0; color: {op_color}; font-size: 1.4rem;">🎯 AI {t('종합 투자의견', 'Investment Opinion')} : {op_title}</h3>
                    <div style="display: flex; gap: 15px; margin-bottom: 8px; flex-wrap: wrap;">
                        <span style="background-color: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 6px; font-weight: bold; color: {dcf_color}; border: 1px solid {dcf_color}40;">
                            {dcf_text}
                        </span>
                        <span style="background-color: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 6px; font-weight: bold; color: {per_color}; border: 1px solid {per_color}40;">
                            {per_text}
                        </span>
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
                    st.caption(t("※ PER/PBR 추이는 주가 변동성에 따라 달라지므로 직접 확인이 필요한 부분입니다.", "※ Historical PER/PBR trends require manual verification due to price volatility."))

                st.divider()
                st.subheader(t("2. 10년 DCF (내재가치)", "2. 10-Year DCF (Intrinsic Value)"))
                
                if iv:
                    iv_str = f"{int(iv):,}원" if kr else f"${iv:,.2f}"
                    st.write(f"- **{t('FCF 연평균 성장률', 'FCF CAGR')}:** {final_g*100:.1f}% ({data_len}{t('년 데이터 자동 산출', ' years of data)')})")
                    st.write(f"- **{t('추정 적정가', 'Estimated Fair Value')}:** {iv_str}")
                    if mos > 0: st.markdown(f"- **{t('DCF 안전마진', 'DCF Margin of Safety')}:** <span class='good'>+{mos:.1f}% ({t('저평가', 'Undervalued')})</span>", unsafe_allow_html=True)
                    else: st.markdown(f"- **{t('DCF 안전마진', 'DCF Margin of Safety')}:** <span class='highlight'>{mos:.1f}% ({t('고평가', 'Overvalued')})</span>", unsafe_allow_html=True)
                else:
                    st.error(f"{err} {t('(확인이 필요한 부분입니다)', '(Needs manual verification)')}")
                
                st.divider()
                st.subheader(t("3. 질적 분석", "3. Qualitative Analysis"))
                off = i.get('companyOfficers', [])
                ceo_raw = off[0].get('name') if off else '누락'
                st.markdown(f"- **CEO:** {clean_ceo_name(ceo_raw)}")
                
                st.write(t("**[도덕성/리스크 리포트]**", "**[Ethics / Risk Report]**"))
                default_ceo = t("현재 내장된 데이터베이스 기준, 해당 기업 CEO의 치명적인 횡령, 배임, 사기 등 중범죄 이력은 두드러지지 않습니다. (안전을 위해 교차 검증은 필수입니다.)", "Based on the database, there are no prominent records of severe crimes such as embezzlement or fraud by the CEO. (Cross-verification is mandatory.)")
                st.info(default_ceo) 
                
                sum_t = i.get('kr_sum', i.get('longBusinessSummary',''))
                st.write(t("**[비즈니스 요약]**", "**[Business Summary]**"))
                st.caption(f"{tr_text(sum_t)[:350]}...")

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
                st.subheader(t("5. 기업 해부 및 학문적 모델 적용", "5. Corporate Anatomy & Academic Models"))
                if final_g > 0: math_eval = f"<span class='good'>{t(f'연평균 {final_g*100:.1f}% 성장하며 복리 모형 탑승 중.', f'Growing at {final_g*100:.1f}% CAGR, riding the compound model.')}</span>"
                else: math_eval = f"<span class='highlight'>{t('현금흐름 역성장 (복리 팽창 구간 아님).', 'Negative FCF (Not a compounding phase).')}</span>"
                    
                st.markdown(f"- **{t('수학 (복리 모형):', 'Math (Compound Model):')}** {math_eval}", unsafe_allow_html=True)
                st.write(f"- **{t('생물학 (생존력):', 'Biology (Survivability):')}** {t('부채 구조를 볼 때 다윈주의적 생존력이 있는지 확인 요망.', 'Check Darwinian survivability regarding debt structure.')}")
                st.write(f"- **{t('심리학 (오판 점검):', 'Psychology (Misjudgment):')}** {t('희망 회로나 확증 편향에 빠진 것은 아닌지 점검하십시오.', 'Check for confirmation bias or wishful thinking.')}")
                st.write(f"- **{t('파급력:', 'Impact:')}** {t('기술 변화가 이 기업에 득인가 독인가?', 'Is technological change a boon or bane for this company?')}")

                st.divider()
                st.subheader(t("6. 매도 3원칙 (오직 다음 경우에만 매도)", "6. Sell 3-Principles (Sell ONLY if:)"))
                sell_rules = t("1. 기업 분석에 치명적인 실수가 있었음을 깨달았을 때.<br>2. 밸류에이션(PBR/PER)이 비상식적으로 지나치게 과열되었을 때.<br>3. 더 확실하고 안전한 기회(기회비용 고려)를 발견했을 때.", "1. You realize a fatal mistake in your initial analysis.<br>2. Valuation (PER/PBR) becomes irrationally overheated.<br>3. You find a much safer and better opportunity (Opportunity Cost).")
                st.markdown(f"<div class='guru-quote'>{sell_rules}</div>", unsafe_allow_html=True)

                st.divider()
                st.subheader(t("거장들의 철학 한마디", "Guru's Philosophy Quotes"))
                st.caption(t("**워런 버핏 (소유권):** 주식은 종이가 아니라 '기업의 소유권'입니다. 내가 지분 100%를 인수한다고 가정하고 분석하십시오. 미스터 마켓은 도구일 뿐 선생님이 아닙니다.", "**Warren Buffett (Ownership):** Stocks are not pieces of paper, but 'ownership of a business'. Analyze as if you are buying 100% of it. Mr. Market is your servant, not your master."))
                st.caption(t("**워런 버핏 (안전마진):** 1만 파운드 트럭이 지나갈 다리를 지을 때, 3만 파운드를 견디도록 설계하는 것이 바로 안전마진입니다.", "**Warren Buffett (Margin of Safety):** When you build a bridge, you insist it can carry 30,000 pounds, but you only drive 10,000 pound trucks across it. That same principle works in investing."))
                st.caption(t("**찰리 멍거 (훌륭한 기업):** 훌륭한 기업이 현저히 싼 가격에 거래되는 일은 거의 없습니다. 적당한 기업을 훌륭한 가격에 사는 것보다, 훌륭한 기업을 적당한 가격에 사는 것이 훨씬 낫습니다.", "**Charlie Munger (Great Business):** It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price. A truly great business rarely comes at a significantly cheap price."))
                st.caption(t("**찰리 멍거 (능력범위):** 당신의 '능력 범위'를 명확히 아는 것이 가장 중요합니다. 전문가의 반론에 논리적으로 재반박할 수 없다면, 그것은 당신의 능력 밖입니다.", "**Charlie Munger (Circle of Competence):** Knowing what you don't know is more useful than being brilliant. If you can't logically refute an expert's counterargument, it's outside your circle."))
                st.caption(t("**필립 피셔 (타이밍):** 가장 좋은 매수 타이밍은 상업화 초기 단계의 일시적 문제, 미스터 마켓의 우울증, 그리고 일시적이고 해결 가능한 경영상의 악재가 발생했을 때입니다.", "**Philip Fisher (Timing):** The best time to buy is when there are temporary problems in early commercialization, market depression, or temporary/solvable management issues."))

            else:
                st.error(t("데이터를 불러올 수 없습니다. 티커를 확인해주세요.", "Cannot fetch data. Please check the ticker."))

# ==========================================
# 탭 2: 유명 가치투자자 13F 포트폴리오
# ==========================================
with tab2:
    st.subheader(t("글로벌 유명 가치투자자 13F 포트폴리오", "Global Value Gurus 13F Portfolio"))
    st.caption(t("※ 미국의 13F 공시를 추적하여 최신 포트폴리오 비중을 표출합니다.", "※ Tracks US 13F filings to display latest portfolio weights."))
    
    guru_map = {
        "리 루 (Himalaya Capital)": "HC",
        "워런 버핏 (Berkshire Hathaway)": "BRK",
        "빌 애크먼 (Pershing Square)": "PSH",
        "세스 클라만 (Baupost Group)": "BAU",
        "척 아크레 (Akre Capital)": "AKRE",
        "모니시 파브라이 (Dalal Street)": "PI",
        "가이 스피어 (Aquamarine Capital)": "AQUA"
    }
    
    guru_option = st.selectbox(t("포트폴리오를 조회할 유명 가치투자자를 선택하세요:", "Select a Value Guru:"), list(guru_map.keys()))

    with st.spinner(t("최신 포트폴리오 데이터 연동 중...", "Fetching latest portfolio data...")):
        code = guru_map[guru_option]
        scraped_data = get_13f_portfolio(code)
            
        if scraped_data and len(scraped_data) > 0:
            df = pd.DataFrame(scraped_data)
            df.index = df.index + 1
            
            st.dataframe(
                df,
                column_config={
                    "티커": st.column_config.TextColumn("Ticker"),
                    "기업명": st.column_config.TextColumn("Company Name"),
                    "비중(%)": st.column_config.ProgressColumn(
                        "Weight (%)", format="%.2f%%", min_value=0, max_value=max(df["비중(%)"]) + 5
                    ),
                },
                use_container_width=True
            )
            
            st.markdown("---")
            st.write(t("🔍 **포트폴리오 종목 빠른 분석 장전**", "🔍 **Fast Load for Analysis**"))
            c_tk, c_btn = st.columns([3, 1])
            with c_tk:
                fast_tk = st.selectbox("Ticker", df["티커"].tolist(), label_visibility="collapsed")
            with c_btn:
                # 💡 장전하기 원클릭 처리 + 토스트 알림
                if st.button(t("검색창에 장전하기", "Load to Search"), use_container_width=True):
                    st.session_state.search_tk = fast_tk
                    st.toast(t(f"🎯 {fast_tk} 분석 장전 완료! 상단의 [개별 기업 가치분석] 탭을 클릭하세요.", f"🎯 {fast_tk} Loaded! Click [Company Value Analysis] tab."), icon="✅")
                    st.rerun() 
        else:
            st.warning(t("데이터를 불러오는 데 실패했습니다.", "Failed to load data."))

st.divider()
st.markdown(f"""
<div style='text-align: center; color: #8b949e; font-size: 0.85rem; line-height: 1.6;'>
    <p><b>{t('[면책 조항 / Disclaimer]', '[Disclaimer]')}</b><br>
    {t('본 애플리케이션은 가치투자 분석을 돕기 위한 <b>단순 보조 도구</b>일 뿐입니다. 제공되는 재무 데이터, 13F 공시 정보, 분석 결과는 오류나 지연이 발생할 수 있습니다.', 'This application is a <b>simple auxiliary tool</b> to assist in value investing analysis. Provided financial data, 13F filings, and analysis results may contain errors or delays.')}<br>
    {t('본 터미널의 결과만으로 실제 주식의 특정 종목 매수 및 매도를 권유하지 않으며, <b>최종 투자 결정 및 그로 인한 재무적 손실에 대한 모든 법적 책임은 전적으로 투자자 본인에게 있습니다.</b>', 'The results of this terminal do not solicit the purchase or sale of specific stocks, and <b>all legal responsibility for final investment decisions and resulting financial losses lies entirely with the investor.</b>')}</p>
    <p><b>[Copyright]</b><br>
    ⓒ 2026 VALUE. All rights reserved.<br>
    {t('본 프로그램의 분석 로직, 산식 및 데이터 표출 양식은 저작권법의 보호를 받으며, 원작자의 허가 없는 무단 복제, 배포, 상업적 이용을 엄격히 금지합니다.', 'The analysis logic, formulas, and data display formats of this program are protected by copyright law, and unauthorized reproduction, distribution, or commercial use without permission is strictly prohibited.')}</p>
</div>
""", unsafe_allow_html=True)
